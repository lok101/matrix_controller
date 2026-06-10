from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass

from beartype import beartype

from src.infrastructure.kit_vending.api.client import KitVendingAPIClient
from src.infrastructure.kit_vending.api.enums import ResultCode, VendingMachineCommand, VendingMachineStatus
from src.infrastructure.kit_vending.api.exceptions import KitAPIError, KitAPIResponseError, KitAPINetworkError
from src.infrastructure.kit_vending.api.models.vending_machine_state import (
    VendingMachinesStatesCollection,
    VendingMachineStateModel,
)
from src.domain.value_objects.command_result import CommandResult

logger = logging.getLogger(__name__)


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class MatrixCommandWorkflow:
    kit_api_client: KitVendingAPIClient
    command: VendingMachineCommand
    status_predicate: Callable[[list[VendingMachineStatus]], bool]
    wait_timeout_seconds: int = 120
    max_retry_attempts: int = 3
    max_command_send_attempts: int = 3
    retry_send_command_timeout_seconds: int = 10

    async def run(self, machine_kit_id: int, machine_name: str) -> CommandResult:
        cycle_attempt = 0
        send_attempts = 0

        while cycle_attempt < self.max_retry_attempts:
            try:
                await self.kit_api_client.send_command_to_vending_machine(
                    machine_id=machine_kit_id,
                    command=self.command,
                )

            except (KitAPINetworkError, KitAPIResponseError) as exc:
                send_attempts += 1
                if isinstance(exc, KitAPIResponseError) and exc.result_code != ResultCode.TOO_MANY_REQUEST:
                    message = f"Ошибка API без retry: {exc}"
                    logger.error(
                        "%s. Аппарат %s, шаг send_command, попытка #%s.",
                        message,
                        machine_name,
                        send_attempts,
                    )
                    return CommandResult(
                        success=False,
                        step="send_command",
                        message=message,
                        attempts=send_attempts,
                    )

                logger.warning(
                    "Не удалось отправить команду %s для %s. Попытка #%s/%s.",
                    self.command.name,
                    machine_name,
                    send_attempts,
                    self.max_command_send_attempts,
                )

                if send_attempts >= self.max_command_send_attempts:
                    message = "Достигнут лимит попыток отправки команды"
                    logger.error(
                        "%s. Аппарат %s, шаг send_command, попытка #%s.",
                        message,
                        machine_name,
                        send_attempts,
                    )
                    return CommandResult(
                        success=False,
                        step="send_command",
                        message=message,
                        attempts=send_attempts,
                    )

                await asyncio.sleep(self.retry_send_command_timeout_seconds)
                continue

            except KitAPIError as exc:
                send_attempts += 1
                message = f"Неожиданная ошибка Kit API: {exc}"
                logger.error(
                    "%s. Аппарат %s, шаг send_command, попытка #%s.",
                    message,
                    machine_name,
                    send_attempts,
                )
                return CommandResult(
                    success=False,
                    step="send_command",
                    message=message,
                    attempts=send_attempts,
                )

            send_attempts = 0
            logger.info(
                "Команда %s отправлена для %s. Ожидание %s сек.",
                self.command.name,
                machine_name,
                self.wait_timeout_seconds,
            )
            await asyncio.sleep(self.wait_timeout_seconds)

            verify_result = await self._verify_status(machine_kit_id, machine_name, cycle_attempt + 1)
            if verify_result.success:
                return verify_result

            cycle_attempt += 1
            logger.warning(
                "Статус не совпал для %s. Цикл #%s/%s.",
                machine_name,
                cycle_attempt,
                self.max_retry_attempts,
            )

        message = "Достигнут лимит циклов ожидания/проверки статуса"
        return CommandResult(
            success=False,
            step="verify_status",
            message=message,
            attempts=self.max_retry_attempts,
        )

    async def _verify_status(
        self,
        machine_kit_id: int,
        machine_name: str,
        attempt: int,
    ) -> CommandResult:
        try:
            states: VendingMachinesStatesCollection = await self.kit_api_client.get_vending_machine_states()
            states_map: dict[int, VendingMachineStateModel] = {
                state.id: state for state in states.get_all()
            }
            machine_state = states_map.get(machine_kit_id)

            if machine_state is None:
                message = "Состояние аппарата не найдено в ответе API"
                logger.error(
                    "%s. Аппарат %s, шаг verify_status, попытка #%s.",
                    message,
                    machine_name,
                    attempt,
                )
                return CommandResult(
                    success=False,
                    step="verify_status",
                    message=message,
                    attempts=attempt,
                )

            if self.status_predicate(machine_state.statuses):
                return CommandResult(
                    success=True,
                    step="verify_status",
                    message="Статус подтверждён",
                    attempts=attempt,
                )

            return CommandResult(
                success=False,
                step="verify_status",
                message="Статус не соответствует ожидаемому",
                attempts=attempt,
            )

        except KitAPIError as exc:
            message = f"Ошибка API при проверке статуса: {exc}"
            logger.error(
                "%s. Аппарат %s, шаг verify_status, попытка #%s.",
                message,
                machine_name,
                attempt,
            )
            return CommandResult(
                success=False,
                step="verify_status",
                message=message,
                attempts=attempt,
            )
