from abc import ABC, abstractmethod

from src.domain.entites.vending_machine import VendingMachine


class DownloadMatrixToVendingMachinePort(ABC):
    @abstractmethod
    async def execute(self, vending_machine: VendingMachine): pass
