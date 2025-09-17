from typing import Mapping

from src.entities import AddGood, Matrix, Position
from src.enums import SnackMatrix
from src.infrastructure.adapters.gspread_adapter import GspreadAdapter
from src.infrastructure.adapters.kit_vending_api_adapter import KitVendingAPIAdapter
from src.infrastructure.external_clients.gspread_client import GspreadClientImpl, GspreadClient
from src.infrastructure.external_clients.kit_api_client import KitAPIClient, KitAPIClientImpl
from src.ports import KitVendingPort, GspreadPort

_kit_api_client: KitAPIClient = KitAPIClientImpl()
_gspread_client: GspreadClient = GspreadClientImpl()

_kit_port: KitVendingPort = KitVendingAPIAdapter(_kit_api_client)
_gspread_port: GspreadPort = GspreadAdapter(_gspread_client)


def _map_to_dto(record: Mapping) -> AddGood:
    return AddGood.model_validate(record, by_name=True)


def _map_to_matrix_position(record: list[int, str, int, int]) -> Position:
    return Position(
        position_number=record[0],
        name=record[1],
        price=record[2],
        capacity=record[3]
    )


async def sync_goods():
    goods_from_ex = _gspread_port.get_all_goods()

    dtos = [_map_to_dto(record) for record in goods_from_ex]

    goods_collection = await _kit_port.get_goods_collection()

    for dto in dtos:
        if not goods_collection.is_good_already_exist(dto.name):
            await _kit_port.add_good(dto)


async def create_matrix(matrix: SnackMatrix = SnackMatrix.ugmk_1stage_blue, matrix_name: str = 'Тестовая матрица'):
    matrix_goods = _gspread_port.get_matrix_goods(matrix)

    positions = [_map_to_matrix_position(item) for item in matrix_goods]

    matrix = Matrix.create(name=matrix_name, positions=positions)

    await _kit_port.create_matrix(matrix)
