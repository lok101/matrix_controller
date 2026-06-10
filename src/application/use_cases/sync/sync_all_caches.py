from dataclasses import dataclass

from beartype import beartype

from src.application.use_cases.sync.sync_matrices_cache import SyncMatricesCache
from src.application.use_cases.sync.sync_products_cache import SyncProductsCache
from src.application.use_cases.sync.sync_vending_machines_cache import SyncVendingMachinesCache


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class SyncAllCachesUseCase:
    sync_products: SyncProductsCache
    sync_vending_machines: SyncVendingMachinesCache
    sync_matrices: SyncMatricesCache

    async def execute(self) -> None:
        self.sync_products.execute()
        await self.sync_vending_machines.execute()
        await self.sync_matrices.execute()
