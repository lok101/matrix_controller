from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Cell:
    product_name: str
    price_cash: int
    price: int
    number: int
    capacity: int | None = field(default=None)


@dataclass(frozen=True)
class Matrix:
    name: str
    cells: list[Cell]


def create_matrix(matrix_name: str, cells: list[Cell]) -> Matrix:
    return Matrix(name=matrix_name, cells=cells)


class IMatrixRepository(ABC):
    @abstractmethod
    async def add(self, matrix: Matrix): pass


class MatrixService:
    def __init__(self, matrix_repository: IMatrixRepository):
        self._matrix_repository = matrix_repository

    async def create_matrix(self, matrix_name: str, matrix_cells: list[Cell]):
        matrix = create_matrix(matrix_name, matrix_cells)
        await self._matrix_repository.add(matrix)
