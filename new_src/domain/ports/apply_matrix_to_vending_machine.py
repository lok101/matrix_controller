from abc import ABC, abstractmethod

from new_src.domain.entites.vending_machine import VendingMachine


class ApplyMatrixToVendingMachinePort(ABC):
    @abstractmethod
    async def execute(self, vending_machine: VendingMachine): pass
