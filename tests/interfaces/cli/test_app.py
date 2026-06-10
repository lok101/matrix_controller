from __future__ import annotations

from dataclasses import dataclass

from typer.testing import CliRunner

from src.interfaces.cli.app import app


def test_run_command_removed() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["run", "--mode", "interactive"])
    assert result.exit_code != 0


@dataclass
class _FakeJob:
    status: str = "completed"


class _FakeContainer:
    def __init__(self, settings: object) -> None:
        self._settings = settings

    async def __aenter__(self) -> _FakeContainer:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def sync_only(self) -> None:
        return None

    def configure_scheduled_selection(self, names: str) -> None:
        _FakeContainer.captured_names = names

    async def run_deployment(self, trigger: str) -> _FakeJob:
        _FakeContainer.captured_trigger = trigger
        return _FakeJob()


class _FakeSettings:
    scheduled_matrix_names = "from_env"
    log_level = "INFO"


def test_deploy_scheduled_cli_names_override(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_SHEETS_MATRIX_TABLE_ID", "sheet-id")
    monkeypatch.setenv("KIT_API_COMPANY_ID", "1")
    monkeypatch.setenv("KIT_API_LOGIN", "login")
    monkeypatch.setenv("KIT_API_PASSWORD", "password")
    monkeypatch.setenv("SCHEDULED_MATRIX_NAMES", "from_env")

    monkeypatch.setattr("src.interfaces.cli.app.Settings", _FakeSettings)
    monkeypatch.setattr("src.interfaces.cli.app.Container", _FakeContainer)
    monkeypatch.setattr("src.interfaces.cli.app.configure_logging", lambda: None)

    _FakeContainer.captured_names = ""
    _FakeContainer.captured_trigger = ""

    runner = CliRunner()
    result = runner.invoke(app, ["deploy", "scheduled", "--names", "cli_a,cli_b"])

    assert result.exit_code == 0
    assert _FakeContainer.captured_names == "cli_a,cli_b"
    assert _FakeContainer.captured_trigger == "scheduled"


def test_deploy_scheduled_uses_env_when_names_omitted(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_SHEETS_MATRIX_TABLE_ID", "sheet-id")
    monkeypatch.setenv("KIT_API_COMPANY_ID", "1")
    monkeypatch.setenv("KIT_API_LOGIN", "login")
    monkeypatch.setenv("KIT_API_PASSWORD", "password")
    monkeypatch.setenv("SCHEDULED_MATRIX_NAMES", "env_matrix")

    monkeypatch.setattr("src.interfaces.cli.app.Settings", _FakeSettings)
    monkeypatch.setattr("src.interfaces.cli.app.Container", _FakeContainer)
    monkeypatch.setattr("src.interfaces.cli.app.configure_logging", lambda: None)

    _FakeContainer.captured_names = ""

    runner = CliRunner()
    result = runner.invoke(app, ["deploy", "scheduled"])

    assert result.exit_code == 0
    assert _FakeContainer.captured_names == "from_env"


def test_deploy_scheduled_rejects_empty_names() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["deploy", "scheduled", "--names", ""])
    assert result.exit_code != 0


def test_deploy_interactive_requires_tty(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_SHEETS_MATRIX_TABLE_ID", "sheet-id")
    monkeypatch.setenv("KIT_API_COMPANY_ID", "1")
    monkeypatch.setenv("KIT_API_LOGIN", "login")
    monkeypatch.setenv("KIT_API_PASSWORD", "password")

    monkeypatch.setattr("src.interfaces.cli.app.Settings", _FakeSettings)
    monkeypatch.setattr("src.interfaces.cli.app.Container", _FakeContainer)
    monkeypatch.setattr("src.interfaces.cli.app.configure_logging", lambda: None)
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)

    runner = CliRunner()
    result = runner.invoke(app, ["deploy", "interactive"])

    assert result.exit_code == 2
    assert "TTY" in result.stderr
