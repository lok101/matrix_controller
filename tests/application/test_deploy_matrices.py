import asyncio
from datetime import datetime

from src.application.use_cases.deploy.deploy_matrices import DeployMatricesUseCase
from src.infrastructure.persistence.in_memory.matrix_repository import InMemoryMatrixRepository
from src.infrastructure.persistence.in_memory.vending_machine_repository import InMemoryVendingMachineRepository
from tests.application.conftest import FakeUploadAndApply, make_machine, make_matrix


def test_deploy_matrices_returns_success_and_failure_counts():
    matrix_repo = InMemoryMatrixRepository()
    matrix_repo.add(make_matrix("M1"))
    matrix_repo.add(make_matrix("M2"))
    vm_repo = InMemoryVendingMachineRepository()
    vm_repo.add(make_machine())

    uc = DeployMatricesUseCase(
        matrix_repository=matrix_repo,
        vending_machine_repository=vm_repo,
        upload_and_apply_matrix_uc=FakeUploadAndApply([(1, 0), (0, 1)]),
    )

    success, failed, skipped = asyncio.run(
        uc.execute(["M1", "M2"], datetime(2026, 6, 10))
    )
    assert success == 1
    assert failed == 1
    assert skipped == 0


def test_deploy_matrices_counts_skipped_when_matrix_not_found():
    matrix_repo = InMemoryMatrixRepository()
    matrix_repo.add(make_matrix("M1"))
    vm_repo = InMemoryVendingMachineRepository()
    vm_repo.add(make_machine())

    uc = DeployMatricesUseCase(
        matrix_repository=matrix_repo,
        vending_machine_repository=vm_repo,
        upload_and_apply_matrix_uc=FakeUploadAndApply([(1, 0)]),
    )

    success, failed, skipped = asyncio.run(
        uc.execute(["M1", "MISSING"], datetime(2026, 6, 10))
    )
    assert success == 1
    assert failed == 0
    assert skipped == 1
