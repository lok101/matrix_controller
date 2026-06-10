from __future__ import annotations

import pytest

from src.domain.exceptions import SynchronizationError
from src.infrastructure.google_sheets.adapters.get_products import GetAllProductsAdapter
from src.infrastructure.google_sheets.client import ProductModel


class FakeSheetsClient:
    def __init__(self, products: list[ProductModel]) -> None:
        self._products = products

    def get_all_products(self) -> list[ProductModel]:
        return self._products


def _adapter_with_client(client: FakeSheetsClient) -> GetAllProductsAdapter:
    adapter = object.__new__(GetAllProductsAdapter)
    object.__setattr__(adapter, "google_table_api_client", client)
    return adapter


def test_get_products_raises_when_price_missing():
    client = FakeSheetsClient(
        [ProductModel(id=1, name="Cola", price=None)]
    )
    adapter = _adapter_with_client(client)

    with pytest.raises(SynchronizationError, match="не указана закупочная цена"):
        adapter.execute()


def test_get_products_raises_when_name_missing():
    client = FakeSheetsClient(
        [ProductModel(id=2, name=None, price=50.0)]
    )
    adapter = _adapter_with_client(client)

    with pytest.raises(SynchronizationError, match="не указано имя"):
        adapter.execute()
