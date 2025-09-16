from abc import abstractmethod, ABC

from src.dtos import AddGood
from src.aggregates.goods_collection import GoodsCollection


class KitVendingPort(ABC):
    @abstractmethod
    async def add_good(self, good: AddGood): pass

    @abstractmethod
    async def get_goods_collection(self) -> GoodsCollection: pass
