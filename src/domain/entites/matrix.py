from dataclasses import dataclass

from src.domain.entites.cell import MatrixCell
from src.domain.value_objects.ids.vending_machine_id import VMId


@dataclass(frozen=True, slots=True, kw_only=True)
class Matrix:
    name: str
    cells: list[MatrixCell]
    vending_machines_ids: list[VMId]
