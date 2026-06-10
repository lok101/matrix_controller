from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.value_objects.matrix_deploy_item import MatrixDeployItem


class BatchDeployCoordinatorPort(ABC):
    @abstractmethod
    async def deploy(
        self,
        items: list[MatrixDeployItem],
        timestamp: datetime,
    ) -> list[tuple[str, int, int]]: ...
