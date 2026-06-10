from abc import ABC, abstractmethod

from src.domain.entities.vending_machine import VendingMachine
from src.domain.value_objects.ids.vending_machine_id import VMId


class VendingMachineRepository(ABC):
    @abstractmethod
    def get_by_id(self, machine_id: VMId) -> VendingMachine | None: ...

    @abstractmethod
    def add(self, vending_machine: VendingMachine) -> None: ...

    @abstractmethod
    def clear(self) -> None: ...

    @abstractmethod
    def get_size(self) -> int: ...
