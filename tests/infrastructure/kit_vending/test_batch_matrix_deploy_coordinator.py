from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock

from src.domain.entities.cell import MatrixCell
from src.domain.entities.matrix import Matrix
from src.domain.entities.product import Product
from src.domain.entities.vending_machine import VendingMachine
from src.domain.value_objects.ids.matrix_kit_id import MatrixKitId
from src.domain.value_objects.ids.product_id import ProductId
from src.domain.value_objects.ids.vending_machine_id import VMId
from src.domain.value_objects.ids.vending_machine_kit_id import VMKitId
from src.domain.value_objects.money import Money
from src.infrastructure.kit_vending.api.enums import VendingMachineCommand
from src.infrastructure.kit_vending.api.exceptions import KitAPINetworkError
from src.infrastructure.kit_vending.api.models.vending_machine_state import VendingMachinesStatesCollection
from src.infrastructure.kit_vending.batch_matrix_deploy_coordinator import BatchMatrixDeployCoordinator
from src.domain.value_objects.matrix_deploy_item import MatrixDeployItem
from tests.application.conftest import FakeBindPort, FakeUploadPort
from tests.infrastructure.kit_vending.conftest import make_kit_client, patch_client_method


def _make_matrix(name: str = "M1") -> Matrix:
    product = Product(id=ProductId(1), name="Cola", purchase_price=Money(rubles=50))
    cell = MatrixCell(line_number=1, product=product, price=Money(rubles=100))
    return Matrix(name=name, cells=[cell], vending_machines_ids=[VMId(101)])


def _make_machine(kit_id: int = 512, name: str = "[512] Общежитие") -> VendingMachine:
    return VendingMachine(id=VMId(101), kit_id=VMKitId(kit_id), name=name)


def _states(*entries: tuple[int, str]) -> VendingMachinesStatesCollection:
    return VendingMachinesStatesCollection.model_validate(
        {"VendingMachines": [{"VendingMachineId": vm_id, "Statuses": statuses} for vm_id, statuses in entries]}
    )


def test_phase_prepare_sends_load_and_throttles_commands() -> None:
    client = make_kit_client()
    send_mock = AsyncMock(return_value=0)
    client = patch_client_method(client, "send_command_to_vending_machine", send_mock)
    states_mock = AsyncMock(
        side_effect=[
            _states((512, "21"), (505, "21")),
            _states((512, "1"), (505, "1")),
        ]
    )
    client = patch_client_method(client, "get_vending_machine_states", states_mock)

    upload = FakeUploadPort(result=MatrixKitId(42))
    bind = FakeBindPort()
    coordinator = BatchMatrixDeployCoordinator(
        kit_api_client=client,
        upload_matrix_port=upload,
        bind_matrix_to_machine_port=bind,
        validate_matrices=False,
        load_timeout_seconds=300,
        apply_timeout_seconds=300,
        poll_interval_seconds=0,
        command_send_delay_seconds=0,
        retry_send_command_delay_seconds=0,
        poll_api_max_retries=3,
    )

    result = asyncio.run(
        coordinator.deploy(
            [MatrixDeployItem(matrix=_make_matrix(), machines=[_make_machine(512), _make_machine(505, "[505]")])],
            datetime(2026, 6, 10, 14, 48),
        )
    )

    assert send_mock.await_count == 4
    assert send_mock.await_args_list[0].kwargs["command"] == VendingMachineCommand.LOAD_MATRIX
    assert send_mock.await_args_list[2].kwargs["command"] == VendingMachineCommand.APPLY_MATRIX
    assert result == [("M1", 2, 0)]
    assert bind.calls == 2


