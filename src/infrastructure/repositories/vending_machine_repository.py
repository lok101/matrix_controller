from dataclasses import asdict

from src.application.dto.create_vending_machine_dto import CreateVendingMachineDTO
from src.domain.entities.vending_machine import VendingMachine
from src.domain.repositories.vending_machine_repository import VendingMachineRepository


class InMemoryVendingMachineRepository(VendingMachineRepository):
    def __init__(self):
        self._storage = {}

    def create(self, dto: CreateVendingMachineDTO):
        key = dto.id

        if key in self._storage.keys():
            raise Exception(f"Аппарат  \"{dto.name}\" - уже существует.")

        vm = VendingMachine(**asdict(dto))

        self._storage[key] = vm

    def get_by_id(self, vm_id: int) -> VendingMachine | None:
        return self._storage.get(vm_id)
