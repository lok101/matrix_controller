from __future__ import annotations

import asyncio

import questionary
from beartype import beartype
from questionary import Choice

_PROMPT = "Выберите матрицы (пробел — отметить, enter — подтвердить):"


@beartype
class QuestionarySelector:
    def select_items(self, items: list[tuple[str, str]]) -> list[str]:
        if not items:
            return []
        try:
            choices = [Choice(title=label, value=value) for label, value in items]
            selected = asyncio.run(
                questionary.checkbox(_PROMPT, choices=choices).ask_async()
            )
        except (KeyboardInterrupt, EOFError):
            return []
        if selected is None:
            return []
        return list(selected)
