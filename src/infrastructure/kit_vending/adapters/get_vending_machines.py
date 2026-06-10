import logging
from dataclasses import dataclass

from beartype import beartype

from src.domain.entities.vending_machine import VendingMachine
from src.domain.ports.get_vending_machines import GetVendingMachinesPort
from src.domain.value_objects.ids.vending_machine_id import VMId
from src.domain.value_objects.ids.vending_machine_kit_id import VMKitId
from src.infrastructure.kit_vending.api.client import KitVendingAPIClient
from src.infrastructure.kit_vending.api.models.vending_machines import ActiveVendingMachineModel

logger = logging.getLogger(__name__)


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class GetVendingMachinesAdapter(GetVendingMachinesPort):
    kit_api_client: KitVendingAPIClient

    async def execute(self) -> list[VendingMachine]:
        collection = await self.kit_api_client.get_vending_machines()
        active = collection.get_active()
        result: list[VendingMachine] = []
        for item in active:
            mapped = self._map_to_domain(item)
            if mapped is not None:
                result.append(mapped)
        return result

    @staticmethod
    def _map_to_domain(model: ActiveVendingMachineModel) -> VendingMachine | None:
        if model.number is None:
            logger.warning("Для аппарата не удалось определить код: %s", model)
            return None
        return VendingMachine(
            id=VMId(model.number),
            kit_id=VMKitId(model.id),
            name=model.name,
        )
