from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class KitAPIAccount:
    login: str
    password: str
    company_id: int
