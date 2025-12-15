from abc import ABC, abstractmethod

from src.application.dto.create_vending_machine_dto import CreateVendingMachineDTO
from src.domain.entities.vending_machine import VendingMachine


class VendingMachineRepository(ABC):
    @abstractmethod
    def create(self, dto: CreateVendingMachineDTO) -> VendingMachine: pass

    @abstractmethod
    def get_by_id(self, vm_id: int) -> VendingMachine | None: pass
