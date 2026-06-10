# План реализации: CLI на typer + questionary

> **Для агентов:** Используй скилл executing-plans для реализации этого плана задача за задачей. Шаги используют синтаксис чекбоксов (`- [ ]`) для отслеживания.

**Цель:** Заменить `argparse` + самописный `InteractiveSelector` на `typer` + `questionary`, показывать в списке выбора имя матрицы и номера аппаратов, реструктурировать команды в `deploy interactive` / `deploy scheduled` + `sync`.

**Архитектура:** Тонкий Typer-слой в `src/interfaces/cli/` (команды, коды выхода, разрешение `--names`). `QuestionarySelector` — обёртка над `questionary.checkbox`. `InteractiveMatrixSelection` (infrastructure) формирует `(label, matrix.name)` через `format_matrix_choice_label()`. `MatrixSelectionPort` и use cases не меняются.

**Ключевые файлы / стек:** Python 3.12+, `uv`, `typer>=0.25.1`, `questionary>=2.1.1`, sync pytest, `beartype`, pydantic-settings.

**Спек:** [docs/specs/2026-06-10-cli-typer-questionary-design.md](../specs/2026-06-10-cli-typer-questionary-design.md)

---

## Карта файлов

| Файл | Действие | Ответственность |
|------|----------|-----------------|
| `pyproject.toml` | Изменить | Зависимости `typer`, `questionary`; entry point `matrix-controller` |
| `src/interfaces/cli/matrix_choice_label.py` | Создать | `format_matrix_choice_label(matrix) → str` |
| `src/interfaces/cli/questionary_selector.py` | Создать | Обёртка `questionary.checkbox` |
| `src/interfaces/cli/app.py` | Создать | Typer app: `deploy interactive/scheduled`, `sync` |
| `src/interfaces/cli/deploy_interactive.py` | Создать | Async runner interactive deploy (бывший `run_interactive.py`) |
| `src/interfaces/cli/deploy_scheduled.py` | Создать | Async runner scheduled deploy (бывший `run_scheduled.py`) |
| `main.py` | Изменить | Делегирование в `app()` |
| `src/infrastructure/selection/interactive_selection.py` | Изменить | Labels + `(label, value)` tuples |
| `src/bootstrap/container.py` | Изменить | `QuestionarySelector` вместо `InteractiveSelector` |
| `src/infrastructure/selection/interactive_selector.py` | Удалить | Старый cls/clear/input селектор |
| `src/interfaces/cli/run_interactive.py` | Удалить | Заменён на `deploy_interactive.py` |
| `src/interfaces/cli/run_scheduled.py` | Удалить | Заменён на `deploy_scheduled.py` |
| `tests/interfaces/cli/test_matrix_choice_label.py` | Создать | TDD форматирования подписи |
| `tests/infrastructure/selection/test_interactive_matrix_selection.py` | Создать | Fake-selector + labels |
| `tests/interfaces/cli/test_app.py` | Создать | CLI: `--names` override, удаление `run --mode` |
| `.env.example` | Изменить | Комментарий про fallback для `deploy scheduled` |
| `docs/specs/2026-06-10-global-rewrite-design.md` | Изменить | Пометка об устаревших CLI entry points |

---

### Задача 1: Зависимости typer и questionary

**Файлы:**
- Изменить: `pyproject.toml`

- [ ] **Шаг 1: Добавить зависимости и entry point**

В `pyproject.toml` в `dependencies` добавить:

```toml
    "questionary>=2.1.1",
    "typer>=0.25.1",
```

После блока `[project]` добавить:

```toml
[project.scripts]
matrix-controller = "src.interfaces.cli.app:app"
```

- [ ] **Шаг 2: Установить зависимости**

Запуск: `uv sync`

Ожидается: exit 0, в lockfile появились `typer` и `questionary`

---

### Задача 2: format_matrix_choice_label

**Файлы:**
- Создать: `tests/interfaces/cli/test_matrix_choice_label.py`
- Создать: `src/interfaces/cli/matrix_choice_label.py`

- [ ] **Шаг 1: Написать падающие тесты**

