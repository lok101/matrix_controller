import asyncio

from src.infrastructure.kit_service import add_matrix_to_kit_vending
from src.infrastructure.gspread_service import get_snack_cells, get_machine_model, get_range_name
from src.utils import create_matrix_name


async def main(sheet_name: str):
    model = get_machine_model(sheet_name)
    matrix_range_name = get_range_name(sheet_name)

    matrix_name = create_matrix_name(sheet_name, machine_model=model)

    snack_cells = get_snack_cells(range_name=matrix_range_name)
    await add_matrix_to_kit_vending(
        matrix_name=matrix_name,
        products=snack_cells
    )
    print(f'Создана матрица с именем: "{matrix_name}"')


if __name__ == "__main__":
    user_input = input('Введите название матрицы: ')
    asyncio.run(main(user_input))
