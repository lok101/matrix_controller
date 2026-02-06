from src.application.repositories.product_repository import ProductRepository
from src.domain.entites.product import Product
from src.domain.value_objects.ids.product_id import ProductId


class InMemoryProductRepository(ProductRepository):

    def __init__(self):
        self._storage: dict[ProductId, Product] = {}
        self._index_by_name: dict[str, Product] = {}

    def add(self, product: Product) -> None:
        self._storage[product.id] = product
        self._index_by_name[product.name] = product

    def get_by_name(self, product_name: str) -> Product | None:
        return self._index_by_name.get(product_name)

    def get_size(self) -> int:
        return len(self._storage)

    def clear(self) -> None:
        self._storage.clear()
        self._index_by_name.clear()
