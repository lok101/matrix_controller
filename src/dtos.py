from pydantic import BaseModel, Field


class AddGood(BaseModel):
    name: str = Field(alias='GoodsName')


class Good(AddGood):
    id: int = Field(alias='GoodsId')
