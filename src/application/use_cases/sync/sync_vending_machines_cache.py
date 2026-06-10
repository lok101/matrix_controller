import logging
from dataclasses import dataclass

from beartype import beartype

from src.domain.exceptions import SynchronizationError
from src.domain.ports.get_vending_machines import GetVendingMachinesPort
from src.domain.repositories.vending_machine_repository import VendingMachineRepository

logger = logging.getLogger(__name__)


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class SyncVendingMachinesCache:
    get_vending_machines: GetVendingMachinesPort
    vending_machine_repository: VendingMachineRepository

    async def execute(self) -> None:
        self.vending_machine_repository.clear()
        machines = await self.get_vending_machines.execute()
        if not machines:
            raise SynchronizationError("При попытке синхронизации не были получены аппараты.")
        for machine in machines:
            self.vending_machine_repository.add(machine)
        logger.info(
            "Синхронизация аппаратов завершена. Аппаратов в репозитории: %s.",
            self.vending_machine_repository.get_size(),
        )
