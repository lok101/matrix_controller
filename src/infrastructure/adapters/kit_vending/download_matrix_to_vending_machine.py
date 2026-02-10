import asyncio
import logging
from dataclasses import dataclass

from beartype import beartype
from kit_api import KitVendingAPIClient, KitAPIResponseError, KitAPIError
from kit_api.enums import VendingMachineCommand, ResultCode, VendingMachineStatus
from kit_api.models.vending_machine_state import VendingMachinesStatesCollection, VendingMachineStateModel

from src.domain.entites.vending_machine import VendingMachine
from src.domain.ports.download_matrix_to_vending_machine import DownloadMatrixToVendingMachinePort
from src.domain.value_objects.ids.vending_machine_kit_id import VMKitId

logger = logging.getLogger(__name__)


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class DownloadMatrixToVendingMachineAdapter(DownloadMatrixToVendingMachinePort):
    kit_api_client: KitVendingAPIClient

    matrix_load_timeout: int = 120
    max_retry_attempts: int = 3

    async def execute(self, vending_machine: VendingMachine) -> bool:
        matrix_reload_attempt: int = 0
        command_send_attempt: int = 0
        max_command_send_attempts: int = 3

        while matrix_reload_attempt < self.max_retry_attempts:
            try:
                await self._download_matrix_to_vending_machine(vending_machine)

            except KitAPIError:
                command_send_attempt += 1
                logger.warning(
                    f"Не удалось отправить команду загрузки матрицы для аппарата {vending_machine.name}. "
                    f"Попытка отправки команды #{command_send_attempt}/{max_command_send_attempts}."
                )

                if command_send_attempt >= max_command_send_attempts:
                    logger.error(
                        f"Достигнуто максимальное количество попыток ({max_command_send_attempts}) "
                        f"для отправки команды загрузки матрицы аппарата {vending_machine.name}. "
                        f"Операция прервана."
                    )
                    return False

                await asyncio.sleep(10)  # Задержка перед повторной попыткой отправки команды
                continue

            # Команда успешно отправлена, сбрасываем счетчик попыток отправки
            command_send_attempt = 0

            logger.info(
                f"Команда загрузки матрицы отправлена для аппарата {vending_machine.name}. "
                f"Ожидание {self.matrix_load_timeout} секунд перед проверкой статуса."
            )
            await asyncio.sleep(self.matrix_load_timeout)

            is_matrix_loaded: bool = await self._is_matrix_loaded(vending_machine)

            if is_matrix_loaded:
                if matrix_reload_attempt > 0:
                    logger.info(
                        f"Матрица успешно загружена для аппарата {vending_machine.name} "
                        f"после {matrix_reload_attempt} попыток перезагрузки."
                    )
                else:
                    logger.info(
                        f"Матрица успешно загружена для аппарата {vending_machine.name}."
                    )
                return True

            matrix_reload_attempt += 1
            logger.warning(
                f"Матрица не загружена для аппарата {vending_machine.name}. "
                f"Попытка перезагрузки #{matrix_reload_attempt}."
            )

        else:
            logger.error(
                f"Достигнуто максимальное количество попыток ({self.max_retry_attempts}) "
                f"для загрузки матрицы аппарата {vending_machine.name}. "
                f"Операция прервана."
            )
            return False

    async def _download_matrix_to_vending_machine(self, vending_machine: VendingMachine) -> bool:
        vending_machine_id: VMKitId = vending_machine.kit_id
        command: VendingMachineCommand = VendingMachineCommand.LOAD_MATRIX

        try:
            res: ResultCode = await self.kit_api_client.send_command_to_vending_machine(
                machine_id=vending_machine_id.value,
                command=command
            )

            if res is not ResultCode.SUCCESS:
                logger.warning(
                    f"Не удалось отправить команду загрузки матрицы для аппарата {vending_machine.name}. "
                    f"Код результата: {res}."
                )
                return False

            return True

        except KitAPIResponseError as ex:
            logger.error(
                f"Ошибка API при отправке команды загрузки матрицы для аппарата {vending_machine.name}: {ex}."
            )
            return False

        except Exception as ex:
            logger.exception(
                f"Неожиданная ошибка при отправке команды загрузки матрицы для аппарата {vending_machine.name}: {ex}."
            )
            return False

    async def _is_matrix_loaded(self, vending_machine: VendingMachine) -> bool:
        try:
            vm_states_collection: VendingMachinesStatesCollection = await self.kit_api_client.get_vending_machine_states()
            # Предполагаем, что vm_state.id соответствует vending_machine.id.value (VMId)
            # Это должно быть число, соответствующее номеру аппарата из ActiveVendingMachineModel.number
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

            if VendingMachineStatus.MATRIX_LOADED in vm_statuses:
                return True

            return False

        except KitAPIResponseError as ex:
            logger.error(
                f"Ошибка API при получении состояния аппарата {vending_machine.name}: {ex}."
            )
            return False

        except Exception as ex:
            logger.exception(
                f"Неожиданная ошибка при проверке загрузки матрицы для аппарата {vending_machine.name}: {ex}."
            )
            return False
