import logging
from dataclasses import dataclass

from beartype import beartype

from src.domain.entities.product import Product
from src.domain.exceptions import SynchronizationError
from src.domain.ports.get_products import GetAllProductsPort
from src.domain.value_objects.ids.product_id import ProductId
from src.domain.value_objects.money import Money
from src.infrastructure.google_sheets.client import GoogleSheetsAPIClient

logger = logging.getLogger(__name__)


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class GetAllProductsAdapter(GetAllProductsPort):
    google_table_api_client: GoogleSheetsAPIClient

    def execute(self) -> list[Product]:
        res: list[Product] = []
        products_data = self.google_table_api_client.get_all_products()
        if not products_data:
            logger.warning("Не были найдены товары.")
        for product_model in products_data:
            if product_model.name is None:
                raise SynchronizationError(
                    f"Товар id={product_model.id}: не указано имя."
                )
            if product_model.price is None:
                raise SynchronizationError(
                    f"Товар '{product_model.name}': не указана закупочная цена."
                )
            res.append(
                Product(
                    id=ProductId(product_model.id),
                    name=product_model.name,
                    purchase_price=Money(rubles=product_model.price),
                )
            )
        return res
