from dataclasses import dataclass
from datetime import datetime

from beartype import beartype
from kit_api import KitVendingAPIClient, KitAPIResponseError

from new_src.domain.entites.matrix import Matrix
from new_src.domain.value_objects.ids.matrix_kit_id import MatrixKitId


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class UploadMatrixAdapter:
    kit_api_client: KitVendingAPIClient

    async def execute(self, matrix: Matrix, timestamp: datetime) -> MatrixKitId | None:
        matrix_name: str = self._get_matrix_kit_name(matrix.name, timestamp)

        try:
            matrix_id: int | None = await self.kit_api_client.create_matrix(
                matrix_name=matrix_name,
                positions=[
                    {
                        "line_number": cell.line_number,
                        "price": cell.price,
                        "product_name": cell.product_name,
                    } for cell in matrix.cells
                ]
            )

            if matrix_id is None:
                raise NotImplementedError()

        except KitAPIResponseError as ex:
            print(ex)
            return None

        return MatrixKitId(matrix_id)

    @staticmethod
    def _get_matrix_kit_name(name: str, timestamp: datetime) -> str:
        return f"{name} - {timestamp.strftime('%Y.%m.%d')}"
