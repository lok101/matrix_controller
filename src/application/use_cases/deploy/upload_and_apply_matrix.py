import logging
from dataclasses import dataclass
from datetime import datetime

from beartype import beartype

from src.domain.entities.matrix import Matrix
from src.domain.entities.vending_machine import VendingMachine
from src.domain.exceptions import UploadMatrixError
from src.domain.ports.apply_matrix_to_vending_machine import ApplyMatrixToVendingMachinePort
from src.domain.ports.bind_matrix_to_vending_machine import BindMatrixToVendingMachinePort
from src.domain.ports.download_matrix_to_vending_machine import DownloadMatrixToVendingMachinePort
from src.domain.ports.upload_machine_matrix import UploadMatrixPort
from src.domain.services.matrix_validator import MatrixValidator
from src.domain.value_objects.command_result import CommandResult
from src.domain.value_objects.ids.matrix_kit_id import MatrixKitId

logger = logging.getLogger(__name__)


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class UploadAndApplyMatrixUseCase:
    upload_matrix_port: UploadMatrixPort
    bind_matrix_to_machine_port: BindMatrixToVendingMachinePort
    download_matrix_to_machine_port: DownloadMatrixToVendingMachinePort
    apply_matrix_to_machine_port: ApplyMatrixToVendingMachinePort
    validate_matrices: bool = True

    async def execute(
        self, matrix: Matrix, machines: list[VendingMachine], timestamp: datetime
    ) -> tuple[int, int]:
        if not machines:
            raise UploadMatrixError("Не переданы аппараты для применения матрицы.")

        if self.validate_matrices:
            MatrixValidator.validate(matrix)

        matrix_id: MatrixKitId | None = await self.upload_matrix_port.execute(matrix, timestamp)
        if matrix_id is None:
            raise UploadMatrixError("Не удалось создать матрицу.")

        success_count = 0
        failure_count = 0

        for machine in machines:
            if not await self.bind_matrix_to_machine_port.execute(machine, matrix_id):
                failure_count += 1
                logger.critical(
                    "Не удалось привязать матрицу. Матрица: %s, аппарат: %s.",
                    matrix.name,
                    machine.name,
                )
                continue

            download_result: CommandResult = await self.download_matrix_to_machine_port.execute(
                machine
            )
            if not download_result.success:
                failure_count += 1
                logger.critical(
                    "Не удалось загрузить матрицу. Матрица: %s, аппарат: %s, "
                    "шаг: %s, попытка: %s, причина: %s.",
                    matrix.name,
                    machine.name,
                    download_result.step,
                    download_result.attempts,
                    download_result.message,
                )
                continue

            apply_result: CommandResult = await self.apply_matrix_to_machine_port.execute(machine)
            if not apply_result.success:
                failure_count += 1
                logger.critical(
                    "Не удалось применить матрицу. Матрица: %s, аппарат: %s, "
                    "шаг: %s, попытка: %s, причина: %s.",
                    matrix.name,
                    machine.name,
                    apply_result.step,
                    apply_result.attempts,
                    apply_result.message,
                )
                continue

            success_count += 1

        if failure_count == 0:
            logger.info(
                "Матрица '%s': все %s аппаратов обработаны успешно.",
                matrix.name,
                success_count,
            )
        elif success_count == 0:
            logger.critical(
                "Матрица '%s': полный провал — 0 из %s аппаратов.",
                matrix.name,
                len(machines),
            )
        else:
            logger.warning(
                "Матрица '%s': частичный успех — %s из %s аппаратов, ошибок: %s.",
                matrix.name,
                success_count,
                len(machines),
                failure_count,
            )

        return success_count, failure_count