```python
# tests/interfaces/cli/test_matrix_choice_label.py
from __future__ import annotations

from src.domain.entities.matrix import Matrix
from src.domain.value_objects.ids.vending_machine_id import VMId
from src.interfaces.cli.matrix_choice_label import format_matrix_choice_label
from tests.application.conftest import make_cell


def test_format_matrix_choice_label_with_machines() -> None:
    matrix = Matrix(
        name="Матрица_А",
        cells=[make_cell()],
        vending_machines_ids=[VMId(101), VMId(102)],
    )
    assert format_matrix_choice_label(matrix) == "Матрица_А — 101, 102"


def test_format_matrix_choice_label_no_machines() -> None:
    matrix = Matrix(
        name="Матрица_А",
        cells=[make_cell()],
        vending_machines_ids=[],
    )
    assert format_matrix_choice_label(matrix) == "Матрица_А — (нет аппаратов)"
```

- [ ] **Шаг 2: Запустить тесты и убедиться что падают**

Запуск: `uv run pytest tests/interfaces/cli/test_matrix_choice_label.py -q`

Ожидается: FAIL (`ModuleNotFoundError: src.interfaces.cli.matrix_choice_label`)

- [ ] **Шаг 3: Написать минимальную реализацию**

```python
# src/interfaces/cli/matrix_choice_label.py
from __future__ import annotations

from beartype import beartype

from src.domain.entities.matrix import Matrix


@beartype
def format_matrix_choice_label(matrix: Matrix) -> str:
    if not matrix.vending_machines_ids:
        return f"{matrix.name} — (нет аппаратов)"
    numbers = ", ".join(str(vm.value) for vm in matrix.vending_machines_ids)
    return f"{matrix.name} — {numbers}"
```

- [ ] **Шаг 4: Запустить тесты и убедиться что проходят**

Запуск: `uv run pytest tests/interfaces/cli/test_matrix_choice_label.py -q`

Ожидается: PASS (2 passed)

---

### Задача 3: QuestionarySelector

**Файлы:**
- Создать: `src/interfaces/cli/questionary_selector.py`

`QuestionarySelector` отдельно не тестируется (обёртка над библиотекой, см. спек § Тестирование).

- [ ] **Шаг 1: Создать QuestionarySelector**

```python
# src/interfaces/cli/questionary_selector.py
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
```

- [ ] **Шаг 2: Проверить импорт**

Запуск: `uv run python -c "from src.interfaces.cli.questionary_selector import QuestionarySelector; print(QuestionarySelector)"`

Ожидается: exit 0, вывод `<class '...QuestionarySelector'>`

---

### Задача 4: InteractiveMatrixSelection с labels

**Файлы:**
- Изменить: `src/infrastructure/selection/interactive_selection.py`
- Создать: `tests/infrastructure/selection/test_interactive_matrix_selection.py`

- [ ] **Шаг 1: Написать падающий тест**

Создать каталог `tests/infrastructure/selection/` с пустым `__init__.py`, если его нет.

```python
# tests/infrastructure/selection/test_interactive_matrix_selection.py
from __future__ import annotations

from dataclasses import dataclass, field

from src.domain.entities.matrix import Matrix
from src.domain.value_objects.ids.vending_machine_id import VMId
from src.infrastructure.selection.interactive_selection import InteractiveMatrixSelection
from tests.application.conftest import make_cell


@dataclass
class FakeSelector:
    last_items: list[tuple[str, str]] = field(default_factory=list)
    return_value: list[str] = field(default_factory=list)

    def select_items(self, items: list[tuple[str, str]]) -> list[str]:
        self.last_items = items
        return self.return_value


def test_interactive_matrix_selection_returns_names() -> None:
    fake = FakeSelector(return_value=["M1"])
    selection = InteractiveMatrixSelection(selector=fake)
    matrices = [
        Matrix(
            name="M1",
            cells=[make_cell()],
            vending_machines_ids=[VMId(101), VMId(102)],
        ),
        Matrix(name="M2", cells=[make_cell()], vending_machines_ids=[]),
    ]

    result = selection.select(matrices)

    assert result == ["M1"]
    assert fake.last_items == [
        ("M1 — 101, 102", "M1"),
        ("M2 — (нет аппаратов)", "M2"),
    ]
```

- [ ] **Шаг 2: Запустить тест и убедиться что падает**

Запуск: `uv run pytest tests/infrastructure/selection/test_interactive_matrix_selection.py::test_interactive_matrix_selection_returns_names -q`

Ожидается: FAIL (`TypeError: InteractiveMatrixSelection.__init__() got an unexpected keyword argument 'selector'` или неверные labels)

- [ ] **Шаг 3: Обновить InteractiveMatrixSelection**

