from abc import ABC, abstractmethod

from new_src.domain.entites.vending_machine import VendingMachine


class VendingMachineRepository(ABC):
    @abstractmethod
    def get_by_name(self, machine_name: str) -> VendingMachine | None: pass
