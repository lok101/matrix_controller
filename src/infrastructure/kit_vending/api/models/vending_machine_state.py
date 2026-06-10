from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field

from src.infrastructure.kit_vending.api.enums import VendingMachineStatus
from src.infrastructure.kit_vending.api.utils import extract_statuses


class VendingMachineStateModel(BaseModel):
    id: Annotated[int, Field(validation_alias="VendingMachineId")]
    statuses: Annotated[
        list[VendingMachineStatus],
        Field(validation_alias="Statuses"),
        BeforeValidator(extract_statuses),
    ]


class VendingMachinesStatesCollection(BaseModel):
    items: Annotated[list[VendingMachineStateModel], Field(validation_alias="VendingMachines")]

    def get_all(self) -> list[VendingMachineStateModel]:
        return self.items.copy()
