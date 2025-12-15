import os

import gspread
from dotenv import load_dotenv

from src.infrastructure.ex_api.models.matrix import MatrixData
from src.infrastructure.ex_api.models.product import ProductData
from src.infrastructure.ex_api.utils import extract_cells_data, extract_machine_ids, extract_machine_model

load_dotenv()
_table_id = os.getenv('GOOGLE_SHEETS_MATRIX_TABLE_ID')


class GspreadAPIClient:
    def __init__(self):

        self._spreadsheet = gspread.service_account().open_by_key(_table_id)

    def get_products(self, range_name: str = "Товары") -> list[ProductData]:

        res = []

        products_data = self._get_range_cells(range_name, headers=4)

        for row in products_data:
            res.append(
                ProductData(
                    id=row[0],
                    name=row[1],
                    capacity=row[3],
                    purchase_price=row[2]
                )
            )

        return res

    def get_matrices(self) -> list[MatrixData]:
        worksheets = self._get_matrix_worksheets()

        res = []

        for sheet in worksheets:
            sheet_data = sheet.get_values()
            machine_model = extract_machine_model(sheet_data)
            machines_ids = extract_machine_ids(sheet_data)
            cells_data = extract_cells_data(sheet_data[2:])

            res.append(
                MatrixData(
                    machine_model=machine_model,
                    machine_ids=machines_ids,
                    cells=cells_data,
                    matrix_name=sheet.title
                )
            )

        return res

    def _get_matrix_worksheets(self) -> list[gspread.Worksheet]:
        return [sheet for sheet in self._spreadsheet.worksheets(exclude_hidden=True) if sheet.tab_color is None]

    def _get_range_cells(self, range_name: str, headers: int = 0):
        response = self._spreadsheet.values_get(range_name)
        return response['values'][headers:]
