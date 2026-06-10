import asyncio

from src.application.use_cases.orchestration.run_deployment_job import RunDeploymentJobUseCase
from src.application.use_cases.sync.sync_all_caches import SyncAllCachesUseCase
from src.application.use_cases.sync.sync_matrices_cache import SyncMatricesCache
from src.application.use_cases.sync.sync_products_cache import SyncProductsCache
from src.application.use_cases.sync.sync_vending_machines_cache import SyncVendingMachinesCache
from src.domain.ports.matrix_selection import MatrixSelectionPort
from src.infrastructure.persistence.in_memory.job_run_repository import InMemoryJobRunRepository
from src.infrastructure.persistence.in_memory.matrix_repository import InMemoryMatrixRepository
from src.infrastructure.persistence.in_memory.product_repository import InMemoryProductRepository
from src.infrastructure.persistence.in_memory.vending_machine_repository import InMemoryVendingMachineRepository
from tests.application.conftest import (
    FakeBatchCoordinator,
    FakeDeployMatrices,
    FakeMatricesPort,
    FakeProductsPort,
    FakeSyncAllRaises,
    FakeVendingMachinesPort,
    make_matrix,
)


class FakeSelection(MatrixSelectionPort):
    async def select(self, available):
        return [m.name for m in available]


def test_run_deployment_job_creates_and_finalizes_job_run():
    job_repo = InMemoryJobRunRepository()
    matrix_repo = InMemoryMatrixRepository()
    matrix_repo.add(make_matrix())

    product_repo = InMemoryProductRepository()
    vm_repo = InMemoryVendingMachineRepository()

    sync_all = SyncAllCachesUseCase(
        sync_products=SyncProductsCache(get_products=FakeProductsPort(), product_repository=product_repo),
        sync_vending_machines=SyncVendingMachinesCache(
            get_vending_machines=FakeVendingMachinesPort(), vending_machine_repository=vm_repo
        ),
        sync_matrices=SyncMatricesCache(get_all_matrices=FakeMatricesPort(), matrix_repository=matrix_repo),
    )

    deploy = FakeDeployMatrices(
        return_value=(2, 0, 0),
        matrix_repository=matrix_repo,
        vending_machine_repository=vm_repo,
        batch_deploy_coordinator=FakeBatchCoordinator(),
    )

    uc = RunDeploymentJobUseCase(
        job_run_repository=job_repo,
        sync_all_caches=sync_all,
        matrix_selection=FakeSelection(),
        matrix_repository=matrix_repo,
        deploy_matrices=deploy,
    )

    job_run = asyncio.run(uc.execute(trigger="scheduled"))

    assert job_run.status == "completed"
    assert job_run.matrices_success == 2
    assert job_repo.get_by_id(job_run.id) is not None


def test_run_deployment_job_partial_when_matrices_skipped():
    job_repo = InMemoryJobRunRepository()
    matrix_repo = InMemoryMatrixRepository()
    matrix_repo.add(make_matrix("M1"))
    product_repo = InMemoryProductRepository()
    vm_repo = InMemoryVendingMachineRepository()

    sync_all = SyncAllCachesUseCase(
        sync_products=SyncProductsCache(get_products=FakeProductsPort(), product_repository=product_repo),
        sync_vending_machines=SyncVendingMachinesCache(
            get_vending_machines=FakeVendingMachinesPort(), vending_machine_repository=vm_repo
        ),
        sync_matrices=SyncMatricesCache(get_all_matrices=FakeMatricesPort(), matrix_repository=matrix_repo),
    )

    deploy = FakeDeployMatrices(
        return_value=(1, 0, 1),
        matrix_repository=matrix_repo,
        vending_machine_repository=vm_repo,
        batch_deploy_coordinator=FakeBatchCoordinator(),
    )

    uc = RunDeploymentJobUseCase(
        job_run_repository=job_repo,
        sync_all_caches=sync_all,
        matrix_selection=FakeSelection(),
        matrix_repository=matrix_repo,
        deploy_matrices=deploy,
    )

    job_run = asyncio.run(uc.execute(trigger="scheduled"))

    assert job_run.status == "partial"
    assert job_run.matrices_total == 1
    assert job_run.matrices_success == 1
    assert job_run.matrices_failed == 0
    assert job_run.error_summary is not None
    assert "Пропущено" in job_run.error_summary


def test_run_deployment_job_failed_when_sync_raises():
    job_repo = InMemoryJobRunRepository()
    matrix_repo = InMemoryMatrixRepository()

    uc = RunDeploymentJobUseCase(
        job_run_repository=job_repo,
        sync_all_caches=FakeSyncAllRaises(),
        matrix_selection=FakeSelection(),
        matrix_repository=matrix_repo,
        deploy_matrices=FakeDeployMatrices(
            return_value=(0, 0, 0),
            matrix_repository=matrix_repo,
            vending_machine_repository=InMemoryVendingMachineRepository(),
            batch_deploy_coordinator=FakeBatchCoordinator(),
        ),
    )

    job_run = asyncio.run(uc.execute(trigger="scheduled"))

    assert job_run.status == "failed"
    assert "sync failed" in (job_run.error_summary or "")


def test_run_deployment_job_failed_when_all_matrices_fail():
    job_repo = InMemoryJobRunRepository()
    matrix_repo = InMemoryMatrixRepository()
    matrix_repo.add(make_matrix())
    product_repo = InMemoryProductRepository()
    vm_repo = InMemoryVendingMachineRepository()

    sync_all = SyncAllCachesUseCase(
        sync_products=SyncProductsCache(get_products=FakeProductsPort(), product_repository=product_repo),
        sync_vending_machines=SyncVendingMachinesCache(
            get_vending_machines=FakeVendingMachinesPort(), vending_machine_repository=vm_repo
        ),
        sync_matrices=SyncMatricesCache(get_all_matrices=FakeMatricesPort(), matrix_repository=matrix_repo),
    )

    deploy = FakeDeployMatrices(
        return_value=(0, 2, 0),
        matrix_repository=matrix_repo,
        vending_machine_repository=vm_repo,
        batch_deploy_coordinator=FakeBatchCoordinator(),
    )

    uc = RunDeploymentJobUseCase(
        job_run_repository=job_repo,
        sync_all_caches=sync_all,
        matrix_selection=FakeSelection(),
        matrix_repository=matrix_repo,
        deploy_matrices=deploy,
    )

    job_run = asyncio.run(uc.execute(trigger="scheduled"))

    assert job_run.status == "failed"
    assert job_run.matrices_success == 0
    assert job_run.matrices_failed == 2
