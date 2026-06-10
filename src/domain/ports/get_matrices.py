from abc import ABC, abstractmethod

from src.domain.entities.matrix import Matrix


class GetAllMatricesPort(ABC):
    @abstractmethod
    def execute(self) -> list[Matrix]: ...
