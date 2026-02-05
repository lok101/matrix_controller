import logging
from dataclasses import dataclass

from beartype import beartype
from kit_api import KitVendingAPIClient, ResultCode

from src.domain.entites.vending_machine import VendingMachine
from src.domain.ports.bind_matrix_to_vending_machine import BindMatrixToVendingMachinePort
from src.domain.value_objects.ids.matrix_kit_id import MatrixKitId
from src.domain.value_objects.ids.vending_machine_kit_id import VMKitId

logger = logging.getLogger("__main__")


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class BindMatrixToVendingMachineAdapter(BindMatrixToVendingMachinePort):
    kit_api_client: KitVendingAPIClient

    async def execute(self, vending_machine: VendingMachine, matrix_kit_id: MatrixKitId) -> bool:
        vending_machine_id: VMKitId = vending_machine.kit_id

        res: ResultCode = await self.kit_api_client.bound_matrix_to_vending_machine(
            machine_id=vending_machine_id.value,
            matrix_id=matrix_kit_id.value
        )

        if res is not ResultCode.SUCCESS:
            logger.critical(
                f"Не удалось привязать матрицу к аппарату {vending_machine.name}."
            )
            return False

        return True
