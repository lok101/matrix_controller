from src.entities import AddGood, Matrix
from src.infrastructure.external_clients.kit_api_client import KitAPIClient, Endpoints, RESULT_CODE_KEY, ResultCodes, \
    GOODS, result_code_messages
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
        else:
            print('Товар не добавлен, result code - ', result_code)

    async def create_matrix(self, matrix: Matrix):
        response = await self._client.post_request(
            endpoint=Endpoints.CREATE_MATRIX,
            payload=matrix.as_dict()
        )
        result_code = response[RESULT_CODE_KEY]

    async def get_goods_collection(self) -> GoodsCollection:
        response = await self._client.post_request(Endpoints.GET_GOODS)
        result_code = response[RESULT_CODE_KEY]

        if result_code == ResultCodes.SUCCESS:
            goods = response[GOODS]
            return GoodsCollection.create(goods)

        else:
            message = result_code_messages.get()
            print('Список товаров не был получен, result code - ', result_code)
