from src.domain.enums import MachineModel
from src.infrastructure.ex_api.models.matrix import CellData

MACHINE_MODEL_CELL_INDEX = 21
MACHINE_IDS_CELL_INDEX = 7


def extract_machine_model(sheet_data: list[list[str | int]]) -> MachineModel:
    try:
        return MachineModel(sheet_data[0][MACHINE_MODEL_CELL_INDEX])
    except KeyError:
        return MachineModel.UNKNOWN


def extract_machine_ids(sheet_data: list[list[str | int]]) -> list[int] | None:
    ids = sheet_data[0][MACHINE_IDS_CELL_INDEX]
    if ids:
        ids = map(int, ids.split(","))
        return list(ids)


def extract_cells_data(data_range: list[list[str | int]]):
    res = []

    for row in range(0, len(data_range) - 1, 3):
        names_row = data_range[row]
        values_row = data_range[row + 1]

        names_row.extend(['' for _ in range(len(values_row) - len(names_row))])

        for col in range(0, len(values_row) - 1, 7):
            product_name = names_row[col]
            if product_name:
                line = values_row[col]
                price = values_row[col + 5]
                if line:
                    res.append(
                        CellData(
                            line=line,
                            product_name=product_name,
                            price=price,
                        )
                    )

    return res
