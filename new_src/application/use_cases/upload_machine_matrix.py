from dataclasses import dataclass
from datetime import datetime

from new_src.domain.entites.matrix import Matrix
from new_src.domain.entites.vending_machine import VendingMachine
from new_src.domain.exceptions import UploadMatrixError
from new_src.domain.ports.apply_matrix_to_vending_machine import ApplyMatrixToVendingMachinePort
from new_src.domain.ports.bind_matrix_to_vending_machine import BindMatrixToVendingMachinePort
from new_src.domain.ports.download_matrix_to_vending_machine import DownloadMatrixToVendingMachinePort
from new_src.domain.ports.upload_machine_matrix import UploadMatrixPort
from new_src.domain.value_objects.ids.matrix_kit_id import MatrixKitId


@dataclass(frozen=True, slots=True, kw_only=True)
class UploadAndApplyMatrixUseCase:
    upload_matrix_port: UploadMatrixPort
    bind_matrix_to_machine_port: BindMatrixToVendingMachinePort
    download_matrix_to_machine_port: DownloadMatrixToVendingMachinePort
    apply_matrix_to_machine_port: ApplyMatrixToVendingMachinePort

    async def execute(self, matrix: Matrix, machines: list[VendingMachine], timestamp: datetime):
        if not machines:
            raise UploadMatrixError('Не переданы аппараты для применения матрицы.')

        matrix_id: MatrixKitId | None = await self.upload_matrix_port.execute(matrix, timestamp)

        if matrix_id is None:
            raise UploadMatrixError("Не удалось создать матрицу.")

        for machine in machines:

            bind_response = await self.bind_matrix_to_machine_port.execute(machine, matrix_id)
            download_response = await self.download_matrix_to_machine_port.execute(machine)
            apply_response = await self.apply_matrix_to_machine_port.execute(machine)

            # проверить
