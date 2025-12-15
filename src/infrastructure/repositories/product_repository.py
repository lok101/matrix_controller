from dataclasses import asdict

from src.application.dto.create_product_dto import CreateProductDTO
from src.domain.entities.product import Product
from src.domain.repositories.product_repository import ProductRepository


class InMemoryProductRepository(ProductRepository):
    def __init__(self):
        self._storage = {}

    def create(self, dto: CreateProductDTO) -> Product:
        key = dto.name

        if key in self._storage.keys():
            raise Exception(f"Продукт \"{dto.name}\" - уже существует.")

        product = Product(**asdict(dto))
        self._storage[key] = product

        return product

    def get_by_name(self, product_name: str) -> Product | None:
        return self._storage.get(product_name)
