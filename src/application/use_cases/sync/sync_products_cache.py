import logging
from dataclasses import dataclass

from beartype import beartype

from src.domain.exceptions import SynchronizationError
from src.domain.ports.get_products import GetAllProductsPort
from src.domain.repositories.product_repository import ProductRepository

logger = logging.getLogger(__name__)


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class SyncProductsCache:
    get_products: GetAllProductsPort
    product_repository: ProductRepository

    def execute(self) -> None:
        self.product_repository.clear()
        products = self.get_products.execute()
        if not products:
            raise SynchronizationError("При попытке синхронизации не были получены товары.")
        for product in products:
            self.product_repository.add(product)
        logger.info(
            "Синхронизация товаров завершена. Товаров в репозитории: %s.",
            self.product_repository.get_size(),
        )
