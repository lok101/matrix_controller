from abc import ABC, abstractmethod

from src.domain.entities.product import Product


class ProductRepository(ABC):
    @abstractmethod
    def get_by_name(self, product_name: str) -> Product | None: ...

    @abstractmethod
    def add(self, product: Product) -> None: ...

    @abstractmethod
    def clear(self) -> None: ...

    @abstractmethod
    def get_size(self) -> int: ...
