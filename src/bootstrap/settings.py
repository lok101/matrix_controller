from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.infrastructure.kit_vending.api.config import KitAPIConfig


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    google_sheets_matrix_table_id: str
    google_application_credentials: str | None = None

    kit_api_company_id: int
    kit_api_login: str
    kit_api_password: str
    kit_api_request_per_window: int = 5
    kit_api_window_seconds: int = 1
    kit_api_backoff_seconds: float = 1.0

    validate_matrices: bool = True
    matrix_load_timeout: int = 300
    matrix_apply_timeout: int = 300
    matrix_status_poll_interval: int = 15
    matrix_command_send_delay: int = 7
    matrix_poll_api_max_retries: int = Field(default=10, ge=1)
    matrix_retry_send_command_delay: int = 10

    scheduled_matrix_names: str = "*"
    log_level: str = "INFO"

    def to_kit_api_config(self) -> KitAPIConfig:
        return KitAPIConfig(
            company_id=self.kit_api_company_id,
            login=self.kit_api_login,
            password=self.kit_api_password,
            request_per_window=self.kit_api_request_per_window,
            window_seconds=self.kit_api_window_seconds,
            backoff_seconds=self.kit_api_backoff_seconds,
        )
