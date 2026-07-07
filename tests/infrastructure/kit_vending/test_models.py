from __future__ import annotations

import pytest

from src.infrastructure.kit_vending.api.enums import VendingMachineStatus
from src.infrastructure.kit_vending.api.models.vending_machine_state import (
    VendingMachineStateModel,
    VendingMachinesStatesCollection,
)
from src.infrastructure.kit_vending.api.models.vending_machines import (
    ActiveVendingMachineModel,
    NotActiveVendingMachineModel,
    VendingMachinesCollection,
)
from src.infrastructure.kit_vending.api.utils import (
    extract_statuses,
    extract_vending_machine_id,
    is_vending_machine_inactive,
)


def test_extract_statuses_parses_comma_separated_codes() -> None:
    result = extract_statuses("21,1,999")

    assert result == [VendingMachineStatus.MATRIX_LOADED, VendingMachineStatus.NO_CONNECTION]


def test_extract_statuses_empty_string_returns_empty_list() -> None:
    assert extract_statuses("") == []


def test_extract_vending_machine_id_from_bracketed_name() -> None:
    assert extract_vending_machine_id("[42] Кофе") == 42


def test_extract_vending_machine_id_returns_none_when_missing() -> None:
    assert extract_vending_machine_id("Без кода") is None


def test_is_vending_machine_inactive_detects_deactivation_marker() -> None:
    assert is_vending_machine_inactive("Кофе [ X ]") is True
    assert is_vending_machine_inactive("[X] отключён") is True
    assert is_vending_machine_inactive("аппарат [Х] кириллица") is True
    assert is_vending_machine_inactive("[ X] test") is True
    assert is_vending_machine_inactive("[X ] test") is True


def test_is_vending_machine_inactive_ignores_machine_number_brackets() -> None:
    assert is_vending_machine_inactive("[7] Кофе") is False
    assert is_vending_machine_inactive("[42] Кофе") is False


def test_is_vending_machine_inactive_active_names_without_marker() -> None:
    assert is_vending_machine_inactive("Кофе") is False


@pytest.mark.parametrize(
    "name",
    ["[7] Кофе", "Кофе"],
)
def test_vending_machines_collection_classifies_active_by_name(name: str) -> None:
    raw = {
        "VendingMachines": [
            {
                "VendingMachineId": 100,
                "VendingMachineName": name,
                "GoodsMatrix": 5,
                "CompanyId": 1,
            }
        ]
    }

    collection = VendingMachinesCollection.model_validate(raw)
    active = collection.get_active()

    assert len(active) == 1
    assert isinstance(active[0], ActiveVendingMachineModel)
    assert active[0].id == 100
    assert active[0].name == name


def test_vending_machines_collection_active_without_modem_serial_number() -> None:
    raw = {
        "VendingMachines": [
            {
                "VendingMachineId": 100,
                "VendingMachineName": "[7] Кофе",
                "GoodsMatrix": 5,
                "CompanyId": 1,
            }
        ]
    }

    collection = VendingMachinesCollection.model_validate(raw)
    active = collection.get_active()

    assert len(active) == 1
    assert isinstance(active[0], ActiveVendingMachineModel)
    assert active[0].number == 7
    assert active[0].name == "[7] Кофе"


@pytest.mark.parametrize(
    "name",
    [
        "Кофе [ X ]",
        "[X] отключён",
        "аппарат [Х] кириллица",
        "[ X] test",
        "[X ] test",
    ],
)
def test_vending_machines_collection_classifies_inactive_by_deactivation_marker(name: str) -> None:
    raw = {
        "VendingMachines": [
            {
                "VendingMachineId": 200,
                "VendingMachineName": name,
                "GoodsMatrix": None,
                "CompanyId": 1,
                "ModemSerialNumber": 12345,
            }
        ]
    }

    collection = VendingMachinesCollection.model_validate(raw)

    assert collection.get_active() == []
    assert len(collection.get_all()) == 1
    assert isinstance(collection.get_all()[0], NotActiveVendingMachineModel)


def test_vending_machines_collection_bracketed_number_stays_active_regression() -> None:
    raw = {
        "VendingMachines": [
            {
                "VendingMachineId": 100,
                "VendingMachineName": "[7] Кофе",
                "GoodsMatrix": 5,
                "CompanyId": 1,
                "ModemSerialNumber": 12345,
            }
        ]
    }

    collection = VendingMachinesCollection.model_validate(raw)
    active = collection.get_active()

    assert len(active) == 1
    assert isinstance(active[0], ActiveVendingMachineModel)
    assert active[0].number == 7


def test_vending_machine_state_model_parses_statuses() -> None:
    raw = {"VendingMachineId": 100, "Statuses": "21,1"}

    model = VendingMachineStateModel.model_validate(raw)

    assert model.id == 100
    assert model.statuses == [VendingMachineStatus.MATRIX_LOADED, VendingMachineStatus.NO_CONNECTION]


def test_vending_machine_states_collection_get_all() -> None:
    raw = {
        "VendingMachines": [
            {"VendingMachineId": 1, "Statuses": "21"},
            {"VendingMachineId": 2, "Statuses": "1"},
        ]
    }

    collection = VendingMachinesStatesCollection.model_validate(raw)

    assert len(collection.get_all()) == 2
