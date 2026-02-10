import logging
from dataclasses import dataclass

from beartype import beartype
from kit_api import KitVendingAPIClient, KitAPIError
from kit_api.enums import VendingMachineCommand

from src.domain.entites.vending_machine import VendingMachine
from src.domain.ports.apply_matrix_to_vending_machine import ApplyMatrixToVendingMachinePort
from src.domain.value_objects.ids.vending_machine_kit_id import VMKitId

logger = logging.getLogger()


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class ApplyMatrixToVendingMachineAdapter(ApplyMatrixToVendingMachinePort):
    kit_api_client: KitVendingAPIClient

    async def execute(self, vending_machine: VendingMachine):
        vending_machine_id: VMKitId = vending_machine.kit_id
        command: VendingMachineCommand = VendingMachineCommand.APPLY_MATRIX

        try:
            await self.kit_api_client.send_command_to_vending_machine(
                machine_id=vending_machine_id.value,
                command=command
            )

        except KitAPIError as ex:
            logger.critical(
                f"Не удалось применить матрицу. Аппарат: {vending_machine.name}. Ошибка: {ex}"
            )
            return False

        return True
