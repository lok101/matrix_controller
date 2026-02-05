from datetime import datetime
from typing import Protocol

from new_src.domain.entites.matrix import Matrix
from new_src.domain.value_objects.ids.matrix_kit_id import MatrixKitId


class UploadMatrixPort(Protocol):
    async def execute(self, matrix: Matrix, timestamp: datetime) -> MatrixKitId | None: pass
