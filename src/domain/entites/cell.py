from dataclasses import dataclass

from src.domain.entites.product import Product
from src.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True, kw_only=True)
class MatrixCell:
    line_number: int
    product: Product
    price: Money
