from __future__ import annotations

import asyncio

import pytest

from src.interfaces.cli.questionary_selector import (
    InteractiveTerminalRequiredError,
    QuestionarySelector,
    ensure_interactive_terminal,
)


def test_ensure_interactive_terminal_requires_tty(monkeypatch) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)

    with pytest.raises(InteractiveTerminalRequiredError, match="TTY"):
        ensure_interactive_terminal()


def test_questionary_selector_empty_items_skips_terminal_check() -> None:
    assert asyncio.run(QuestionarySelector().select_items([])) == []
