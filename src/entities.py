from typing import Annotated

from pydantic import BaseModel, Field, ConfigDict, BeforeValidator

from config import MIN_SALE_PRICE

MAX_SPIRAL_SIZE = 15


def parse_cell_int_value(val: str) -> int | None:
    if not val.isnumeric():
        raise Exception(f'Переданное значение должно быть числом, передано - "{val}"')

    return int(val)


class CellPosition(BaseModel):
    product_name: str
    line: int
    price: Annotated[int, Field(gt=MIN_SALE_PRICE)]
    capacity: Annotated[int, Field(le=MAX_SPIRAL_SIZE), BeforeValidator(parse_cell_int_value)]

    def as_kit_cell(self) -> dict:
        return {
            'LineNumber': self.line,
            'ChoiceNumber': self.line,
            'GoodsName': self.product_name,
            'Price2': self.price,
            'Price': self.price,
            'MaxCount': self.capacity,
        }


class Product(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(alias='GoodsName')

    def as_kit_product(self) -> dict:
        return self.model_dump(by_alias=True)

    def __hash__(self):
        return hash(self.name)


class ProductsCollection(BaseModel):
    products: list[Product] = Field(validation_alias='Goods')

    def get_missing_elements(self, products: list[Product]) -> list[Product]:
        return list(set(products) - set(self.products))
