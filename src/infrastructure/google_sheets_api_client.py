import logging
import re
from dataclasses import dataclass
from itertools import batched
from typing import Any

import gspread
from beartype import beartype

logger = logging.getLogger("__main__")

MACHINE_IDS_CELL_INDEX = 7

CELL_DATAW_HEIGHT = 3
CELL_DATAW_WIDTH = 7


class ExtractDataError(Exception):
    pass


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class MatrixCellDTO:
    number: int | None
    product_name: str | None
    product_price: float | None


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class MatrixDTO:
    matrix_name: str
    cells_data: list[MatrixCellDTO]
    vending_machine_ids: list[int]


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class GoogleSheetsAPIClient:
    spreadsheet: gspread.Spreadsheet

    def get_all_matrices(self) -> list[MatrixDTO]:
        res: list[MatrixDTO] = []

        matrices_worksheets = self._get_matrices_worksheets()

        for sheet in matrices_worksheets:
            sheet_data: list[list[Any]] = sheet.get_values()
            matrix_name: str = sheet.title

            cells: list[MatrixCellDTO] = self._extract_cells_data(sheet_data[2:], matrix_name)
            vending_machines_ids: list[int] = self._extract_vending_machines_ids(sheet_data, matrix_name)

            res.append(
                MatrixDTO(
                    cells_data=cells,
                    matrix_name=matrix_name,
                    vending_machine_ids=vending_machines_ids,
                )
            )

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
    def _extract_cells_data(data_range: list[list[str]], matrix_name: str) -> list[MatrixCellDTO]:
        res: list[MatrixCellDTO] = []
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

                if price_data.isdigit():
                    price: float = float(price_data)

                elif product_name is not None:
                    logger.error(f"Переданная цена товара не является числом. Матрица: {matrix_name}.")

                res.append(
                    MatrixCellDTO(
                        product_price=price,
                        product_name=product_name,
                        number=cell_number,
                    )
                )

        return res
