from typing import Protocol, runtime_checkable

from new_src.domain.entites.matrix import Matrix


@runtime_checkable
class GetAllMatricesPort(Protocol):
    async def execute(self) -> list[Matrix]: pass
