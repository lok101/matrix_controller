from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from beartype import beartype

from src.domain.entities.vending_machine import VendingMachine
from src.domain.ports.batch_matrix_deploy import BatchDeployCoordinatorPort
from src.domain.ports.bind_matrix_to_vending_machine import BindMatrixToVendingMachinePort
from src.domain.ports.upload_machine_matrix import UploadMatrixPort
from src.domain.services.matrix_validator import MatrixValidator
from src.domain.value_objects.ids.matrix_kit_id import MatrixKitId
from src.domain.value_objects.matrix_deploy_item import MatrixDeployItem
from src.infrastructure.kit_vending.api.client import KitVendingAPIClient
from src.infrastructure.kit_vending.api.enums import ResultCode, VendingMachineCommand, VendingMachineStatus
from src.infrastructure.kit_vending.api.exceptions import KitAPIError, KitAPIResponseError, KitAPINetworkError
from src.infrastructure.kit_vending.api.models.vending_machine_state import (
    VendingMachinesStatesCollection,
    VendingMachineStateModel,
)
from src.infrastructure.kit_vending.machine_deploy_task import (
    MachineDeployTask,
    MachinePollSnapshot,
    is_apply_confirmed,
    is_load_confirmed,
)

logger = logging.getLogger(__name__)

