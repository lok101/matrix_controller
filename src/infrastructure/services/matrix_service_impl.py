# from src.domain.entities.matrix import Matrix, MatrixCell
# from src.domain.repositories.matrix_repository import MatrixRepository
# from src.domain.repositories.product_repository import ProductRepository
# from src.domain.services.matrix_data_provider import MatrixDataProvider
# from src.domain.services.matrix_service import MatrixService
#
#
# class MatrixServiceImpl(MatrixService):
#     def __init__(self, product_repo: ProductRepository, matrix_repo: MatrixRepository):
#         self._product_repo = product_repo
#         self._matrix_repo = matrix_repo
#
#     async def get_matrix(self, matrix_name: str) -> Matrix:
#         matrix = self._matrix_repo.get_by_name(matrix_name)
#
#         cells = []
#
#         for cell in matrix_data.cells:
#             product = self._product_repo.get_by_name(cell.product_name)
#             cells.append(
#                 MatrixCell(
#                     product=product,
#                     line_number=cell.line,
#                     price=cell.price
#                 )
#             )
#
#         return Matrix(
#             cells=cells,
#             machine_model=matrix_data.machine_model,
#             machine_ids=matrix_data.machine_ids,
#             name=matrix_name
#
#         )
