from new_src.domain.entites.vending_machine import VendingMachine
from new_src.domain.repositories.vending_machine_repository import VendingMachineRepository
from new_src.domain.value_objects.ids.vending_machine_id import VMId


class InMemoryVendingMachineRepository(VendingMachineRepository):
    def __init__(self):
        self._storage: dict[VMId, VendingMachine] = {}

    def get_by_id(self, vm_id: VMId) -> VendingMachine | None:
        return self._storage.get(vm_id)

    def add(self, vending_machine: VendingMachine) -> None:
        self._storage[vending_machine.id] = vending_machine

    def get_size(self) -> int:
        return len(self._storage)

    def clear(self) -> None:
        self._storage.clear()
