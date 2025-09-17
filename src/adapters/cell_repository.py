from typing import Any

from src.infrastructure.external_clients.gspread_client import GspreadClient
from src.services.matrix_service import ICellRepository, MatrixType, Cell


class CellRepository(ICellRepository):
    def __init__(self, gspread_client: GspreadClient):
        self._gspread_client = gspread_client

    def get_all(self, matrix_type: MatrixType) -> list[Cell]:
        raw_data = self._gspread_client.get_range_data(matrix_type)
        not_empty_positions = self._clear_records(raw_data)
        matrix_cells = [self._map_to_matrix_cell(item) for item in not_empty_positions]
        return matrix_cells

    @staticmethod
    def _map_to_matrix_cell(record: list[str | int]):
        return Cell(
            number=record[0],
            product_name=record[1],
            price=record[2],
            capacity=record[3]
        )

    @staticmethod
    def _clear_records(records: list[list[Any]]):
        res = []

        for record in records:

            if not any(record):
                return res

            row_data = []

            for cell in record:

                if cell and cell.isnumeric():
                    row_data.append(int(cell))
                elif cell:
                    row_data.append(cell)

            res.append(row_data)

        return res
