from typing import Mapping

from src.external_clients.gspread_client import GspreadClient
from src.services.matrix_service import  Cell
from src.services.positions_service import ProductPositionsRepository
from src.services.snack_machine_service import SnackMatrixId

_headers = ['number', 'product_name', 'price', 'capacity']


class CellRepository(ProductPositionsRepository):
    def __init__(self, gspread_client: GspreadClient):
        self._gspread_client = gspread_client

    def find_all(self, matrix_type: SnackMatrixId) -> list[Cell]:
        records = self._gspread_client.get_records(matrix_type, headers=_headers)
        matrix_cells = [self._map_to_matrix_cell(item) for item in records]
        return matrix_cells

    @staticmethod
    def _map_to_matrix_cell(record: Mapping):
        return Cell(
            **record,
            price_cash=record['price']
        )

