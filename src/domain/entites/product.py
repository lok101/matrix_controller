from dataclasses import dataclass

from beartype import beartype

from src.domain.value_objects.ids.product_id import ProductId
from src.domain.value_objects.money import Money

@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class Product:
    id: ProductId
    name: str
    purchase_price: Money
