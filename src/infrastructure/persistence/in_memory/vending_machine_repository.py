from src.domain.entities.vending_machine import VendingMachine
from src.domain.repositories.vending_machine_repository import VendingMachineRepository
from src.domain.value_objects.ids.vending_machine_id import VMId


class InMemoryVendingMachineRepository(VendingMachineRepository):
    def __init__(self) -> None:
        self._storage: dict[int, VendingMachine] = {}

    def get_by_id(self, machine_id: VMId) -> VendingMachine | None:
        return self._storage.get(machine_id.value)

    def add(self, vending_machine: VendingMachine) -> None:
        self._storage[vending_machine.id.value] = vending_machine

    def clear(self) -> None:
        self._storage.clear()

    def get_size(self) -> int:
        return len(self._storage)
