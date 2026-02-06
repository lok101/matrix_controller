from abc import ABC, abstractmethod

from src.domain.entites.product import Product


class ProductRepository(ABC):
    @abstractmethod
    def get_by_name(self, product_name: str) -> Product | None: pass
