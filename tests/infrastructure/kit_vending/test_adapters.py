from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from src.domain.entites.cell import MatrixCell
from src.domain.entites.matrix import Matrix
from src.domain.entites.product import Product
from src.domain.entites.vending_machine import VendingMachine
from src.domain.value_objects.command_result import CommandResult
from src.domain.value_objects.ids.matrix_kit_id import MatrixKitId
from src.domain.value_objects.ids.product_id import ProductId
from src.domain.value_objects.ids.vending_machine_id import VMId
from src.domain.value_objects.ids.vending_machine_kit_id import VMKitId
from src.domain.value_objects.money import Money
from src.infrastructure.kit_vending.adapters.apply_matrix_to_vending_machine import (
    ApplyMatrixToVendingMachineAdapter,
)
from src.infrastructure.kit_vending.adapters.bind_matrix_to_machine import BindMatrixToVendingMachineAdapter
from src.infrastructure.kit_vending.adapters.download_matrix_to_vending_machine import (
    DownloadMatrixToVendingMachineAdapter,
)
from src.infrastructure.kit_vending.adapters.upload_matrix import UploadMatrixAdapter
from src.infrastructure.kit_vending.api.exceptions import KitAPINetworkError
from src.infrastructure.kit_vending.api.models.vending_machine_state import VendingMachinesStatesCollection
from tests.infrastructure.kit_vending.conftest import make_kit_client, patch_client_method


def _sample_matrix() -> Matrix:
    product = Product(
        id=ProductId(1),
        name="Эспрессо",
        purchase_price=Money(rubles=10),
    )
    cell = MatrixCell(line_number=1, price=Money(rubles=50), product=product)
    return Matrix(name="Тест", cells=[cell], vending_machines_ids=[VMId(7)])


def _sample_machine() -> VendingMachine:
    return VendingMachine(id=VMId(7), kit_id=VMKitId(100), name="[7] Кофе")


def test_upload_matrix_adapter_returns_matrix_kit_id() -> None:
    client = patch_client_method(
        make_kit_client(),
        "create_matrix",
        AsyncMock(return_value=555),
    )

    adapter = UploadMatrixAdapter(kit_api_client=client)
    result = asyncio.run(
        adapter.execute(_sample_matrix(), datetime(2026, 6, 10, tzinfo=timezone.utc))
    )

    assert result == MatrixKitId(555)
    client.create_matrix.assert_awaited_once()


def test_upload_matrix_adapter_returns_none_on_network_error() -> None:
    client = patch_client_method(
        make_kit_client(),
        "create_matrix",
        AsyncMock(side_effect=KitAPINetworkError("timeout")),
    )

    adapter = UploadMatrixAdapter(kit_api_client=client)
    result = asyncio.run(
        adapter.execute(_sample_matrix(), datetime(2026, 6, 10, tzinfo=timezone.utc))
    )

    assert result is None


def test_bind_matrix_adapter_returns_true_on_success() -> None:
    client = patch_client_method(
        make_kit_client(),
        "bound_matrix_to_vending_machine",
        AsyncMock(return_value=0),
    )

    adapter = BindMatrixToVendingMachineAdapter(kit_api_client=client)
    result = asyncio.run(adapter.execute(_sample_machine(), MatrixKitId(555)))

    assert result is True
    client.bound_matrix_to_vending_machine.assert_awaited_once_with(
        machine_id=100,
        matrix_id=555,
    )


def test_download_adapter_returns_command_result_on_success() -> None:
    client = patch_client_method(
        make_kit_client(),
        "send_command_to_vending_machine",
        AsyncMock(return_value=0),
    )
    client = patch_client_method(
        client,
        "get_vending_machine_states",
        AsyncMock(
            return_value=VendingMachinesStatesCollection.model_validate(
                {"VendingMachines": [{"VendingMachineId": 100, "Statuses": "21"}]}
            )
        ),
    )

    adapter = DownloadMatrixToVendingMachineAdapter(
        kit_api_client=client,
        matrix_load_timeout=0,
    )
    result = asyncio.run(adapter.execute(_sample_machine()))

    assert isinstance(result, CommandResult)
    assert result.success is True
    assert result.step == "verify_status"


def test_apply_adapter_returns_command_result_when_matrix_applied() -> None:
    client = patch_client_method(
        make_kit_client(),
        "send_command_to_vending_machine",
        AsyncMock(return_value=0),
    )
    client = patch_client_method(
        client,
        "get_vending_machine_states",
        AsyncMock(
            return_value=VendingMachinesStatesCollection.model_validate(
                {"VendingMachines": [{"VendingMachineId": 100, "Statuses": "1"}]}
            )
        ),
    )

    adapter = ApplyMatrixToVendingMachineAdapter(
        kit_api_client=client,
        matrix_apply_timeout=0,
    )
    result = asyncio.run(adapter.execute(_sample_machine()))

    assert isinstance(result, CommandResult)
    assert result.success is True
    assert result.step == "verify_status"
