from dataclasses import dataclass


@dataclass(frozen=True)
class Product:
    id: int
    name: str
    capacity: int
    purchase_price: int
