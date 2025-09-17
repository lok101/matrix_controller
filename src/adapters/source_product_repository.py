from typing import Mapping

from src.external_clients.gspread_client import GspreadClient
from src.services.product_service import ISoursProductsRepo, Product

_headers = ['name']


class SoursProductsRepo(ISoursProductsRepo):
    def __init__(self, gspread_client: GspreadClient):
        self._gspread_client = gspread_client

    def get_all(self) -> list[Product]:
        records = self._gspread_client.get_records('Товары', headers=_headers)
        products = [self._map_to_product(item) for item in records]
        return products

    @staticmethod
    def _map_to_product(record: Mapping):
        return Product(
            name=record['name']
        )
