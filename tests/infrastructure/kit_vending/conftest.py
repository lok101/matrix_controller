from __future__ import annotations

from unittest.mock import AsyncMock

from src.infrastructure.kit_vending.api.account import KitAPIAccount
from src.infrastructure.kit_vending.api.client import KitVendingAPIClient
from src.infrastructure.kit_vending.api.config import KitAPIConfig

TEST_CONFIG = KitAPIConfig(
    company_id=99,
    login="user",
    password="secret",
    request_per_window=10,
    window_seconds=1,
    backoff_seconds=0.01,
)
TEST_ACCOUNT = KitAPIAccount(login="user", password="secret", company_id=99)
TEST_REQUEST_ID = 1700000000


def make_kit_client() -> KitVendingAPIClient:
    return KitVendingAPIClient(
        account=TEST_ACCOUNT,
        config=TEST_CONFIG,
    )


def patch_client_method(client: KitVendingAPIClient, name: str, mock: AsyncMock) -> KitVendingAPIClient:
    object.__setattr__(client, name, mock)
    return client
