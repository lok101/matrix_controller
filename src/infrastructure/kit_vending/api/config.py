from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class KitAPIConfig:
    company_id: int
    login: str
    password: str
    request_per_window: int = 1
    window_seconds: int = 10
    backoff_seconds: float = 60.0
