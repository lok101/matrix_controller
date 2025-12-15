from abc import ABC, abstractmethod

from src.domain.entities.matrix import Matrix
from src.domain.entities.vending_machine import VendingMachine


class VendorMatrixGateway(ABC):
    @abstractmethod
    async def upload_matrix(self, matrix: Matrix): pass

    @abstractmethod
    async def apply_to_machine(self, matrix_id: int, vending_machine: VendingMachine): pass
