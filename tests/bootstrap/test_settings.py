from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.bootstrap.settings import Settings


def test_settings_matrix_deploy_defaults(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_SHEETS_MATRIX_TABLE_ID", "sheet-id")
    monkeypatch.setenv("KIT_API_COMPANY_ID", "1")
    monkeypatch.setenv("KIT_API_LOGIN", "user")
    monkeypatch.setenv("KIT_API_PASSWORD", "secret")
    for key in (
        "MATRIX_LOAD_TIMEOUT",
        "MATRIX_APPLY_TIMEOUT",
        "MATRIX_STATUS_POLL_INTERVAL",
        "MATRIX_COMMAND_SEND_DELAY",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = Settings()

    assert settings.matrix_load_timeout == 300
    assert settings.matrix_apply_timeout == 300
    assert settings.matrix_status_poll_interval == 15
    assert settings.matrix_command_send_delay == 7


def test_settings_poll_and_retry_defaults(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_SHEETS_MATRIX_TABLE_ID", "sheet-id")
    monkeypatch.setenv("KIT_API_COMPANY_ID", "1")
    monkeypatch.setenv("KIT_API_LOGIN", "user")
    monkeypatch.setenv("KIT_API_PASSWORD", "secret")
    for key in ("MATRIX_POLL_API_MAX_RETRIES", "MATRIX_RETRY_SEND_COMMAND_DELAY"):
        monkeypatch.delenv(key, raising=False)

    settings = Settings()
    assert settings.matrix_poll_api_max_retries == 10
    assert settings.matrix_retry_send_command_delay == 10


def test_settings_rejects_zero_poll_api_max_retries(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_SHEETS_MATRIX_TABLE_ID", "sheet-id")
    monkeypatch.setenv("KIT_API_COMPANY_ID", "1")
    monkeypatch.setenv("KIT_API_LOGIN", "user")
    monkeypatch.setenv("KIT_API_PASSWORD", "secret")
    monkeypatch.setenv("MATRIX_POLL_API_MAX_RETRIES", "0")

    with pytest.raises(ValidationError):
        Settings()
