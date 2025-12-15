from dataclasses import dataclass

from src.domain.enums import MachineModel


@dataclass(frozen=True)
class CellData:
    product_name: str
    line: int
    price: int


@dataclass
class MatrixData:
    matrix_name: str
    machine_model: MachineModel
    machine_ids: list[int]
    cells: list[CellData]
