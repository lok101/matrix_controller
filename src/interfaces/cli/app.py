from __future__ import annotations

import asyncio
import logging

import typer

from src.bootstrap.container import Container
from src.bootstrap.settings import Settings
from src.infrastructure.logging import configure_logging
from src.interfaces.cli.deploy_interactive import deploy_interactive
from src.interfaces.cli.deploy_scheduled import deploy_scheduled

app = typer.Typer(no_args_is_help=True)
deploy_app = typer.Typer(no_args_is_help=True)
app.add_typer(deploy_app, name="deploy")


def _validate_scheduled_names(names: str | None) -> str | None:
    if names is not None and not names.strip():
        raise typer.BadParameter("--names не может быть пустой строкой")
    return names


async def _async_main(
    command: str,
    *,
    scheduled_names: str | None = None,
) -> int:
    try:
        settings = Settings()
    except Exception as exc:
        typer.echo(f"Ошибка конфигурации: {exc}", err=True)
        return 2

    configure_logging()
    logging.getLogger().setLevel(settings.log_level)

    async with Container(settings) as container:
        if command == "sync":
            await container.sync_only()
            return 0
        if command == "deploy-interactive":
            return await deploy_interactive(container)
        if command == "deploy-scheduled":
            names = (
                scheduled_names
                if scheduled_names is not None
                else settings.scheduled_matrix_names
            )
            return await deploy_scheduled(container, names)

    return 2


def _run(command: str, *, scheduled_names: str | None = None) -> None:
    code = asyncio.run(_async_main(command, scheduled_names=scheduled_names))
    raise typer.Exit(code)


@deploy_app.command("interactive")
def deploy_interactive_cmd() -> None:
    """Sync + интерактивный выбор матриц + deploy."""
    _run("deploy-interactive")


@deploy_app.command("scheduled")
def deploy_scheduled_cmd(
    names: str | None = typer.Option(
        None,
        "--names",
        help='Список матриц через запятую или "*". По умолчанию — SCHEDULED_MATRIX_NAMES из env.',
    ),
) -> None:
    """Sync + deploy по списку имён (cron / Task Scheduler)."""
    validated = _validate_scheduled_names(names)
    _run("deploy-scheduled", scheduled_names=validated)


@app.command("sync")
def sync_cmd() -> None:
    """Только sync кэшей (products, vending machines, matrices)."""
    _run("sync")
