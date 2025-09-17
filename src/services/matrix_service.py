import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


class MatrixType(enum.StrEnum):
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
    def get_all(self, matrix_type: MatrixType) -> list[Cell]: pass


def _generate_matrix_name(matrix_name: str) -> str:
    timestamp_str = datetime.now().strftime('%d.%m.%y')
    matrix_name = f'{timestamp_str} | {matrix_name}'
    return matrix_name


class MatrixService:
    def __init__(self, cell_repository: ICellRepository, matrix_repository: IMatrixRepository):
        self._cell_repo = cell_repository
        self._matrix_repository = matrix_repository

    async def create_matrix(self, matrix_name: str, matrix_type: MatrixType):
        matrix_name = _generate_matrix_name(matrix_name)
        matrix_cells = self._cell_repo.get_all(matrix_type)
        matrix = create_matrix(matrix_name, matrix_cells)
        await self._matrix_repository.add(matrix)
