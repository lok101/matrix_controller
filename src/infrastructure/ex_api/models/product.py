from dataclasses import dataclass


@dataclass(frozen=True)
class ProductData:
    id: int
    name: str
    capacity: int
    purchase_price: float
