import logging
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from beartype import beartype
from kit_api import KitVendingAPIClient, VendingMachinesCollection
from kit_api.models.vending_machines import ActiveVendingMachineModel

from new_src.application.exceptions import SynchronizationError
from new_src.domain.entites.vending_machine import VendingMachine
from new_src.domain.value_objects.ids.vending_machine_id import VMId
from new_src.domain.value_objects.ids.vending_machine_kit_id import VMKitId

logger = logging.getLogger("__main__")

@runtime_checkable
class VendingMachineCache(Protocol):
    def add(self, vending_machine: VendingMachine) -> None: pass

    def get_size(self) -> int: pass

    def clear(self) -> None: pass


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class SyncVendingMachinesCache:
    kit_api_client: KitVendingAPIClient

    vending_machine_repository: VendingMachineCache

    async def execute(self) -> None:
        self.vending_machine_repository.clear()
        machines_quantity: int = self.vending_machine_repository.get_size()
        logger.info(f"Репозиторий аппаратов очищен. Аппаратов в репозитории: {machines_quantity}.")

        machines_collection: VendingMachinesCollection = await self.kit_api_client.get_vending_machines()

        active_machines: list[ActiveVendingMachineModel] = machines_collection.get_active()

        if not active_machines:
            raise SynchronizationError("При попытке синхронизации не были получены аппараты.")

        for item in active_machines:
            vending_machine: VendingMachine | None = self._map_to_domain(item)

            if vending_machine is not None:
                self.vending_machine_repository.add(vending_machine)

        machines_quantity: int = self.vending_machine_repository.get_size()
        logger.info(f"Синхронизация аппаратов завершена. Аппаратов в репозитории: {machines_quantity}.")

    @staticmethod
    def _map_to_domain(model: ActiveVendingMachineModel) -> VendingMachine | None:
        if model.number is None:
            logger.warning(f"Для переданного аппарата не удалось определить код: {model}")
            return None

        machine_id: VMId = VMId(model.number)
        kit_id: VMKitId = VMKitId(model.id)
        name: str = model.name

        return VendingMachine(
            id=machine_id,
            kit_id=kit_id,
            name=name,
        )
