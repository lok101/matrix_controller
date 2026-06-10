from abc import ABC, abstractmethod

from src.domain.entities.product import Product


class GetAllProductsPort(ABC):
    @abstractmethod
    def execute(self) -> list[Product]: ...
