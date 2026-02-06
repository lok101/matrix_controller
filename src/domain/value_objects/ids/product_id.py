from dataclasses import dataclass

from beartype import beartype


@beartype
@dataclass(frozen=True, slots=True)
class ProductId:
    value: int
