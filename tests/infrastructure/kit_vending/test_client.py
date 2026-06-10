from __future__ import annotations

import asyncio
import hashlib
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import ClientError

from src.infrastructure.kit_vending.api.enums import VendingMachineCommand
from src.infrastructure.kit_vending.api.exceptions import KitAPIResponseError, KitAPINetworkError
from tests.infrastructure.kit_vending.conftest import (
    TEST_ACCOUNT,
    TEST_REQUEST_ID,
    make_kit_client,
    patch_client_method,
)


def _mock_post_response(payload: dict) -> AsyncMock:
    response = AsyncMock()
    response.raise_for_status = MagicMock()
    response.json = AsyncMock(return_value=payload)
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=False)
    return response


def _attach_session(client, post_side_effect) -> None:
    session = AsyncMock()
    session.post = MagicMock(side_effect=post_side_effect)
    session.closed = False
    client._session = session
    client._own_session = False


def test_build_auth_sign_is_md5_of_company_password_request_id() -> None:
    client = make_kit_client()

    auth = client._build_auth(TEST_REQUEST_ID, None)

    expected_sign = hashlib.md5(
        f"{TEST_ACCOUNT.company_id}{TEST_ACCOUNT.password}{TEST_REQUEST_ID}".encode("utf-8")
    ).hexdigest()

    assert auth["Sign"] == expected_sign
    assert auth["CompanyId"] == 99
    assert auth["RequestId"] == TEST_REQUEST_ID
    assert auth["UserLogin"] == "user"


def test_get_vending_machines_success() -> None:
    payload = {
        "ResultCode": 0,
        "VendingMachines": [
            {
                "VendingMachineId": 1,
                "VendingMachineName": "[1] Тест",
                "GoodsMatrix": None,
                "CompanyId": 99,
                "ModemSerialNumber": 111,
            }
        ],
    }
    client = make_kit_client()
    _attach_session(client, [_mock_post_response(payload)])

    collection = asyncio.run(client.get_vending_machines())

    assert len(collection.get_active()) == 1


def test_send_command_raises_on_non_zero_result_code() -> None:
    payload = {"ResultCode": 5, "ErrorMessage": "Ошибка"}
    client = make_kit_client()
    _attach_session(client, [_mock_post_response(payload)])

    with pytest.raises(KitAPIResponseError) as exc_info:
        asyncio.run(
            client.send_command_to_vending_machine(
                machine_id=1,
                command=VendingMachineCommand.LOAD_MATRIX,
            )
        )

    assert exc_info.value.result_code == 5


def test_async_send_post_retries_on_too_many_requests() -> None:
    ok_payload = {"ResultCode": 0, "VendingMachines": []}
    rate_limit_payload = {"ResultCode": 27, "ErrorMessage": "Too many"}
    responses = [_mock_post_response(rate_limit_payload), _mock_post_response(ok_payload)]

    client = make_kit_client()
    session = AsyncMock()
    session.post = MagicMock(side_effect=responses)
    session.closed = False
    client._session = session
    client._own_session = False

    collection = asyncio.run(client.get_vending_machines())

    assert collection.get_all() == []
    assert session.post.call_count == 2


def test_async_send_post_raises_network_error() -> None:
    client = make_kit_client()
    session = AsyncMock()
    session.post = MagicMock(side_effect=ClientError("connection reset"))
    session.closed = False
    client._session = session
    client._own_session = False

    with pytest.raises(KitAPINetworkError, match="Ошибка сети"):
        asyncio.run(client.get_vending_machines())
