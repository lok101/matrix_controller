import argparse
import asyncio
import logging
import sys

from src.bootstrap.container import Container
from src.bootstrap.settings import Settings
from src.infrastructure.logging import configure_logging
from src.interfaces.cli.run_interactive import run_interactive
from src.interfaces.cli.run_scheduled import run_scheduled


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="matrix-controller")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Sync + deploy")
    run_parser.add_argument(
        "--mode",
        choices=["interactive", "scheduled"],
        required=True,
    )

    sub.add_parser("sync", help="Sync caches only")
    return parser


async def async_main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        settings = Settings()
    except Exception as exc:
        print(f"Ошибка конфигурации: {exc}", file=sys.stderr)
        return 2

    configure_logging()
    logging.getLogger().setLevel(settings.log_level)

    async with Container(settings) as container:
        if args.command == "sync":
            await container.sync_only()
            return 0

        if args.command == "run":
            if args.mode == "interactive":
                return await run_interactive(container)
            return await run_scheduled(container, settings.scheduled_matrix_names)

    return 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(async_main()))