def test_batch_poll_uses_single_get_vm_states_per_cycle() -> None:
    client = make_kit_client()
    client = patch_client_method(
        client,
        "send_command_to_vending_machine",
        AsyncMock(return_value=0),
    )
    states_mock = AsyncMock(
        side_effect=[
            _states((512, "1"), (505, "1"), (503, "1")),
            _states((512, "21"), (505, "1"), (503, "1")),
            _states((512, "21"), (505, "21"), (503, "1")),
            _states((512, "21"), (505, "21"), (503, "21")),
            _states((512, "21"), (505, "21"), (503, "21")),
            _states((512, "1"), (505, "1"), (503, "1")),
        ]
    )
    client = patch_client_method(client, "get_vending_machine_states", states_mock)

    coordinator = BatchMatrixDeployCoordinator(
        kit_api_client=client,
        upload_matrix_port=FakeUploadPort(result=MatrixKitId(42)),
        bind_matrix_to_machine_port=FakeBindPort(),
        validate_matrices=False,
        load_timeout_seconds=300,
        apply_timeout_seconds=300,
        poll_interval_seconds=0,
        command_send_delay_seconds=0,
        retry_send_command_delay_seconds=0,
        poll_api_max_retries=3,
    )
    machines = [
        _make_machine(512),
        _make_machine(505, "[505]"),
        _make_machine(503, "[503]"),
    ]

    asyncio.run(
        coordinator.deploy(
            [MatrixDeployItem(matrix=_make_matrix(), machines=machines)],
            datetime(2026, 6, 10),
        )
    )

    assert states_mock.await_count == 6


def test_one_machine_load_timeout_does_not_block_apply_for_others() -> None:
    client = make_kit_client()
    client = patch_client_method(
        client,
        "send_command_to_vending_machine",
        AsyncMock(return_value=0),
    )
    states_mock = AsyncMock(
        side_effect=[
            _states((512, "21"), (505, "1")),
            _states((512, "1"), (505, "1")),
        ]
    )
    client = patch_client_method(client, "get_vending_machine_states", states_mock)

    coordinator = BatchMatrixDeployCoordinator(
        kit_api_client=client,
        upload_matrix_port=FakeUploadPort(result=MatrixKitId(42)),
        bind_matrix_to_machine_port=FakeBindPort(),
        validate_matrices=False,
        load_timeout_seconds=0,
        apply_timeout_seconds=300,
        poll_interval_seconds=0,
        command_send_delay_seconds=0,
        retry_send_command_delay_seconds=0,
        poll_api_max_retries=3,
    )

    result = asyncio.run(
        coordinator.deploy(
            [
                MatrixDeployItem(
                    matrix=_make_matrix(),
                    machines=[_make_machine(512), _make_machine(505, "[505]")],
                )
            ],
            datetime(2026, 6, 10),
        )
    )

    assert result == [("M1", 1, 1)]


def test_bind_failure_marks_machine_failed_others_continue() -> None:
    client = make_kit_client()
    client = patch_client_method(client, "send_command_to_vending_machine", AsyncMock(return_value=0))
    client = patch_client_method(
        client,
        "get_vending_machine_states",
        AsyncMock(side_effect=[_states((505, "21")), _states((505, "1"))]),
    )

    class SelectiveBind(FakeBindPort):
        async def execute(self, vending_machine, matrix_kit_id):
            self.calls += 1
            return vending_machine.kit_id.value == 505

    coordinator = BatchMatrixDeployCoordinator(
        kit_api_client=client,
        upload_matrix_port=FakeUploadPort(result=MatrixKitId(42)),
        bind_matrix_to_machine_port=SelectiveBind(),
        validate_matrices=False,
        load_timeout_seconds=300,
        apply_timeout_seconds=300,
        poll_interval_seconds=0,
        command_send_delay_seconds=0,
        retry_send_command_delay_seconds=0,
        poll_api_max_retries=3,
    )

    result = asyncio.run(
        coordinator.deploy(
            [
                MatrixDeployItem(
                    matrix=_make_matrix(),
                    machines=[_make_machine(512), _make_machine(505, "[505]")],
                )
            ],
            datetime(2026, 6, 10),
        )
    )

    assert result == [("M1", 1, 1)]


def test_poll_retries_on_api_error_without_resetting_deadline() -> None:
    client = make_kit_client()
    client = patch_client_method(client, "send_command_to_vending_machine", AsyncMock(return_value=0))
    states_mock = AsyncMock(
        side_effect=[
            KitAPINetworkError("timeout"),
            _states((512, "21")),
            _states((512, "1")),
        ]
    )
    client = patch_client_method(client, "get_vending_machine_states", states_mock)

    coordinator = BatchMatrixDeployCoordinator(
        kit_api_client=client,
        upload_matrix_port=FakeUploadPort(result=MatrixKitId(42)),
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
            [MatrixDeployItem(matrix=_make_matrix(), machines=[_make_machine()])],
            datetime(2026, 6, 10),
        )
    )

    assert result == [("M1", 1, 0)]
    assert states_mock.await_count == 3


