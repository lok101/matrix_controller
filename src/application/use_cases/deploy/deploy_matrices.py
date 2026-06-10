import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from beartype import beartype

from src.application.use_cases.deploy.upload_and_apply_matrix import UploadAndApplyMatrixUseCase
from src.domain.entities.vending_machine import VendingMachine
from src.domain.exceptions import UploadMatrixError
from src.domain.repositories.matrix_repository import MatrixRepository
from src.domain.repositories.vending_machine_repository import VendingMachineRepository
from src.domain.value_objects.ids.vending_machine_id import VMId

logger = logging.getLogger(__name__)


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class DeployMatricesUseCase:
    matrix_repository: MatrixRepository
    vending_machine_repository: VendingMachineRepository
    upload_and_apply_matrix_uc: UploadAndApplyMatrixUseCase

    async def execute(
        self, selected_matrix_names: list[str], timestamp: datetime
    ) -> tuple[int, int, int]:
        if not selected_matrix_names:
            raise UploadMatrixError("Не выбрано ни одной матрицы для загрузки")

        tasks = []
        names: list[str] = []
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

            tasks.append(self.upload_and_apply_matrix_uc.execute(matrix, machines, timestamp))
            names.append(name)

        if not tasks:
            raise UploadMatrixError("Не удалось создать ни одной задачи для загрузки матриц")

        results = await asyncio.gather(*tasks, return_exceptions=True)

        matrices_success = 0
        matrices_failed = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                matrices_failed += 1
                logger.error("Ошибка при загрузке матрицы '%s': %s", names[i], result)
                continue

            success_count, failure_count = result
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
