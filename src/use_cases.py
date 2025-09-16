from src.dtos import AddGood
from src.infrastructure.adapters.kit_vending_api_adapter import KitVendingAPIAdapter
from src.infrastructure.clients.kit_api_client import KitAPIClient, KitAPIClientImpl
from src.ports import KitVendingPort

_api_client: KitAPIClient = KitAPIClientImpl()
_goods_repository: KitVendingPort = KitVendingAPIAdapter(_api_client)


async def add_goods(goods: list[AddGood]):
    goods_collection = await _goods_repository.get_goods_collection()

    for good in goods:
        if not goods_collection.is_good_already_exist(good.name):
            await _goods_repository.add_good(good)
