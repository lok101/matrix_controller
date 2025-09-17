from dataclasses import dataclass

from pydantic import BaseModel, Field


class AddGood(BaseModel):
    name: str = Field(alias='GoodsName')


class Good(AddGood):
    id: int = Field(alias='GoodsId')


@dataclass
class Position:
    position_number: int
    name: str
    price: int
    capacity: int

    def as_dict(self) -> dict[str, int | str]:
        return {
            'LineNumber': self.position_number,
            'ChoiceNumber': self.position_number,
            'GoodsName': self.name,
            'Price': self.price,
            'MaxCount': self.capacity,
        }


@dataclass
class Matrix:
    name: str
    positions: list[Position]

    @classmethod
    def create(cls, name: str, positions: list[Position]):
        return cls(
            name=name,
            positions=positions
        )

    def as_dict(self):
        return {
            'MatrixName': self.name,
            'Positions': [
                position.as_dict() for position in self.positions
            ]

        }