```python
# src/infrastructure/selection/interactive_selection.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from beartype import beartype

from src.domain.entities.matrix import Matrix
from src.domain.ports.matrix_selection import MatrixSelectionPort
from src.interfaces.cli.matrix_choice_label import format_matrix_choice_label


class MatrixItemSelector(Protocol):
    def select_items(self, items: list[tuple[str, str]]) -> list[str]: ...


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class InteractiveMatrixSelection(MatrixSelectionPort):
    selector: MatrixItemSelector

    def select(self, available: list[Matrix]) -> list[str]:
        choices = [(format_matrix_choice_label(m), m.name) for m in available]
        return self.selector.select_items(choices)
```

- [ ] **Шаг 4: Запустить тест и убедиться что проходит**

Запуск: `uv run pytest tests/infrastructure/selection/test_interactive_matrix_selection.py::test_interactive_matrix_selection_returns_names -q`

Ожидается: PASS

- [ ] **Шаг 5: Обновить wiring в Container**

В `src/bootstrap/container.py`:

1. Заменить импорт:
```python
from src.interfaces.cli.questionary_selector import QuestionarySelector
```
(удалить `from src.infrastructure.selection.interactive_selector import InteractiveSelector`)

2. В `configure_interactive_selection`:
```python
    def configure_interactive_selection(self) -> None:
        self.set_matrix_selection(
            InteractiveMatrixSelection(selector=QuestionarySelector())
        )
```

- [ ] **Шаг 6: Убедиться что существующие тесты проходят**

Запуск: `uv run pytest tests/interfaces/cli/test_configured_selection.py -q`

Ожидается: PASS (2 passed)

---

### Задача 5: deploy_interactive и deploy_scheduled

**Файлы:**
- Создать: `src/interfaces/cli/deploy_interactive.py`
- Создать: `src/interfaces/cli/deploy_scheduled.py`
- Удалить: `src/interfaces/cli/run_interactive.py`
- Удалить: `src/interfaces/cli/run_scheduled.py`

- [ ] **Шаг 1: Создать deploy_interactive.py**

```python
# src/interfaces/cli/deploy_interactive.py
from __future__ import annotations

from src.bootstrap.container import Container


async def deploy_interactive(container: Container) -> int:
    container.configure_interactive_selection()
    job = await container.run_deployment(trigger="interactive")
    return 0 if job.status in ("completed", "partial") else 1
```

- [ ] **Шаг 2: Создать deploy_scheduled.py**

```python
# src/interfaces/cli/deploy_scheduled.py
from __future__ import annotations

from src.bootstrap.container import Container


async def deploy_scheduled(container: Container, scheduled_matrix_names: str) -> int:
    container.configure_scheduled_selection(scheduled_matrix_names)
    job = await container.run_deployment(trigger="scheduled")
    return 0 if job.status in ("completed", "partial") else 1
```

- [ ] **Шаг 3: Удалить старые файлы**

Удалить `src/interfaces/cli/run_interactive.py` и `src/interfaces/cli/run_scheduled.py`.

- [ ] **Шаг 4: Проверить что старые импорты нигде не остались**

Запуск: `uv run python -c "import main"`

Ожидается: FAIL до обновления `main.py` (задача 6) — это нормально на этом шаге; после задачи 6 — PASS

---

### Задача 6: Typer app и main.py

**Файлы:**
- Создать: `src/interfaces/cli/app.py`
- Изменить: `main.py`

- [ ] **Шаг 1: Написать падающий тест test_run_command_removed**

```python
# tests/interfaces/cli/test_app.py
from __future__ import annotations

from typer.testing import CliRunner

from src.interfaces.cli.app import app


def test_run_command_removed() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["run", "--mode", "interactive"])
    assert result.exit_code != 0
```

- [ ] **Шаг 2: Запустить тест и убедиться что падает**

Запуск: `uv run pytest tests/interfaces/cli/test_app.py::test_run_command_removed -q`

Ожидается: FAIL (`ModuleNotFoundError: app` или `exit_code == 0`)

- [ ] **Шаг 3: Создать app.py**

```python
# src/interfaces/cli/app.py
from __future__ import annotations

import asyncio
import logging
import sys

import typer

from src.bootstrap.container import Container
from src.bootstrap.settings import Settings
from src.infrastructure.logging import configure_logging
from src.interfaces.cli.deploy_interactive import deploy_interactive
from src.interfaces.cli.deploy_scheduled import deploy_scheduled

app = typer.Typer(prog_name="matrix-controller", no_args_is_help=True)
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
```

- [ ] **Шаг 4: Обновить main.py**

