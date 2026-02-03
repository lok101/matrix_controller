from dataclasses import dataclass

from beartype import beartype
from kit_api import KitVendingAPIClient, KitAPIResponseError

from new_src.domain.entites.matrix import Matrix
from new_src.domain.value_objects.ids.matrix_kit_id import MatrixKitId


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class UploadMatrixAdapter:
    kit_api_client: KitVendingAPIClient

    async def execute(self, matrix: Matrix) -> MatrixKitId | None:
        try:
            matrix_id: int | None = await self.kit_api_client.create_matrix(
                matrix_name=matrix.name,
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
