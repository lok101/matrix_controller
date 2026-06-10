from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from beartype import beartype

from src.domain.entities.vending_machine import VendingMachine
from src.domain.exceptions import UploadMatrixError
from src.domain.ports.batch_matrix_deploy import BatchDeployCoordinatorPort
from src.domain.repositories.matrix_repository import MatrixRepository
from src.domain.repositories.vending_machine_repository import VendingMachineRepository
from src.domain.value_objects.ids.vending_machine_id import VMId
from src.domain.value_objects.matrix_deploy_item import MatrixDeployItem

logger = logging.getLogger(__name__)


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class DeployMatricesUseCase:
    matrix_repository: MatrixRepository
    vending_machine_repository: VendingMachineRepository
    batch_deploy_coordinator: BatchDeployCoordinatorPort

    async def execute(
        self, selected_matrix_names: list[str], timestamp: datetime
    ) -> tuple[int, int, int]:
        if not selected_matrix_names:
            raise UploadMatrixError("Не выбрано ни одной матрицы для загрузки")

        items: list[MatrixDeployItem] = []
        skipped = 0

        for name in selected_matrix_names:
            matrix = self.matrix_repository.get_by_name(name)
            if matrix is None:
                logger.error("Матрица с именем '%s' не найдена", name)
                skipped += 1
                continue

            machines = self._get_vending_machines(matrix.vending_machines_ids)
            if not machines:
                logger.warning("Не найдено ни одной машины для матрицы '%s'", name)
                skipped += 1
                continue

            items.append(MatrixDeployItem(matrix=matrix, machines=machines))

        if not items:
            raise UploadMatrixError("Не удалось создать ни одной задачи для загрузки матриц")

        results = await self.batch_deploy_coordinator.deploy(items, timestamp)

        matrices_success = 0
        matrices_failed = 0

        for _matrix_name, success_count, failure_count in results:
            if failure_count == 0:
                matrices_success += 1
            elif success_count == 0:
                matrices_failed += 1
            else:
                matrices_success += 1

        return matrices_success, matrices_failed, skipped

    def _get_vending_machines(self, machines_ids: list[VMId]) -> list[VendingMachine]:
        res: list[VendingMachine] = []
        for machine_id in machines_ids:
            vm = self.vending_machine_repository.get_by_id(machine_id)
            if vm is None:
                logger.error("Не была получена машина с Id: %s.", machine_id.value)
                continue
            res.append(vm)
        return res
