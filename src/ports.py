from abc import abstractmethod, ABC
from typing import Mapping

from src.entities import AddGood, Matrix
from src.aggregates.goods_collection import GoodsCollection


class KitVendingPort(ABC):
    @abstractmethod
    async def add_good(self, good: AddGood): pass

    @abstractmethod
    async def create_matrix(self, matrix: Matrix): pass

    @abstractmethod
    async def get_goods_collection(self) -> GoodsCollection: pass


class GspreadPort(ABC):
    @abstractmethod
    def get_all_goods(self) -> list[Mapping]: pass

    @abstractmethod
    def get_matrix_goods(self, range_name: str) -> list[list[int, str, int, int]]: pass
