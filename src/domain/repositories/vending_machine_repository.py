from abc import ABC, abstractmethod

from src.domain.entites.vending_machine import VendingMachine
from src.domain.value_objects.ids.vending_machine_id import VMId


class VendingMachineRepository(ABC):
    @abstractmethod
    def get_by_id(self, vm_id: VMId) -> VendingMachine | None: pass
