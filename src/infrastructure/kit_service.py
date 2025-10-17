from src.kit_api_client import Endpoints, KitAPIClientImpl

_kit_client = KitAPIClientImpl()


async def add_matrix_to_kit_vending(matrix_name: str, products: list):
    data = {
        'MatrixName': matrix_name,
        'Positions': [product.as_kit_cell() for product in products]
    }

    await _kit_client.post_request(endpoint=Endpoints.CREATE_MATRIX, payload=data)
