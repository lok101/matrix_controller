from src.domain.entities.product import Product
from src.domain.repositories.product_repository import ProductRepository


class InMemoryProductRepository(ProductRepository):
    def __init__(self) -> None:
        self._storage: dict[str, Product] = {}

    def get_by_name(self, product_name: str) -> Product | None:
        return self._storage.get(product_name)

    def add(self, product: Product) -> None:
        self._storage[product.name] = product

    def clear(self) -> None:
        self._storage.clear()

    def get_size(self) -> int:
        return len(self._storage)
