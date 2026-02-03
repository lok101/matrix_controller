from dataclasses import dataclass

from new_src.domain.entites.matrix import Matrix
from new_src.domain.entites.vending_machine import VendingMachine
from new_src.domain.exceptions import UploadMatrixError
from new_src.domain.ports.upload_machine_matrix import UploadMatrixPort
from new_src.domain.value_objects.ids.matrix_kit_id import MatrixKitId


@dataclass(frozen=True, slots=True, kw_only=True)
class UploadAndApplyMatrixUseCase:
    upload_matrix_port: UploadMatrixPort

    async def execute(self, matrix: Matrix, machines: list[VendingMachine]):
        if not machines:
            raise UploadMatrixError('No machine to upload')

        matrix_id: MatrixKitId | None = await self.upload_matrix_port.execute(matrix)

        if matrix_id is None:
            raise NotImplementedError()

        for machine in machines:
            # применить к аппарату
            # загрузить
            # применить
            # проверить

            pass
