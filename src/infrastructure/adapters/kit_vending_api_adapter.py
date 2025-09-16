from src.dtos import AddGood
from src.infrastructure.clients.kit_api_client import KitAPIClient, Endpoints, RESULT_CODE_KEY, ResultCodes, GOODS
from src.ports import KitVendingPort
from src.aggregates.goods_collection import GoodsCollection


class KitVendingAPIAdapter(KitVendingPort):
    def __init__(self, kit_api_client: KitAPIClient):
        self._client = kit_api_client

    async def add_good(self, dto: AddGood):
        response = await self._client.post_request(
            endpoint=Endpoints.ADD_GOOD,
            payload=dto.model_dump(by_alias=True)
        )
        result_code = response[RESULT_CODE_KEY]
        if result_code == ResultCodes.SUCCESS:
            print('Добавлен товар: ', dto.name)

    async def get_goods_collection(self) -> GoodsCollection:
        response = await self._client.post_request(Endpoints.GET_GOODS)
        result_code = response[RESULT_CODE_KEY]

        if result_code == ResultCodes.SUCCESS:
            goods = response[GOODS]
            return GoodsCollection.create(goods)
