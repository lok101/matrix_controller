from datetime import date


def create_matrix_name(machine_name: str, machine_model: str) -> str:
    return f'{machine_name} | {date.today().strftime('%d.%m.%y')} | {machine_model}'
