from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, Field, model_validator

from src.infrastructure.kit_vending.api.utils import extract_vending_machine_id


class VendingMachineModel(BaseModel):
    id: Annotated[int, Field(validation_alias="VendingMachineId")]
    name: Annotated[str, Field(validation_alias="VendingMachineName")]
    matrix_id: Annotated[int | None, Field(validation_alias="GoodsMatrix")]
    number: Annotated[
        int | None,
        Field(validation_alias="VendingMachineName"),
        BeforeValidator(extract_vending_machine_id),
    ]
    company_id: Annotated[int, Field(validation_alias="CompanyId")]


class ActiveVendingMachineModel(VendingMachineModel):
    terminal_number: Annotated[int, Field(validation_alias="ModemSerialNumber")]


class NotActiveVendingMachineModel(VendingMachineModel):
    terminal_number: Annotated[None, Field(validation_alias="ModemSerialNumber")]


class VendingMachinesCollection(BaseModel):
    items: Annotated[
        list[ActiveVendingMachineModel | NotActiveVendingMachineModel],
        Field(validation_alias="VendingMachines"),
    ]

    @model_validator(mode="before")
    @classmethod
    def _create_typed_models(cls, data: Any) -> Any:
        if isinstance(data, dict) and "VendingMachines" in data:
            machines = []
            for machine_data in data["VendingMachines"]:
                if isinstance(machine_data, dict):
                    modem_serial = machine_data.get("ModemSerialNumber")
                    if modem_serial is not None:
                        machines.append(ActiveVendingMachineModel.model_validate(machine_data))
                    else:
                        machines.append(NotActiveVendingMachineModel.model_validate(machine_data))
                else:
                    machines.append(machine_data)
            data["VendingMachines"] = machines
        return data

    def get_all(self) -> list[VendingMachineModel]:
        return self.items.copy()

    def get_active(self) -> list[ActiveVendingMachineModel]:
        return [item for item in self.items if isinstance(item, ActiveVendingMachineModel)]
