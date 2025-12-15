from abc import ABC, abstractmethod

from src.application.dto.create_product_dto import CreateProductDTO
from src.domain.entities.product import Product


class ProductRepository(ABC):
    @abstractmethod
    def create(self, dto: CreateProductDTO) -> Product: pass

    @abstractmethod
    def get_by_name(self, name: str) -> Product | None: pass
