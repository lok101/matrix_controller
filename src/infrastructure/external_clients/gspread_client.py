from abc import ABC, abstractmethod
from typing import Mapping, Any

import gspread

_client = gspread.service_account()
_headers = ['name']

type range = list[list[Any]]


class GspreadClient(ABC):
    @abstractmethod
    def get_all_goods_data(self, range_name: str = 'Товары') -> list[Mapping]: pass

    @abstractmethod
    def fetch_data(self, range_name: str) -> list[list[int, str, int, int]]: pass

    @abstractmethod
    def get_range_data(self, range_name: str) -> list[list[Any]]: pass


class GspreadClientImpl(GspreadClient):
    def __init__(self, table_id: str = '1Sv17olPfODpOVCB4Yuy4nWU27-otwCs0XJa_CiAyO7k'):
        self._spreadsheet = _client.open_by_key(table_id)

    def get_all_goods_data(self, range_name: str = 'Товары') -> list[Mapping]:
        response = self._spreadsheet.values_batch_get([range_name])
        cells_data = response['valueRanges'][0]['values']
        return self._map_to_records(_headers, cells_data[1:])

    def fetch_data(self, range_name: str) -> list[list[int | str]]:
        response = self._spreadsheet.values_batch_get([range_name])
        cells_data = response['valueRanges'][0]['values']
        cleaned_records = self._clear_records(cells_data)
        return cleaned_records

    def get_range_data(self, range_name: str) -> range:
        response = self._spreadsheet.values_batch_get([range_name])
        return response['valueRanges'][0]['values']

    @staticmethod
    def _map_to_records(headers: list[str], values: list[Mapping]):
        res = []

        for row in values:
            record = {}

            for i, value in enumerate(row):
                key = headers[i]

                if value.isnumeric():
                    value = int(value)

                record[key] = value

            if record['name']:
                res.append(record)

        return res

    @staticmethod
    def _clear_records(records: list[list[int, str, int, int]]):
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
