from __future__ import annotations

import sys

import questionary
from beartype import beartype
from questionary import Choice

if sys.platform == "win32":
    from prompt_toolkit.output.win32 import NoConsoleScreenBufferError
else:
    NoConsoleScreenBufferError = type(
        "NoConsoleScreenBufferError", (RuntimeError,), {}
    )

_PROMPT = "Выберите матрицы (пробел — отметить, enter — подтвердить):"
_NO_TERMINAL_MSG = (
    "Интерактивный выбор требует терминала с TTY. "
    "Запустите из cmd.exe или PowerShell: uv run matrix-controller deploy interactive"
)


class InteractiveTerminalRequiredError(RuntimeError):
    """Нет интерактивного терминала для questionary."""


@beartype
def ensure_interactive_terminal() -> None:
    if sys.stdin is None or sys.stdout is None:
        raise InteractiveTerminalRequiredError(_NO_TERMINAL_MSG)
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise InteractiveTerminalRequiredError(_NO_TERMINAL_MSG)


@beartype
class QuestionarySelector:
    async def select_items(self, items: list[tuple[str, str]]) -> list[str]:
        if not items:
            return []
        ensure_interactive_terminal()
        try:
            choices = [Choice(title=label, value=value) for label, value in items]
            selected = await questionary.checkbox(_PROMPT, choices=choices).ask_async(
                patch_stdout=True
            )
        except (KeyboardInterrupt, EOFError):
            return []
        except NoConsoleScreenBufferError as exc:
            raise InteractiveTerminalRequiredError(_NO_TERMINAL_MSG) from exc
        if selected is None:
            return []
        return list(selected)
