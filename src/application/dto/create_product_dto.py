from dataclasses import dataclass


@dataclass(frozen=True)
class CreateProductDTO:
    id: int
    name: str
    capacity: int
    purchase_price: int
