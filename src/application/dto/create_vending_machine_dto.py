from dataclasses import dataclass


@dataclass(frozen=True)
class CreateVendingMachineDTO:
    id: int
    kit_id: int
    name: str
