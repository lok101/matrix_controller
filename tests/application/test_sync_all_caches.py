import asyncio

import pytest

from src.application.use_cases.sync.sync_all_caches import SyncAllCachesUseCase
from src.application.use_cases.sync.sync_matrices_cache import SyncMatricesCache
from src.application.use_cases.sync.sync_products_cache import SyncProductsCache
from src.application.use_cases.sync.sync_vending_machines_cache import SyncVendingMachinesCache
from src.domain.exceptions import SynchronizationError
from src.infrastructure.persistence.in_memory.matrix_repository import InMemoryMatrixRepository
from src.infrastructure.persistence.in_memory.product_repository import InMemoryProductRepository
from src.infrastructure.persistence.in_memory.vending_machine_repository import InMemoryVendingMachineRepository
from tests.application.conftest import (
    FakeMatricesPort,
    FakeProductsPort,
    FakeProductsPortEmpty,
    FakeVendingMachinesPort,
)


def test_sync_all_caches_populates_repositories():
    product_repo = InMemoryProductRepository()
    matrix_repo = InMemoryMatrixRepository()
    vm_repo = InMemoryVendingMachineRepository()

    sync_all = SyncAllCachesUseCase(
        sync_products=SyncProductsCache(
            get_products=FakeProductsPort(),
            product_repository=product_repo,
        ),
        sync_vending_machines=SyncVendingMachinesCache(
            get_vending_machines=FakeVendingMachinesPort(),
            vending_machine_repository=vm_repo,
        ),
        sync_matrices=SyncMatricesCache(
            get_all_matrices=FakeMatricesPort(),
            matrix_repository=matrix_repo,
        ),
    )

    asyncio.run(sync_all.execute())

    assert product_repo.get_size() == 1
    assert vm_repo.get_size() == 1
    assert matrix_repo.get_size() == 1


def test_sync_all_caches_raises_when_products_empty():
    product_repo = InMemoryProductRepository()
    matrix_repo = InMemoryMatrixRepository()
    vm_repo = InMemoryVendingMachineRepository()

    sync_all = SyncAllCachesUseCase(
        sync_products=SyncProductsCache(
            get_products=FakeProductsPortEmpty(),
            product_repository=product_repo,
        ),
        sync_vending_machines=SyncVendingMachinesCache(
            get_vending_machines=FakeVendingMachinesPort(),
            vending_machine_repository=vm_repo,
        ),
        sync_matrices=SyncMatricesCache(
            get_all_matrices=FakeMatricesPort(),
            matrix_repository=matrix_repo,
        ),
    )

    with pytest.raises(SynchronizationError, match="не были получены товары"):
        asyncio.run(sync_all.execute())
