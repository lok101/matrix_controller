from dataclasses import dataclass

from src.domain.entities.matrix import MatrixCell
from src.domain.enums import MachineModel


@dataclass(frozen=True)
class CreateMatrixDTO:
    name: str
    machine_ids: list[int]
    machine_model: MachineModel
    cells: list[MatrixCell]
