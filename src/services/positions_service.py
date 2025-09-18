from abc import ABC, abstractmethod

from src.services.matrix_service import Cell
from src.services.snack_machine_service import SnackMatrixId


class ProductPositionsRepository(ABC):
    @abstractmethod
    def find_all(self, matrix_type: SnackMatrixId) -> list[Cell]: pass


class ProductPositionsService:
    def __init__(self, repository: ProductPositionsRepository):
        self._repository = repository

    @abstractmethod
    def get_cells(self, matrix_type: SnackMatrixId) -> list[Cell]:
        return self._repository.find_all(matrix_type)
