from src.external_clients.kit_api_client import KitAPIClient, Endpoints, RESULT_CODE_KEY, ResultCodes, \
    GOODS
from src.services.product_service import ITargetProductsRepo, Product


def _map_product_to_dict(product: Product) -> dict[str, str]:
    return {
        'GoodsName': product.name
    }


def _map_dict_to_product(record: dict) -> Product:
    return Product(
        name=record['GoodsName']
    )


class KitProductsRepo(ITargetProductsRepo):
    def __init__(self, kit_api_client: KitAPIClient):
        self._kit_client = kit_api_client

    async def add(self, product: Product):
        response = await self._kit_client.post_request(
            endpoint=Endpoints.ADD_GOOD,
            payload=_map_product_to_dict(product)
        )
        result_code = response[RESULT_CODE_KEY]

        if result_code == ResultCodes.SUCCESS:
            print('Добавлен товар: ', product.name)
        else:
            print('Товар не добавлен, result code - ', result_code)

    async def get_all(self) -> list[Product]:
        response = await self._kit_client.post_request(Endpoints.GET_GOODS)
        result_code = response[RESULT_CODE_KEY]

        if result_code != ResultCodes.SUCCESS:
            raise Exception(f'Не удалось получить данные от Kit API, код ответа - {result_code}')

        products = [_map_dict_to_product(item) for item in response[GOODS]]
        return products
