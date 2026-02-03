from dataclasses import dataclass
from typing import Any

import gspread
from beartype import beartype
from gspread import Spreadsheet

from new_src.domain.entites.cell import MatrixCell
from new_src.domain.entites.matrix import Matrix


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class GetAllMatricesAdapter:
    spreadsheet: Spreadsheet

    async def execute(self) -> list[Matrix]:
        matrices_worksheets = self._get_matrices_worksheets()

        res: list[Matrix] = []

        for sheet in matrices_worksheets:
            sheet_data: list[list[Any]] = sheet.get_values()
            matrix_name: str = sheet.title

            cells: list[MatrixCell] = self._extract_cells_data(sheet_data[2:])

            res.append(
                Matrix(
                    cells=cells,
                    name=matrix_name
                )
            )

        return res

    def _get_matrices_worksheets(self) -> list[gspread.Worksheet]:
        return [sheet for sheet in self.spreadsheet.worksheets(exclude_hidden=True) if sheet.tab_color is None]

    @staticmethod
    def _extract_cells_data(data_range: list[list[str | int]]):
        res = []

        for row in range(0, len(data_range) - 1, 3):
            names_row = data_range[row]
            values_row = data_range[row + 1]

            names_row.extend(['' for _ in range(len(values_row) - len(names_row))])

            for col in range(0, len(values_row) - 1, 7):
                product_name = names_row[col]
                line = values_row[col]
                price = values_row[col + 5]

                if product_name and line:
                    res.append(
                        MatrixCell(
                            line_number=line,
                            product_name=product_name,
                            price=price,
                        )
                    )

        return res
