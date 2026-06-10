from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class JobRunId:
    value: str

    @classmethod
    def generate(cls) -> JobRunId:
        return cls(value=str(uuid.uuid4()))
