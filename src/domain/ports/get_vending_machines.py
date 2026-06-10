from abc import ABC, abstractmethod

from src.domain.entities.vending_machine import VendingMachine


class GetVendingMachinesPort(ABC):
    @abstractmethod
    async def execute(self) -> list[VendingMachine]: ...