def test_upload_failure_marks_matrix_failed_others_continue() -> None:
    class UploadFailM2(FakeUploadPort):
        async def execute(self, matrix: Matrix, timestamp: datetime) -> MatrixKitId | None:
            if matrix.name == "M2":
                return None
            return MatrixKitId(42)

    client = make_kit_client()
    client = patch_client_method(client, "send_command_to_vending_machine", AsyncMock(return_value=0))
    client = patch_client_method(
        client,
        "get_vending_machine_states",
        AsyncMock(side_effect=[_states((512, "21")), _states((512, "1"))]),
    )

    coordinator = BatchMatrixDeployCoordinator(
        kit_api_client=client,
        upload_matrix_port=UploadFailM2(),
        bind_matrix_to_machine_port=FakeBindPort(),
        validate_matrices=False,
        load_timeout_seconds=300,
        apply_timeout_seconds=300,
        poll_interval_seconds=0,
        command_send_delay_seconds=0,
        retry_send_command_delay_seconds=0,
        poll_api_max_retries=3,
    )

    result = asyncio.run(
        coordinator.deploy(
            [
                MatrixDeployItem(matrix=_make_matrix("M1"), machines=[_make_machine(512)]),
                MatrixDeployItem(matrix=_make_matrix("M2"), machines=[_make_machine(505, "[505]")]),
            ],
            datetime(2026, 6, 10),
        )
    )

    assert result == [("M1", 1, 0), ("M2", 0, 1)]


def test_same_kit_id_in_two_matrices_does_not_collide() -> None:
    shared_kit_id = 512
    machine_m1 = _make_machine(shared_kit_id, "[512] M1")
    machine_m2 = _make_machine(shared_kit_id, "[512] M2")

    client = make_kit_client()
    client = patch_client_method(client, "send_command_to_vending_machine", AsyncMock(return_value=0))
    client = patch_client_method(
        client,
        "get_vending_machine_states",
        AsyncMock(
            side_effect=[
                _states((512, "21")),
                _states((512, "1")),
            ]
        ),
    )

    coordinator = BatchMatrixDeployCoordinator(
        kit_api_client=client,
        upload_matrix_port=FakeUploadPort(result=MatrixKitId(42)),
        bind_matrix_to_machine_port=FakeBindPort(),
        validate_matrices=False,
        load_timeout_seconds=300,
        apply_timeout_seconds=300,
        poll_interval_seconds=0,
        command_send_delay_seconds=0,
        retry_send_command_delay_seconds=0,
        poll_api_max_retries=3,
    )

    result = asyncio.run(
        coordinator.deploy(
            [
                MatrixDeployItem(matrix=_make_matrix("M1"), machines=[machine_m1]),
                MatrixDeployItem(matrix=_make_matrix("M2"), machines=[machine_m2]),
            ],
            datetime(2026, 6, 10),
        )
    )

    assert result == [("M1", 1, 0), ("M2", 1, 0)]
    assert client.send_command_to_vending_machine.await_count == 4


def test_poll_api_transient_failure_retries_next_cycle() -> None:
    client = make_kit_client()
    client = patch_client_method(client, "send_command_to_vending_machine", AsyncMock(return_value=0))
    states_mock = AsyncMock(
        side_effect=[
            KitAPINetworkError("down"),
            KitAPINetworkError("down"),
            _states((512, "21")),
            _states((512, "1")),
        ]
    )
    client = patch_client_method(client, "get_vending_machine_states", states_mock)

    coordinator = BatchMatrixDeployCoordinator(
        kit_api_client=client,
        upload_matrix_port=FakeUploadPort(result=MatrixKitId(42)),
        bind_matrix_to_machine_port=FakeBindPort(),
        validate_matrices=False,
        load_timeout_seconds=300,
        apply_timeout_seconds=300,
        poll_interval_seconds=0,
        command_send_delay_seconds=0,
        retry_send_command_delay_seconds=0,
        poll_api_max_retries=2,
    )

    result = asyncio.run(
        coordinator.deploy(
            [MatrixDeployItem(matrix=_make_matrix(), machines=[_make_machine()])],
            datetime(2026, 6, 10),
        )
    )

    assert result == [("M1", 1, 0)]
    assert states_mock.await_count == 4


