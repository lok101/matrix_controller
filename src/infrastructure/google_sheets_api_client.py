import logging
import re
from dataclasses import dataclass
from itertools import batched
from typing import Any

import gspread
from beartype import beartype
from gspread import Worksheet

logger = logging.getLogger("__main__")

GOODS_WORKSHEET_ID = "2037389959"
GOODS_DATA_START_ROW = 4

MACHINE_IDS_CELL_INDEX = 7

CELL_DATAW_HEIGHT = 3
CELL_DATAW_WIDTH = 7


class ExtractDataError(Exception):
    pass

def is_float(s: str) -> bool:
    s = s.replace(",", ".")
    try:
        float(s)
        return True
    except ValueError:
        return False


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class ProductModel:
    id: int
    name: str | None
    price: float | None


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class MatrixCellModel:
    number: int | None
    product_name: str | None
    product_price: float | None


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class MatrixModel:
    matrix_name: str
    cells_data: list[MatrixCellModel]
    vending_machine_ids: list[int]


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class GoogleSheetsAPIClient:
    spreadsheet: gspread.Spreadsheet

    def get_all_matrices(self) -> list[MatrixModel]:
        res: list[MatrixModel] = []

        matrices_worksheets = self._get_matrices_worksheets()

        for sheet in matrices_worksheets:
            sheet_data: list[list[Any]] = sheet.get_values()
            matrix_name: str = sheet.title

            cells: list[MatrixCellModel] = self._extract_cells_data(sheet_data[2:], matrix_name)
            vending_machines_ids: list[int] = self._extract_vending_machines_ids(sheet_data, matrix_name)

            res.append(
                MatrixModel(
                    cells_data=cells,
                    matrix_name=matrix_name,
                    vending_machine_ids=vending_machines_ids,
                )
            )

        return res

    def get_all_products(self) -> list[ProductModel]:
        res: list[ProductModel] = []

        worksheet: Worksheet = self.spreadsheet.get_worksheet_by_id(GOODS_WORKSHEET_ID)
        all_values: list[list[Any]] = worksheet.get_values()
        goods_data: list[list[Any]] = all_values[GOODS_DATA_START_ROW:]

        for row in goods_data:
            product_id: int
            product_name: str | None = None
            product_price: float | None = None

            product_id_data, product_name_data, product_price_data, _ = row[:4]

            if not product_id_data:
                continue

            if product_id_data.isdigit():
                product_id: int = int(product_id_data)
            else:
                raise ExtractDataError(f"В поле Id у товара передано не цифровое значение. Имя товара: {product_name}.")

            if is_float(product_price_data):
                product_price_data = product_price_data.replace(",", ".")
                product_price: float = float(product_price_data)

            product_name: str | None = product_name_data or None


            product: ProductModel = ProductModel(
                id=product_id,
                name=product_name,
                price=product_price,
            )

            res.append(product)

        return res

    def _get_matrices_worksheets(self) -> list[gspread.Worksheet]:
        return [sheet for sheet in self.spreadsheet.worksheets(exclude_hidden=True) if sheet.tab_color is None]

    @staticmethod
    def _extract_vending_machines_ids(data_range: list[list[str | int]], matrix_name: str) -> list[int]:
        res: list[int] = []

        ids_raw: str | int = data_range[0][MACHINE_IDS_CELL_INDEX]

        if not ids_raw:
            logger.warning(f"Для матрицы {matrix_name} не переданы Id аппаратов.")
            return res

        ids: str = str(ids_raw).strip()

        if ids:
            ids: str = re.sub(r"[().]", "", ids)

            for str_id in ids.split(','):
                str_id: str = str_id.strip()

                if not str_id.isdigit():
                    logger.error(f"Для матрицы {matrix_name} передан не цифровой Id: {str_id}.")
                    continue

                int_id: int = int(str_id)
                res.append(int_id)

        return res

    @staticmethod
    def _extract_cells_data(data_range: list[list[str]], matrix_name: str) -> list[MatrixCellModel]:
        res: list[MatrixCellModel] = []
        data_range.append([])  # выравнивание для batched

        for names_row, data_row, _ in batched(data_range, CELL_DATAW_HEIGHT):
            data_row.append('')  # выравнивание для batched
            names_row.extend(['' for _ in range(len(data_row) - len(names_row))])

            for i, (cell_number_data, _, _, _, _, price_data, _) in enumerate(batched(data_row, CELL_DATAW_WIDTH)):
                product_name: str | None = names_row[i * CELL_DATAW_WIDTH] or None
                cell_number: int | None = None
                price: float | None = None

                if cell_number_data.isdigit():
                    cell_number: int = int(cell_number_data)

                elif product_name is not None:
                    logger.error(f"Переданный номер ячейки не является числом. Матрица: {matrix_name}.")

                if is_float(price_data):
                    price: float = float(price_data)

                elif product_name is not None:
                    logger.error(f"Переданная цена товара не является числом. Матрица: {matrix_name}.")

                res.append(
                    MatrixCellModel(
                        product_price=price,
                        product_name=product_name,
                        number=cell_number,
                    )
                )

        return res
