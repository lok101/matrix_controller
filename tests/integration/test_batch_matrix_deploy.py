from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from src.domain.value_objects.ids.matrix_kit_id import MatrixKitId
from src.domain.value_objects.ids.vending_machine_kit_id import VMKitId
from src.infrastructure.kit_vending.api.enums import ResultCode
from src.infrastructure.kit_vending.api.exceptions import KitAPIResponseError
from src.infrastructure.kit_vending.api.models.vending_machine_state import VendingMachinesStatesCollection
from src.infrastructure.kit_vending.batch_matrix_deploy_coordinator import BatchMatrixDeployCoordinator
from src.domain.value_objects.matrix_deploy_item import MatrixDeployItem
from tests.application.conftest import FakeBindPort, FakeUploadPort, make_machine, make_matrix
from tests.infrastructure.kit_vending.conftest import make_kit_client, patch_client_method


def _states(*entries: tuple[int, str]) -> VendingMachinesStatesCollection:
    return VendingMachinesStatesCollection.model_validate(
        {"VendingMachines": [{"VendingMachineId": vm_id, "Statuses": s} for vm_id, s in entries]}
    )


@pytest.mark.integration
def test_five_machines_status_21_on_poll_2_and_4() -> None:
    client = make_kit_client()
    client = patch_client_method(client, "send_command_to_vending_machine", AsyncMock(return_value=0))

    poll_responses = [
        _states((501, "1"), (502, "1"), (503, "1"), (504, "1"), (505, "1")),
        _states((501, "1"), (502, "21"), (503, "1"), (504, "1"), (505, "1")),
        _states((501, "21"), (502, "1"), (503, "1"), (504, "21"), (505, "1")),
        _states((501, "21"), (502, "21"), (503, "21"), (504, "21"), (505, "21")),
        _states((501, "21"), (502, "21"), (503, "21"), (504, "21"), (505, "21")),
        _states((501, "1"), (502, "1"), (503, "1"), (504, "1"), (505, "1")),
    ]
    client = patch_client_method(
        client,
        "get_vending_machine_states",
        AsyncMock(side_effect=poll_responses),
    )

    machines = [make_machine(name=f"VM-{i}") for i in range(501, 506)]
    for i, machine in enumerate(machines, start=501):
        object.__setattr__(machine, "kit_id", VMKitId(i))

    coordinator = BatchMatrixDeployCoordinator(
        kit_api_client=client,
        upload_matrix_port=FakeUploadPort(result=MatrixKitId(99)),
        bind_matrix_to_machine_port=FakeBindPort(),
        validate_matrices=False,
        load_timeout_seconds=300,
        apply_timeout_seconds=300,
        poll_interval_seconds=0,
        command_send_delay_seconds=0,
        retry_send_command_delay_seconds=0,
        poll_api_max_retries=10,
    )

    result = asyncio.run(
        coordinator.deploy(
            [MatrixDeployItem(matrix=make_matrix(), machines=machines)],
            datetime(2026, 6, 10, 9, 55),
        )
    )

    assert result == [("M1", 5, 0)]


@pytest.mark.integration
def test_rate_limit_on_poll_retries_timers_not_reset() -> None:
    client = make_kit_client()
    client = patch_client_method(client, "send_command_to_vending_machine", AsyncMock(return_value=0))
    client = patch_client_method(
        client,
        "get_vending_machine_states",
        AsyncMock(
            side_effect=[
                KitAPIResponseError("too many", result_code=ResultCode.TOO_MANY_REQUEST),
                _states((512, "21")),
                _states((512, "1")),
            ]
        ),
    )

    machine = make_machine()
    object.__setattr__(machine, "kit_id", VMKitId(512))

    coordinator = BatchMatrixDeployCoordinator(
        kit_api_client=client,
        upload_matrix_port=FakeUploadPort(result=MatrixKitId(99)),
        bind_matrix_to_machine_port=FakeBindPort(),
        validate_matrices=False,
        load_timeout_seconds=300,
        apply_timeout_seconds=300,
        poll_interval_seconds=0,
        command_send_delay_seconds=0,
        retry_send_command_delay_seconds=0,
        poll_api_max_retries=10,
    )

    result = asyncio.run(
        coordinator.deploy(
            [MatrixDeployItem(matrix=make_matrix(), machines=[machine])],
            datetime(2026, 6, 10),
        )
    )

    assert result == [("M1", 1, 0)]
