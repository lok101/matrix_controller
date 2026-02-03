from typing import Protocol

from new_src.domain.entites.matrix import Matrix


class GetAllMatricesPort(Protocol):
    async def execute(self) -> list[Matrix]: pass
