from dataclasses import dataclass


@dataclass(frozen=True)
class VendingMachine:
    id: int
    kit_id: int
    name: str
