from dataclasses import dataclass

from src.domain.value_objects.ids.vending_machine_id import VMId
from src.domain.value_objects.ids.vending_machine_kit_id import VMKitId


@dataclass(frozen=True)
class VendingMachine:
    id: VMId
    kit_id: VMKitId
    name: str
