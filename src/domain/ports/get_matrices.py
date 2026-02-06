from typing import Protocol, runtime_checkable

from src.domain.entites.matrix import Matrix


@runtime_checkable
class GetAllMatricesPort(Protocol):
    def execute(self) -> list[Matrix]: pass
