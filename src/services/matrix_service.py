import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass


class SnackMatrixId(enum.StrEnum):
    ugmk_1stage_blue = 'угмк_kv12'


@dataclass(frozen=True)
class Cell:
    product_name: str
    price: int
    number: int
    capacity: int


@dataclass(frozen=True)
class Matrix:
    name: str
    cells: list[Cell]


def create_matrix(matrix_name: str, cells: list[Cell]) -> Matrix:
    return Matrix(name=matrix_name, cells=cells)


class IMatrixRepository(ABC):
    @abstractmethod
    async def add(self, matrix: Matrix): pass


class ICellRepository(ABC):
    @abstractmethod
    def get_all(self, matrix_type: SnackMatrixId) -> list[Cell]: pass


class MatrixService:
    def __init__(self, cell_repository: ICellRepository, matrix_repository: IMatrixRepository):
        self._cell_repo = cell_repository
        self._matrix_repository = matrix_repository

    async def create_matrix(self, matrix_name: str, matrix_type: SnackMatrixId):
        matrix_cells = self._cell_repo.get_all(matrix_type)
        matrix = create_matrix(matrix_name, matrix_cells)
        await self._matrix_repository.add(matrix)
