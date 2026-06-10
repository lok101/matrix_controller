from __future__ import annotations

from src.infrastructure.kit_vending.api.enums import VendingMachineStatus
from src.infrastructure.kit_vending.api.models.vending_machine_state import (
    VendingMachineStateModel,
    VendingMachinesStatesCollection,
)
from src.infrastructure.kit_vending.api.models.vending_machines import (
    ActiveVendingMachineModel,
    VendingMachinesCollection,
)
from src.infrastructure.kit_vending.api.utils import extract_statuses, extract_vending_machine_id


def test_extract_statuses_parses_comma_separated_codes() -> None:
    result = extract_statuses("21,1,999")

    assert result == [VendingMachineStatus.MATRIX_LOADED, VendingMachineStatus.NO_CONNECTION]


def test_extract_statuses_empty_string_returns_empty_list() -> None:
    assert extract_statuses("") == []


def test_extract_vending_machine_id_from_bracketed_name() -> None:
    assert extract_vending_machine_id("[42] Кофе") == 42


def test_extract_vending_machine_id_returns_none_when_missing() -> None:
    assert extract_vending_machine_id("Без кода") is None


def test_vending_machines_collection_parses_active_machine() -> None:
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
    assert active[0].id == 100
    assert active[0].number == 7
    assert active[0].name == "[7] Кофе"


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
