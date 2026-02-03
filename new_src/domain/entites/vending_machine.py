from dataclasses import dataclass

from new_src.domain.value_objects.ids.vending_machine_kit_id import VMKitId


@dataclass(frozen=True)
class VendingMachine:
    kit_id: VMKitId
    name: str
