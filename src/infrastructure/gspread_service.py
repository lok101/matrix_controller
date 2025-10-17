import os

import gspread
from dotenv import load_dotenv

from src.entities import CellPosition, Product

load_dotenv()
_table_id = os.getenv('GOOGLE_SHEETS_MATRIX_TABLE_ID')

_service_account = gspread.service_account()
_spreadsheet = _service_account.open_by_key(_table_id)


def _get_range_cells(range_name: str):
    response = _spreadsheet.values_get(range_name)
    return response['values']


def get_machine_model(sheet_name: str) -> str:
    range_name = f'\'{sheet_name}\'!model'
    try:
        return _get_range_cells(range_name)[0][0]
    except KeyError:
        return 'Модель не указана в таблице.'


def get_range_name(sheet_name: str) -> str:
    return f'\'{sheet_name}\'!matrix'


def get_products() -> list[Product]:
    cells_data = _get_range_cells('Товары')
    products = [Product(name=cell_value) for row in cells_data[1:] for cell_value in row]
    return products


def get_snack_cells(range_name: str):
    cells_data = _get_range_cells(range_name)

    res = []

    for r in range(0, len(cells_data) - 1, 3):
        values_row = cells_data[r + 1]

        names_row = cells_data[r]
        names_row.extend(['' for _ in range(len(values_row) - len(names_row))])

        for c in range(0, len(values_row) - 1, 5):
            product_name = names_row[c]
            if product_name:
                line = values_row[c]
                capacity = values_row[c + 1]
                width = values_row[c + 2]
                price = values_row[c + 3]
                product = CellPosition(line=line, product_name=product_name, capacity=capacity, price=price,
                                       width=width)
                res.append(product)

    return res
