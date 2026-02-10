import asyncio
import logging
from dataclasses import dataclass

from beartype import beartype
from kit_api import KitVendingAPIClient, KitAPIError
from kit_api.enums import VendingMachineCommand, VendingMachineStatus
from kit_api.models.vending_machine_state import VendingMachinesStatesCollection, VendingMachineStateModel

from src.domain.entites.vending_machine import VendingMachine
from src.domain.ports.apply_matrix_to_vending_machine import ApplyMatrixToVendingMachinePort
from src.domain.value_objects.ids.vending_machine_kit_id import VMKitId

logger = logging.getLogger(__name__)


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class ApplyMatrixToVendingMachineAdapter(ApplyMatrixToVendingMachinePort):
    kit_api_client: KitVendingAPIClient

    matrix_apply_timeout: int = 120
    max_retry_attempts: int = 3
    retry_send_command_timeout: int = 10

    async def execute(self, vending_machine: VendingMachine):
        command: VendingMachineCommand = VendingMachineCommand.APPLY_MATRIX

        matrix_apply_attempt: int = 0
        command_send_attempt: int = 0
        max_command_send_attempts: int = 3

        while matrix_apply_attempt < self.max_retry_attempts:
            try:
                await self.kit_api_client.send_command_to_vending_machine(
                    machine_id=vending_machine.id.value,
                    command=command
                )

            except KitAPIError:
                command_send_attempt += 1
                logger.warning(
                    f"Не удалось отправить команду применения матрицы для аппарата {vending_machine.name}. "
                    f"Попытка отправки команды #{command_send_attempt}/{max_command_send_attempts}."
                )

                if command_send_attempt >= max_command_send_attempts:
                    logger.error(
                        f"Достигнуто максимальное количество попыток ({max_command_send_attempts}) "
                        f"для отправки команды применения матрицы аппарата {vending_machine.name}. "
                        f"Операция прервана."
                    )
                    return False

                await asyncio.sleep(self.retry_send_command_timeout)
                continue

            # Команда успешно отправлена, сбрасываем счетчик попыток отправки
            command_send_attempt = 0

            logger.info(
                f"Команда применения матрицы отправлена для аппарата {vending_machine.name}. "
                f"Ожидание {self.matrix_apply_timeout} секунд перед проверкой статуса."
            )
            await asyncio.sleep(self.matrix_apply_timeout)

            is_matrix_applied: bool = await self._is_matrix_applied(vending_machine)

            if is_matrix_applied:
                if matrix_apply_attempt > 0:
                    logger.info(
                        f"Матрица успешно применена для аппарата {vending_machine.name} "
                        f"после {matrix_apply_attempt} попыток."
                    )
                else:
                    logger.info(
                        f"Матрица успешно применена для аппарата {vending_machine.name}."
                    )
                return True

            matrix_apply_attempt += 1
            logger.warning(
                f"Матрица не применена для аппарата {vending_machine.name}. "
                f"Попытка #{matrix_apply_attempt}."
            )

        else:
            logger.error(
                f"Достигнуто максимальное количество попыток ({self.max_retry_attempts}) "
                f"для применения матрицы аппарата {vending_machine.name}. "
                f"Операция прервана."
            )
            return False

    async def _is_matrix_applied(self, vending_machine: VendingMachine) -> bool:
        try:
            vm_states_collection: VendingMachinesStatesCollection = await self.kit_api_client.get_vending_machine_states()
            vm_states_map: dict[VMKitId, VendingMachineStateModel] = {
                VMKitId(vm_state.id): vm_state for vm_state in vm_states_collection.get_all()
            }

            vm_state: VendingMachineStateModel | None = vm_states_map.get(vending_machine.kit_id)

            if vm_state is None:
                logger.warning(
                    f"Не удалось найти состояние аппарата {vending_machine.name} "
                    f"в коллекции состояний."
                )
                return False

            vm_statuses: list[VendingMachineStatus] = vm_state.statuses

            return VendingMachineStatus.MATRIX_LOADED not in vm_statuses

        except KitAPIError as ex:
            logger.error(
                f"Ошибка API при получении состояния аппарата {vending_machine.name}: {ex}."
            )
            return False

        except Exception as ex:
            logger.exception(
                f"Неожиданная ошибка при проверке применения матрицы для аппарата {vending_machine.name}: {ex}."
            )
            return False
