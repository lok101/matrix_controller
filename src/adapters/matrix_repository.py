from typing import Any

from src.external_clients.kit_api_client import KitAPIClient, Endpoints, RESULT_CODE_KEY, ResultCodes
from src.services.matrix_service import IMatrixRepository, Matrix


def _as_dict(matrix: Matrix) -> dict[str, Any]:
    return {
        'MatrixName': matrix.name,
        'Positions': [
            {
                'LineNumber': position.number,
                'ChoiceNumber': position.number,
                'GoodsName': position.product_name,
                'Price2': position.price,
                'Price': position.price,
                'MaxCount': position.capacity,
            }
            for position in matrix.cells
        ]
    }


class MatrixRepository(IMatrixRepository):
    def __init__(self, kit_api_client: KitAPIClient):
        self._kit_client = kit_api_client

    async def add(self, matrix: Matrix):
        response = await self._kit_client.post_request(
            endpoint=Endpoints.CREATE_MATRIX,
            payload=_as_dict(matrix)
        )
        result_code = response[RESULT_CODE_KEY]

        if result_code != ResultCodes.SUCCESS:
            print('Ошибка при добавлении матрицы.')
            # todo добавить вывод ответа от сервера.
