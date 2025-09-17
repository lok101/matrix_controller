from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Product:
    name: str


class SoursProductsRepo(ABC):
    @abstractmethod
    def get_all(self) -> list[Product]: pass


class TargetProductsRepo(ABC):
    @abstractmethod
    def get_all(self) -> list[Product]: pass

    @abstractmethod
    def add(self, product: Product): pass


class ProductsService:
    def __init__(self, source_repository: SoursProductsRepo, target_repository: TargetProductsRepo):
        self._source_repo = source_repository
        self._target_repo = target_repository

    async def sync_products(self):
        source_products = self._source_repo.get_all()
        already_exist_products = self._target_repo.get_all()
        need_add_products = set(source_products) - set(already_exist_products)

        for item in need_add_products:
            self._target_repo.add(item)
