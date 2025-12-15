from dataclasses import dataclass
from datetime import date

from src.domain.entities.product import Product
from src.domain.enums import MachineModel


@dataclass(frozen=True)
class MatrixCell:
    product: Product
    line_number: int
    price: int

    @property
    def product_full_name(self) -> str:
        return "{:.60}...".format(f"{self.product.id} | {self.product.name}")

    @property
    def product_capacity(self) -> int:
        return self.product.capacity


@dataclass
class Matrix:
    name: str
    machine_ids: list[int]
    machine_model: MachineModel
    cells: list[MatrixCell]

    def get_matrix_full_name(self):
        return f'{self.name} | {date.today().strftime('%d.%m.%y')} | {self.machine_model}'
