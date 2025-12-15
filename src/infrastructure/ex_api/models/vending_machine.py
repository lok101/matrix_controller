from typing import Annotated

from pydantic import BaseModel, Field

from src.application.dto.create_vending_machine_dto import CreateVendingMachineDTO


class VendingMachineModel(BaseModel):
    id: Annotated[int, Field(validation_alias="VendingMachineId")]
    name: Annotated[str, Field(validation_alias="VendingMachineName")]
    matrix_id: Annotated[int | None, Field(validation_alias="GoodsMatrix")]
    number: Annotated[int, Field(validation_alias="AutomatNumber")]


class VendingMachinesCollection(BaseModel):
    items: Annotated[list[VendingMachineModel], Field(validation_alias="VendingMachines")]

    def as_dtos(self) -> list[CreateVendingMachineDTO]:
        return [
            CreateVendingMachineDTO(
                kit_id=item.id,
                name=item.name,
                id=item.number,
            ) for item in self.items
        ]
