from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.entites.matrix import Matrix
from src.domain.value_objects.ids.matrix_kit_id import MatrixKitId


class UploadMatrixPort(ABC):
    @abstractmethod
    async def execute(self, matrix: Matrix, timestamp: datetime) -> MatrixKitId | None: pass