def test_poll_api_persistent_error_fails_on_load_timeout(monkeypatch) -> None:
    t_start = datetime(2026, 6, 10, 12, 0, 0)
    t_late = datetime(2026, 6, 10, 12, 2, 0)

    class _DatetimeProxy:
        _first = True

        @staticmethod
        def now(tz=None) -> datetime:
            if _DatetimeProxy._first:
                _DatetimeProxy._first = False
                return t_start
            return t_late

    import src.infrastructure.kit_vending.batch_matrix_deploy_coordinator as coord

    monkeypatch.setattr(coord, "datetime", _DatetimeProxy)

    client = make_kit_client()
    client = patch_client_method(client, "send_command_to_vending_machine", AsyncMock(return_value=0))
    client = patch_client_method(
        client,
        "get_vending_machine_states",
        AsyncMock(side_effect=KitAPINetworkError("down")),
    )

    coordinator = BatchMatrixDeployCoordinator(
        kit_api_client=client,
        upload_matrix_port=FakeUploadPort(result=MatrixKitId(42)),
        bind_matrix_to_machine_port=FakeBindPort(),
        validate_matrices=False,
        load_timeout_seconds=60,
        apply_timeout_seconds=300,
        poll_interval_seconds=0,
        command_send_delay_seconds=0,
        retry_send_command_delay_seconds=0,
        poll_api_max_retries=2,
    )

    result = asyncio.run(
        coordinator.deploy(
            [MatrixDeployItem(matrix=_make_matrix(), machines=[_make_machine()])],
            datetime(2026, 6, 10),
        )
    )

    assert result == [("M1", 0, 1)]
    assert client.get_vending_machine_states.await_count == 2


def test_send_command_retry_waits_between_attempts(monkeypatch) -> None:
    sleep_calls: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    client = make_kit_client()
    client = patch_client_method(
        client,
        "send_command_to_vending_machine",
        AsyncMock(
            side_effect=[
                KitAPINetworkError("timeout"),
                0,
                0,
            ]
        ),
    )
    client = patch_client_method(
        client,
        "get_vending_machine_states",
        AsyncMock(side_effect=[_states((512, "21")), _states((512, "1"))]),
    )

    coordinator = BatchMatrixDeployCoordinator(
        kit_api_client=client,
        upload_matrix_port=FakeUploadPort(result=MatrixKitId(42)),
        bind_matrix_to_machine_port=FakeBindPort(),
        validate_matrices=False,
        load_timeout_seconds=300,
        apply_timeout_seconds=300,
        poll_interval_seconds=0,
        command_send_delay_seconds=0,
        retry_send_command_delay_seconds=10,
        poll_api_max_retries=3,
    )

    asyncio.run(
        coordinator.deploy(
            [MatrixDeployItem(matrix=_make_matrix(), machines=[_make_machine()])],
            datetime(2026, 6, 10),
        )
    )

    assert 10 in sleep_calls


def test_send_command_no_sleep_after_final_retry_failure(monkeypatch) -> None:
    sleep_calls: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    client = make_kit_client()
    client = patch_client_method(
        client,
        "send_command_to_vending_machine",
        AsyncMock(side_effect=KitAPINetworkError("timeout")),
    )

    coordinator = BatchMatrixDeployCoordinator(
        kit_api_client=client,
        upload_matrix_port=FakeUploadPort(result=MatrixKitId(42)),
        bind_matrix_to_machine_port=FakeBindPort(),
        validate_matrices=False,
        load_timeout_seconds=300,
        apply_timeout_seconds=300,
        poll_interval_seconds=0,
        command_send_delay_seconds=0,
        retry_send_command_delay_seconds=10,
        poll_api_max_retries=3,
        max_command_send_attempts=3,
    )

    result = asyncio.run(
        coordinator.deploy(
            [MatrixDeployItem(matrix=_make_matrix(), machines=[_make_machine()])],
            datetime(2026, 6, 10),
        )
    )

    assert result == [("M1", 0, 1)]
    assert sleep_calls.count(10) == 2
