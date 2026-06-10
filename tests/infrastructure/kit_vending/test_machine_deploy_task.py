from __future__ import annotations

from src.infrastructure.kit_vending.api.enums import VendingMachineStatus
from src.infrastructure.kit_vending.machine_deploy_task import (
    is_apply_confirmed,
    is_load_confirmed,
)


def test_is_load_confirmed_when_matrix_loaded_status_present() -> None:
    assert is_load_confirmed([VendingMachineStatus.MATRIX_LOADED, VendingMachineStatus.NO_CONNECTION]) is True


def test_is_load_confirmed_when_matrix_loaded_status_absent() -> None:
    assert is_load_confirmed([VendingMachineStatus.NO_CONNECTION]) is False


def test_is_apply_confirmed_when_matrix_loaded_status_absent() -> None:
    assert is_apply_confirmed([VendingMachineStatus.NO_CONNECTION]) is True


def test_is_apply_confirmed_when_matrix_loaded_status_present() -> None:
    assert is_apply_confirmed([VendingMachineStatus.MATRIX_LOADED]) is False


def test_is_apply_confirmed_when_statuses_empty() -> None:
    assert is_apply_confirmed([]) is False
