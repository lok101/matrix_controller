from __future__ import annotations

from src.infrastructure.kit_vending.api.enums import VendingMachineStatus
from src.infrastructure.kit_vending.machine_deploy_task import (
    MachinePollSnapshot,
    is_apply_confirmed,
    is_load_confirmed,
)


def test_is_load_confirmed_when_matrix_loaded_status_present() -> None:
    snapshot = MachinePollSnapshot(
        found=True,
        statuses=[VendingMachineStatus.MATRIX_LOADED, VendingMachineStatus.NO_CONNECTION],
    )
    assert is_load_confirmed(snapshot) is True


def test_is_load_confirmed_when_matrix_loaded_status_absent() -> None:
    snapshot = MachinePollSnapshot(found=True, statuses=[VendingMachineStatus.NO_CONNECTION])
    assert is_load_confirmed(snapshot) is False


def test_is_load_confirmed_when_machine_not_in_response() -> None:
    snapshot = MachinePollSnapshot(found=False, statuses=[])
    assert is_load_confirmed(snapshot) is False


def test_is_load_confirmed_when_machine_in_response_with_empty_statuses() -> None:
    snapshot = MachinePollSnapshot(found=True, statuses=[])
    assert is_load_confirmed(snapshot) is False


def test_is_apply_confirmed_when_matrix_loaded_status_absent() -> None:
    snapshot = MachinePollSnapshot(found=True, statuses=[VendingMachineStatus.NO_CONNECTION])
    assert is_apply_confirmed(snapshot) is True


def test_is_apply_confirmed_when_matrix_loaded_status_present() -> None:
    snapshot = MachinePollSnapshot(found=True, statuses=[VendingMachineStatus.MATRIX_LOADED])
    assert is_apply_confirmed(snapshot) is False


def test_is_apply_confirmed_when_machine_in_response_with_empty_statuses() -> None:
    snapshot = MachinePollSnapshot(found=True, statuses=[])
    assert is_apply_confirmed(snapshot) is True


def test_is_apply_confirmed_when_machine_not_in_response() -> None:
    snapshot = MachinePollSnapshot(found=False, statuses=[])
    assert is_apply_confirmed(snapshot) is False
