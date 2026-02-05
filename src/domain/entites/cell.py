from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class MatrixCell:
    line_number: int
    product_name: str
    price: int
