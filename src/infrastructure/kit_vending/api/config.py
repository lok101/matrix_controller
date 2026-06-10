from __future__ import annotations

import os
from dataclasses import dataclass

from src.infrastructure.kit_vending.api.exceptions import KitAPIValidationError


@dataclass(frozen=True, slots=True, kw_only=True)
class KitAPIConfig:
    company_id: int
    login: str
    password: str
    request_per_window: int = 1
    window_seconds: int = 10
    backoff_seconds: float = 60.0

    @classmethod
    def from_env(cls) -> KitAPIConfig:
        login = os.getenv("KIT_API_LOGIN")
        password = os.getenv("KIT_API_PASSWORD")
        company_id_raw = os.getenv("KIT_API_COMPANY_ID")

        if login is None or password is None or company_id_raw is None:
            raise KitAPIValidationError(
                "KIT_API_LOGIN, KIT_API_PASSWORD и KIT_API_COMPANY_ID обязательны в .env"
            )

        try:
            company_id = int(company_id_raw)
            request_per_window = int(os.getenv("KIT_API_REQUEST_PER_WINDOW", "1"))
            window_seconds = int(os.getenv("KIT_API_WINDOW_SECONDS", "10"))
            backoff_seconds = float(os.getenv("KIT_API_BACKOFF_SECONDS", "60.0"))
        except ValueError as exc:
            raise KitAPIValidationError(
                "KIT_API_COMPANY_ID, KIT_API_REQUEST_PER_WINDOW, "
                "KIT_API_WINDOW_SECONDS и KIT_API_BACKOFF_SECONDS должны быть числами."
            ) from exc

        return cls(
            company_id=company_id,
            login=login,
            password=password,
            request_per_window=request_per_window,
            window_seconds=window_seconds,
            backoff_seconds=backoff_seconds,
        )
