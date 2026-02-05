from abc import ABC, abstractmethod

from new_src.domain.entites.vending_machine import VendingMachine
from new_src.domain.value_objects.ids.matrix_kit_id import MatrixKitId


class BindMatrixToVendingMachinePort(ABC):
    @abstractmethod
    async def execute(self, vending_machine: VendingMachine, matrix_kit_id: MatrixKitId): pass
