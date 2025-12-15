from dataclasses import dataclass


@dataclass(frozen=True)
class UpdateMatricesRequest:
    matrices_names: list[str]
