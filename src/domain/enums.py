import enum


class MachineModel(enum.StrEnum):
    TCN_720 = "TCN"
    KV_10 = "KV10"
    KV_12 = "KV12"
    UNKNOWN = "Модель не указана."
