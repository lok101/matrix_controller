import logging
from dataclasses import dataclass

from beartype import beartype

from src.domain.entites.product import Product
from src.domain.ports.get_products import GetAllProductsPort
from src.domain.value_objects.ids.product_id import ProductId
from src.domain.value_objects.money import Money
from src.infrastructure.google_sheets_api_client import GoogleSheetsAPIClient, ProductModel

logger = logging.getLogger("__main__")


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class GetAllProductsAdapter(GetAllProductsPort):
    google_table_api_client: GoogleSheetsAPIClient

    def execute(self) -> list[Product]:
        res: list[Product] = []
        products_data: list[ProductModel] = self.google_table_api_client.get_all_products()

        if not products_data:
            logger.warning("Не были найдены товары.")

        for product_model in products_data:
            product_id: ProductId = ProductId(product_model.id)
            product_name: str = product_model.name
            price: Money = Money(product_model.price)

            product: Product = Product(
                id=product_id,
                name=product_name,
                purchase_price=price,
            )
            res.append(product)

        return res
