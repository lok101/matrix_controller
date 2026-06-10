from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

from src.infrastructure.kit_vending.api.enums import VendingMachineCommand, VendingMachineStatus
from src.infrastructure.kit_vending.api.exceptions import KitAPIResponseError, KitAPINetworkError
from src.infrastructure.kit_vending.api.models.vending_machine_state import VendingMachinesStatesCollection
from src.infrastructure.kit_vending.matrix_command_workflow import MatrixCommandWorkflow
from tests.infrastructure.kit_vending.conftest import make_kit_client, patch_client_method


def test_workflow_load_matrix_happy_path() -> None:
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
                {
                    "VendingMachines": [
                        {"VendingMachineId": 10, "Statuses": "21"},
                    ]
                }
            )
        ),
    )

    workflow = MatrixCommandWorkflow(
        kit_api_client=client,
        command=VendingMachineCommand.LOAD_MATRIX,
        status_predicate=lambda statuses: VendingMachineStatus.MATRIX_LOADED in statuses,
        wait_timeout_seconds=0,
        max_retry_attempts=3,
        max_command_send_attempts=3,
        retry_send_command_timeout_seconds=0,
    )

    result = asyncio.run(workflow.run(machine_kit_id=10, machine_name="[10] Кофе"))

    assert result.success is True
    assert result.step == "verify_status"
    assert result.attempts >= 1


def test_workflow_fails_after_max_retry_when_status_never_matches() -> None:
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
                {"VendingMachines": [{"VendingMachineId": 10, "Statuses": "1"}]}
            )
        ),
    )

    workflow = MatrixCommandWorkflow(
        kit_api_client=client,
        command=VendingMachineCommand.LOAD_MATRIX,
        status_predicate=lambda statuses: VendingMachineStatus.MATRIX_LOADED in statuses,
        wait_timeout_seconds=0,
        max_retry_attempts=2,
        max_command_send_attempts=3,
        retry_send_command_timeout_seconds=0,
    )

    result = asyncio.run(workflow.run(machine_kit_id=10, machine_name="[10] Кофе"))

    assert result.success is False
    assert result.step == "verify_status"
    assert client.send_command_to_vending_machine.await_count == 2


def test_workflow_retries_send_on_network_error() -> None:
    client = patch_client_method(
        make_kit_client(),
        "send_command_to_vending_machine",
        AsyncMock(
            side_effect=[
                KitAPINetworkError("timeout"),
                0,
            ]
        ),
    )
    client = patch_client_method(
        client,
        "get_vending_machine_states",
        AsyncMock(
            return_value=VendingMachinesStatesCollection.model_validate(
                {"VendingMachines": [{"VendingMachineId": 10, "Statuses": "21"}]}
            )
        ),
    )

    workflow = MatrixCommandWorkflow(
        kit_api_client=client,
        command=VendingMachineCommand.LOAD_MATRIX,
        status_predicate=lambda statuses: VendingMachineStatus.MATRIX_LOADED in statuses,
        wait_timeout_seconds=0,
        max_retry_attempts=1,
        max_command_send_attempts=3,
        retry_send_command_timeout_seconds=0,
    )

    result = asyncio.run(workflow.run(machine_kit_id=10, machine_name="[10] Кофе"))

    assert result.success is True
    assert client.send_command_to_vending_machine.await_count == 2


def test_workflow_does_not_retry_on_non_rate_limit_response_error() -> None:
    client = patch_client_method(
        make_kit_client(),
        "send_command_to_vending_machine",
        AsyncMock(side_effect=KitAPIResponseError("bad request", result_code=5)),
    )

    workflow = MatrixCommandWorkflow(
        kit_api_client=client,
        command=VendingMachineCommand.APPLY_MATRIX,
        status_predicate=lambda statuses: VendingMachineStatus.MATRIX_LOADED not in statuses,
        wait_timeout_seconds=0,
        max_retry_attempts=3,
        max_command_send_attempts=3,
        retry_send_command_timeout_seconds=0,
    )

    result = asyncio.run(workflow.run(machine_kit_id=10, machine_name="[10] Кофе"))

    assert result.success is False
    assert result.step == "send_command"
    assert client.send_command_to_vending_machine.await_count == 1
