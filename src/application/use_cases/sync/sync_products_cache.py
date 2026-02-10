import logging
from dataclasses import dataclass

from beartype import beartype

from src.application.repositories.product_repository import ProductRepository
from src.domain.entites.product import Product
from src.domain.ports.get_products import GetAllProductsPort

logger = logging.getLogger()


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class SyncProductsCache:
    get_products: GetAllProductsPort
    product_repository: ProductRepository

    def execute(self):
        self.product_repository.clear()
        products: list[Product] = self.get_products.execute()

        for product in products:
            self.product_repository.add(product)

        logger.info(f"Синхронизация товаров завершена. Товаров в репозитории: {self.product_repository.get_size()}")
