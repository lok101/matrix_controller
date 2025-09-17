from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Product:
    name: str

    def __hash__(self):
        return hash(self.name)


class ISoursProductsRepo(ABC):
    @abstractmethod
    def get_all(self) -> list[Product]: pass


class ITargetProductsRepo(ABC):
    @abstractmethod
    async def get_all(self) -> list[Product]: pass

    @abstractmethod
    async def add(self, product: Product): pass


class ProductService:
    def __init__(self, source_repository: ISoursProductsRepo, target_repository: ITargetProductsRepo):
        self._source_repo = source_repository
        self._target_repo = target_repository

    async def sync_products(self):
        source_products = self._source_repo.get_all()
        already_exist_products = await self._target_repo.get_all()
        need_add_products = set(source_products) - set(already_exist_products)

        for item in need_add_products:
            await self._target_repo.add(item)
