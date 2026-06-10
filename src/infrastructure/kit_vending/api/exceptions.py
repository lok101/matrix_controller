from __future__ import annotations


class KitAPIError(Exception):
    """Базовое исключение для ошибок Kit API."""


class KitAPIAuthError(KitAPIError):
    """Ошибка аутентификации."""


class KitAPINetworkError(KitAPIError):
    """Ошибка сети."""


class KitAPIResponseError(KitAPIError):
    """Ошибка ответа от API."""

    def __init__(self, message: str, result_code: int) -> None:
        self.result_code = result_code
        super().__init__(message)


class KitAPIValidationError(KitAPIError):
    """Ошибка валидации данных или конфигурации."""
