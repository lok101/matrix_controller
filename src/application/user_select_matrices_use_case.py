from src.domain.repositories.matrix_repository import MatrixRepository
from src.infrastructure.interactive_matrices_selector import InteractiveSelector


class GetMatricesWithSelectionUseCase:
    def __init__(
            self,
            matrix_repo: MatrixRepository,
            selector: InteractiveSelector
    ):
        self._matrix_repo = matrix_repo
        self._selector = selector

    def execute(self) -> list[str]:
        matrices_names = self._matrix_repo.get_matrices_names()

        if not matrices_names:
            print("Нет доступных матриц!")
            return []

        selected_names = self._selector.select_items(matrices_names)

        return selected_names