TaskKey = tuple[str, int]


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class BatchMatrixDeployCoordinator(BatchDeployCoordinatorPort):
    kit_api_client: KitVendingAPIClient
    upload_matrix_port: UploadMatrixPort
    bind_matrix_to_machine_port: BindMatrixToVendingMachinePort
    validate_matrices: bool
    load_timeout_seconds: int
    apply_timeout_seconds: int
    poll_interval_seconds: int
    command_send_delay_seconds: int
    poll_api_max_retries: int
    retry_send_command_delay_seconds: int
    max_command_send_attempts: int = 3

    async def deploy(
        self,
        items: list[MatrixDeployItem],
        timestamp: datetime,
    ) -> list[tuple[str, int, int]]:
        tasks: dict[TaskKey, MachineDeployTask] = {}

        for item in items:
            await self._phase_prepare_and_send_load(item, timestamp, tasks)

        await self._phase_poll_load(tasks)
        await self._phase_send_apply(tasks)
        await self._phase_poll_apply(tasks)

        return self._aggregate_results(items, tasks)

    async def _phase_prepare_and_send_load(
        self,
        item: MatrixDeployItem,
        timestamp: datetime,
        tasks: dict[TaskKey, MachineDeployTask],
    ) -> None:
        matrix = item.matrix
        if self.validate_matrices:
            MatrixValidator.validate(matrix)

        matrix_id: MatrixKitId | None = await self.upload_matrix_port.execute(matrix, timestamp)
        if matrix_id is None:
            logger.critical(
                "Не удалось создать матрицу '%s' — все аппараты матрицы помечены failed.",
                matrix.name,
            )
            for machine in item.machines:
                tasks[self._task_key(matrix.name, machine.kit_id.value)] = MachineDeployTask(
                    machine=machine,
                    matrix_name=matrix.name,
                    phase="failed",
                    failure_step="upload",
                    failure_message="Не удалось создать матрицу",
                )
            return

        for machine in item.machines:
            kit_id = machine.kit_id.value
            if not await self.bind_matrix_to_machine_port.execute(machine, matrix_id):
                tasks[self._task_key(matrix.name, kit_id)] = MachineDeployTask(
                    machine=machine,
                    matrix_name=matrix.name,
                    phase="failed",
                    failure_step="bind",
                    failure_message="Не удалось привязать матрицу",
                )
                continue

            sent = await self._send_command(machine, VendingMachineCommand.LOAD_MATRIX)
            if not sent:
                tasks[self._task_key(matrix.name, kit_id)] = MachineDeployTask(
                    machine=machine,
                    matrix_name=matrix.name,
                    phase="failed",
                    failure_step="send_command",
                    failure_message="Не удалось отправить LOAD_MATRIX",
                )
                continue

            tasks[self._task_key(matrix.name, kit_id)] = MachineDeployTask(
                machine=machine,
                matrix_name=matrix.name,
                phase="pending_load",
                phase_started_at=datetime.now(),
            )
            await asyncio.sleep(self.command_send_delay_seconds)

    async def _phase_poll_load(self, tasks: dict[TaskKey, MachineDeployTask]) -> None:
        pending = [t for t in tasks.values() if t.phase == "pending_load"]
        poll_number = 0
        while pending:
            pending = [t for t in tasks.values() if t.phase == "pending_load"]
            if not pending:
                break

            logger.info("Deploy: фаза load, pending=%s", len(pending))
            await asyncio.sleep(self.poll_interval_seconds)
            poll_number += 1
            states_map = await self._fetch_states_map()
            if states_map is None:
                logger.warning(
                    "GetVMStates недоступен после %s попыток, пропуск poll-цикла load",
                    self.poll_api_max_retries,
                )
                for task in pending:
                    self._fail_on_phase_timeout(task, self.load_timeout_seconds, "poll_load")
                continue

            for task in pending:
                snapshot = self._poll_snapshot_for_machine(states_map, task.machine.kit_id.value)
                elapsed = (datetime.now() - task.phase_started_at).total_seconds()
                status_repr = self._format_poll_snapshot(snapshot)

                if is_load_confirmed(snapshot):
                    task.phase = "loaded"
                    logger.info(
                        "[%s] load подтверждён за %.0f сек, статусы: %s",
                        task.machine.kit_id.value,
                        elapsed,
                        status_repr,
                    )
                elif self._fail_on_phase_timeout(
                    task, self.load_timeout_seconds, "poll_load", status_repr=status_repr
                ):
                    pass
                else:
                    task.last_seen_in_response = snapshot.found
                    task.last_seen_statuses = snapshot.statuses
                    logger.debug(
                        "Poll load #%s (%.0fs): [%s]=%s waiting",
                        poll_number,
                        elapsed,
                        task.machine.kit_id.value,
                        status_repr,
                    )

    async def _phase_send_apply(self, tasks: dict[TaskKey, MachineDeployTask]) -> None:
        for task in tasks.values():
            if task.phase != "loaded":
                continue

            sent = await self._send_command(task.machine, VendingMachineCommand.APPLY_MATRIX)
            if not sent:
                task.phase = "failed"
                task.failure_step = "send_command"
                task.failure_message = "Не удалось отправить APPLY_MATRIX"
                continue

            task.phase = "pending_apply"
            task.phase_started_at = datetime.now()
            await asyncio.sleep(self.command_send_delay_seconds)

    async def _phase_poll_apply(self, tasks: dict[TaskKey, MachineDeployTask]) -> None:
        pending = [t for t in tasks.values() if t.phase == "pending_apply"]
        poll_number = 0
        while pending:
            pending = [t for t in tasks.values() if t.phase == "pending_apply"]
            if not pending:
                break

            logger.info("Deploy: фаза apply, pending=%s", len(pending))
            await asyncio.sleep(self.poll_interval_seconds)
            poll_number += 1
            states_map = await self._fetch_states_map()
            if states_map is None:
                logger.warning(
                    "GetVMStates недоступен после %s попыток, пропуск poll-цикла apply",
                    self.poll_api_max_retries,
                )
                for task in pending:
                    self._fail_on_phase_timeout(task, self.apply_timeout_seconds, "poll_apply")
                continue

            for task in pending:
                snapshot = self._poll_snapshot_for_machine(states_map, task.machine.kit_id.value)
                elapsed = (datetime.now() - task.phase_started_at).total_seconds()
                status_repr = self._format_poll_snapshot(snapshot)

                if is_apply_confirmed(snapshot):
                    task.phase = "applied"
                    logger.info(
                        "[%s] apply подтверждён за %.0f сек, статусы: %s",
                        task.machine.kit_id.value,
                        elapsed,
                        status_repr,
                    )
                elif self._fail_on_phase_timeout(
                    task, self.apply_timeout_seconds, "poll_apply", status_repr=status_repr
                ):
                    pass
                else:
                    task.last_seen_in_response = snapshot.found
                    task.last_seen_statuses = snapshot.statuses
                    logger.debug(
                        "Poll apply #%s (%.0fs): [%s]=%s waiting",
                        poll_number,
                        elapsed,
                        task.machine.kit_id.value,
                        status_repr,
                    )

    async def _send_command(
        self,
        machine: VendingMachine,
        command: VendingMachineCommand,
    ) -> bool:
        attempts = 0
        while attempts < self.max_command_send_attempts:
            try:
                await self.kit_api_client.send_command_to_vending_machine(
                    machine_id=machine.kit_id.value,
                    command=command,
                )
                return True
            except (KitAPINetworkError, KitAPIResponseError) as exc:
                attempts += 1
                if isinstance(exc, KitAPIResponseError) and exc.result_code != ResultCode.TOO_MANY_REQUEST:
                    logger.error(
                        "Ошибка API без retry для %s, команда %s: %s",
                        machine.name,
                        command.name,
                        exc,
                    )
                    return False
                logger.warning(
                    "Retry send_command %s для %s, попытка %s/%s",
                    command.name,
                    machine.name,
                    attempts,
                    self.max_command_send_attempts,
                )
                if attempts < self.max_command_send_attempts:
                    await asyncio.sleep(self.retry_send_command_delay_seconds)
            except KitAPIError as exc:
                logger.error("Неожиданная ошибка Kit API для %s: %s", machine.name, exc)
                return False
        return False

    async def _fetch_states_map(self) -> dict[int, VendingMachineStateModel] | None:
        for attempt in range(1, self.poll_api_max_retries + 1):
            try:
                states: VendingMachinesStatesCollection = (
                    await self.kit_api_client.get_vending_machine_states()
                )
                return {state.id: state for state in states.get_all()}
            except KitAPIError as exc:
                logger.warning(
                    "Ошибка API на poll GetVMStates, попытка %s/%s: %s",
                    attempt,
                    self.poll_api_max_retries,
                    exc,
                )
        return None

    def _poll_snapshot_for_machine(
        self,
        states_map: dict[int, VendingMachineStateModel],
        kit_id: int,
    ) -> MachinePollSnapshot:
        machine_state = states_map.get(kit_id)
        if machine_state is None:
            logger.warning("[%s] not_found в GetVMStates", kit_id)
            return MachinePollSnapshot(found=False, statuses=[])
        return MachinePollSnapshot(found=True, statuses=machine_state.statuses)

    def _fail_on_phase_timeout(
        self,
        task: MachineDeployTask,
        timeout_seconds: int,
        failure_step: str,
        *,
        status_repr: str | None = None,
    ) -> bool:
        elapsed = (datetime.now() - task.phase_started_at).total_seconds()
        if elapsed <= timeout_seconds:
            return False
        task.phase = "failed"
        task.failure_step = failure_step
        task.failure_message = f"{failure_step} timeout {timeout_seconds} сек"
        logger.warning(
            "[%s] %s timeout %.0f сек, последнее состояние: %s",
            task.machine.kit_id.value,
            failure_step,
            timeout_seconds,
            status_repr if status_repr is not None else self._format_last_seen(task),
        )
        return True

    @staticmethod
    def _task_key(matrix_name: str, kit_id: int) -> TaskKey:
        return (matrix_name, kit_id)

    @staticmethod
    def _format_statuses(statuses: list[VendingMachineStatus]) -> str:
        if not statuses:
            return "[]"
        return "[" + ", ".join(str(s.value) for s in statuses) + "]"

    @staticmethod
    def _format_poll_snapshot(snapshot: MachinePollSnapshot) -> str:
        if not snapshot.found:
            return "not_found"
        return BatchMatrixDeployCoordinator._format_statuses(snapshot.statuses)

    def _format_last_seen(self, task: MachineDeployTask) -> str:
        if task.last_seen_in_response is False:
            return "not_found"
        if task.last_seen_in_response is None:
            return "нет данных"
        return self._format_statuses(task.last_seen_statuses)

    def _aggregate_results(
        self,
        items: list[MatrixDeployItem],
        tasks: dict[TaskKey, MachineDeployTask],
    ) -> list[tuple[str, int, int]]:
        results: list[tuple[str, int, int]] = []
        for item in items:
            matrix_tasks = [t for t in tasks.values() if t.matrix_name == item.matrix.name]
            success = sum(1 for t in matrix_tasks if t.phase == "applied")
            failure = sum(1 for t in matrix_tasks if t.phase == "failed")
            total = len(item.machines)
            if failure == 0:
                logger.info("Матрица '%s': все %s аппаратов обработаны успешно.", item.matrix.name, success)
            elif success == 0:
                logger.critical("Матрица '%s': полный провал — 0 из %s аппаратов.", item.matrix.name, total)
            else:
                logger.warning(
                    "Матрица '%s': частичный успех — %s из %s аппаратов, ошибок: %s.",
                    item.matrix.name,
                    success,
                    total,
                    failure,
                )
            results.append((item.matrix.name, success, failure))
        return results
