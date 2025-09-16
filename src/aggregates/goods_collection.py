from src.dtos import Good


class GoodsCollection:
    def __init__(self):
        self._goods: dict[str, Good] = {}

    @classmethod
    def create(cls, data: list[dict[str, int | str]]) -> 'GoodsCollection':
        instance = cls()

        for item in data:
            good = Good(**item)
            instance._goods[good.name] = good

        return instance

    def is_good_already_exist(self, good_name: str) -> bool:
        return good_name in self._goods.keys()