```python
# main.py
from src.interfaces.cli.app import app

if __name__ == "__main__":
    app()
```

- [ ] **Шаг 5: Запустить test_run_command_removed**

Запуск: `uv run pytest tests/interfaces/cli/test_app.py::test_run_command_removed -q`

Ожидается: PASS

- [ ] **Шаг 6: Проверить help новых команд**

Запуск: `uv run matrix-controller --help`

Ожидается: exit 0, в выводе команды `deploy`, `sync`, без `run`

Запуск: `uv run matrix-controller deploy --help`

Ожидается: exit 0, подкоманды `interactive`, `scheduled`

---

### Задача 7: test_deploy_scheduled_cli_names_override

**Файлы:**
- Изменить: `tests/interfaces/cli/test_app.py`

- [ ] **Шаг 1: Написать падающий тест**

Добавить в `tests/interfaces/cli/test_app.py`:

```python
from dataclasses import dataclass


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
```

- [ ] **Шаг 2: Запустить новые тесты**

Запуск: `uv run pytest tests/interfaces/cli/test_app.py -q`

Ожидается: PASS (4 passed)

---

### Задача 8: Удаление InteractiveSelector

**Файлы:**
- Удалить: `src/infrastructure/selection/interactive_selector.py`

- [ ] **Шаг 1: Удалить файл**

Удалить `src/infrastructure/selection/interactive_selector.py`.

- [ ] **Шаг 2: Убедиться что ссылок не осталось**

Запуск: `uv run pytest -q`

Ожидается: 0 failed

---

### Задача 9: Миграция документации

**Файлы:**
- Изменить: `.env.example`
- Изменить: `docs/specs/2026-06-10-global-rewrite-design.md`

- [ ] **Шаг 1: Обновить .env.example**

Заменить комментарий к `SCHEDULED_MATRIX_NAMES`:

```dotenv
# deploy scheduled: fallback если CLI --names не передан; "*" — все матрицы, или matrix_a,matrix_b
SCHEDULED_MATRIX_NAMES=*
```

- [ ] **Шаг 2: Пометить устаревшие entry points в global-rewrite-design**

В таблице Selection policies (`docs/specs/2026-06-10-global-rewrite-design.md`, § Selection policies) заменить строки:

| `InteractiveMatrixSelection` | `main.py run --mode interactive` |
| `ConfiguredMatrixSelection` | `main.py run --mode scheduled` — ... |

на:

| `InteractiveMatrixSelection` | `matrix-controller deploy interactive` (см. [cli-typer-questionary-design.md](./2026-06-10-cli-typer-questionary-design.md)) |
| `ConfiguredMatrixSelection` | `matrix-controller deploy scheduled` — `--names` или `SCHEDULED_MATRIX_NAMES` |

Добавить после таблицы одну строку:

> **Примечание (2026-06-10):** команда `run --mode` удалена; актуальные CLI entry points — в [2026-06-10-cli-typer-questionary-design.md](./2026-06-10-cli-typer-questionary-design.md).

---

## Само-ревью

### Покрытие спека

| Требование спека | Задача |
|------------------|--------|
| `typer` + `questionary` | 1 |
| `format_matrix_choice_label` | 2 |
| `QuestionarySelector` | 3 |
| `InteractiveMatrixSelection` с labels | 4 |
| Команды `deploy interactive/scheduled`, `sync` | 6 |
| `--names` переопределяет env | 7 |
| Удаление `run --mode` | 6, 7 |
| Коды выхода 0/1/2 | 6 (`app.py`) |
| Удаление `InteractiveSelector` | 8 |
| Тесты из спека § Тестирование | 2, 4, 7 |
| `.env.example`, global-rewrite-design | 9 |
| `ConfiguredMatrixSelection` без изменений | — (существующие тесты) |

Пробелов нет.

### Плейсхолдеры

Не обнаружены.

### Согласованность имён

- `selector` / `MatrixItemSelector` / `QuestionarySelector` — единообразно в задачах 3–5
- `deploy_interactive` / `deploy_scheduled` — функции и Typer-команды с суффиксом `_cmd`
- `scheduled_names` / `settings.scheduled_matrix_names` — логика из спека § deploy scheduled

---

## Покрытие спека (чеклист для исполнителя)

После всех задач:

```bash
uv run pytest tests/interfaces/cli/ tests/infrastructure/selection/ -q
uv run matrix-controller --help
uv run matrix-controller deploy --help
```

Ожидается: все тесты PASS; help показывает `deploy` и `sync`.
