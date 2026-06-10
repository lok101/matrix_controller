from abc import ABC, abstractmethod

from src.domain.entities.vending_machine import VendingMachine
from src.domain.value_objects.ids.matrix_kit_id import MatrixKitId


class BindMatrixToVendingMachinePort(ABC):
    @abstractmethod
    async def execute(
        self, vending_machine: VendingMachine, matrix_kit_id: MatrixKitId
    ) -> bool: ...
