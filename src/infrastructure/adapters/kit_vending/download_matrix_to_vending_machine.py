import logging
from dataclasses import dataclass

from beartype import beartype
from kit_api import KitVendingAPIClient
from kit_api.enums import VendingMachineCommand, ResultCode

from src.domain.entites.vending_machine import VendingMachine
from src.domain.ports.download_matrix_to_vending_machine import DownloadMatrixToVendingMachinePort
from src.domain.value_objects.ids.vending_machine_kit_id import VMKitId

logger = logging.getLogger("__main__")


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class DownloadMatrixToVendingMachineAdapter(DownloadMatrixToVendingMachinePort):
    kit_api_client: KitVendingAPIClient

    async def execute(self, vending_machine: VendingMachine):
        vending_machine_id: VMKitId = vending_machine.kit_id
        command: VendingMachineCommand = VendingMachineCommand.LOAD_MATRIX

        res: ResultCode = await self.kit_api_client.send_command_to_vending_machine(
            machine_id=vending_machine_id.value,
            command=command
        )

        if res is not ResultCode.SUCCESS:
            logger.critical(
                f"Не удалось привязать матрицу к аппарату {vending_machine.name}."
            )
            return False

        return True
