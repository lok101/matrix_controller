# CLI на typer + questionary: дизайн

**Дата:** 2026-06-10  
**Статус:** утверждён в brainstorming  
**Контекст:** замена `argparse` + самописного `InteractiveSelector` на `typer` + `questionary` по образцу `snanck_loading_automatization`, с отображением номеров аппаратов в подписях матриц.

## Цель

Дать оператору удобный интерактивный CLI для выбора матриц к деплою, где в списке видны **имя матрицы** и **номера привязанных аппаратов**. Реструктурировать команды: `deploy interactive` / `deploy scheduled` + `sync`.

## Требования (зафиксировано в brainstorming)

| Параметр | Решение |
|----------|---------|
| Единица выбора | Матрицы (как сейчас) |
| Подпись в списке | `Имя — 101, 102` или `Имя — (нет аппаратов)` |
| CLI-стек | `typer` + `questionary` |
| Структура команд | `deploy interactive` / `deploy scheduled` + `sync` |
| Scheduled names | CLI `--names` переопределяет env `SCHEDULED_MATRIX_NAMES`; если флаг не передан — читаем env |
| Обратная совместимость | Команда `run --mode` удаляется |

## Выбранный подход

**Вариант 1: тонкий Typer-слой + замена селектора.**

- `typer`-приложение в `src/interfaces/cli/`
- `InteractiveSelector` заменяется на `QuestionarySelector` (`questionary.checkbox`)
- Форматирование подписи — в `format_matrix_choice_label()` из `Matrix.vending_machines_ids`
- `MatrixSelectionPort` и use cases не меняются

Альтернативы отклонены: абстрактный `ChoiceSelectorPort` (лишняя сложность), обогащение в CLI-слое (размазывает selection).

## Архитектура CLI

### Команды

```bash
# Интерактивный deploy (questionary checkbox)
uv run matrix-controller deploy interactive

# Scheduled deploy (cron / Task Scheduler)
uv run matrix-controller deploy scheduled
uv run matrix-controller deploy scheduled --names "matrix_a,matrix_b"
uv run matrix-controller deploy scheduled --names "*"

# Только sync кэшей
uv run matrix-controller sync
```

### Структура файлов

```
src/interfaces/cli/
  app.py                  # typer app: deploy (interactive/scheduled), sync
  deploy_interactive.py   # бывший run_interactive.py
  deploy_scheduled.py     # бывший run_scheduled.py
  matrix_choice_label.py  # format_matrix_choice_label(matrix) → str
  questionary_selector.py # обёртка questionary.checkbox
```

`main.py` остаётся как `if __name__ == "__main__"` entry point, делегирует в `app()`.

### pyproject.toml

```toml
dependencies = [
    # ... существующие ...
    "questionary>=2.1.1",
    "typer>=0.25.1",
]

[project.scripts]
matrix-controller = "src.interfaces.cli.app:app"
```

### Коды выхода

| Код | Ситуация |
|-----|----------|
| 0 | Успех (`completed` / `partial` для deploy, sync) |
| 1 | Ошибка deploy (`failed`) |
| 2 | Ошибка конфигурации (`Settings()`) |

## Интерактивный выбор

### Форматирование подписи

```python
def format_matrix_choice_label(matrix: Matrix) -> str:
    if not matrix.vending_machines_ids:
        return f"{matrix.name} — (нет аппаратов)"
    numbers = ", ".join(str(vm.value) for vm in matrix.vending_machines_ids)
    return f"{matrix.name} — {numbers}"
```

Номера из `Matrix.vending_machines_ids` (заполняются при sync из Google Sheets). Репозиторий аппаратов для подписи не используется.

### QuestionarySelector

Заменяет `InteractiveSelector` (cls/clear/input). Интерфейс:

```python
class QuestionarySelector:
    def select_items(self, items: list[tuple[str, str]]) -> list[str]:
        # items = [(label, value), ...]
        # label — отображаемая подпись, value — matrix.name
        # asyncio.run(questionary.checkbox(...).ask_async())
```

- Промпт: `"Выберите матрицы (пробел — отметить, enter — подтвердить):"`
- Пустой выбор, Esc или Ctrl+C → `[]` без traceback

### InteractiveMatrixSelection

```python
def select(self, available: list[Matrix]) -> list[str]:
    choices = [(format_matrix_choice_label(m), m.name) for m in available]
    return self.selector.select_items(choices)
```

Порт `MatrixSelectionPort.select()` остаётся синхронным. `questionary` вызывается внутри selector через `asyncio.run()` (паттерн snanck).

### Поток deploy interactive

```
deploy interactive
  → Settings() + Container (async with)
  → RunDeploymentJobUseCase.execute(trigger="interactive")
      → sync_all_caches
      → matrix_repository.get_all()
      → InteractiveMatrixSelection.select()  # questionary
      → deploy_matrices(selected_names)
```

Sync перед выбором — как сейчас: пользователь видит актуальный список.

### Крайние случаи

| Ситуация | Поведение |
|----------|-----------|
| Нет матриц после sync | Пустой checkbox → `[]` → job `completed`, exit 0 |
| Матрица без аппаратов | `Имя — (нет аппаратов)`, выбрать можно |
| Ничего не выбрано | `[]` → job `completed`, exit 0 |
| Ctrl+C / Esc | `[]`, без traceback |

## deploy scheduled

### Разрешение списка матриц

```python
names = cli_names if cli_names is not None else settings.scheduled_matrix_names
```

- Флаг `--names` опциональный (`typer.Option(None, "--names")`)
- Пустая строка в флаге → `typer.BadParameter`
- `ConfiguredMatrixSelection` не меняется: `"*"` — все, иначе CSV имён

### Примеры cron / Task Scheduler

```bash
uv run matrix-controller deploy scheduled
uv run matrix-controller deploy scheduled --names "matrix_a,matrix_b"
```

## Обработка ошибок

| Слой | Поведение |
|------|-----------|
| Конфигурация | `typer.echo(..., err=True)` → exit 2 |
| Sync (`SynchronizationError`) | Job `failed`, exit 1 |
| Deploy partial | exit 0 |
| Deploy failed | exit 1 |
| Scheduled: невалидный `--names` | `typer.BadParameter` до job |
| Scheduled: имена не в кэше | Пустой selection → job `completed`, exit 0 |

## Тестирование

| Тест | Проверяет |
|------|-----------|
| `test_format_matrix_choice_label_with_machines` | `Матрица_А — 101, 102` |
| `test_format_matrix_choice_label_no_machines` | `Матрица_А — (нет аппаратов)` |
| `test_interactive_matrix_selection_returns_names` | Fake-selector: labels + возврат `matrix.name` |
| `test_configured_selection_*` | Без изменений (уже есть) |
| `test_deploy_scheduled_cli_names_override` | `--names` переопределяет env |
| `test_run_command_removed` | `run --mode` не принимается |

`QuestionarySelector` отдельно не тестируется (обёртка над библиотекой). Интерактив тестируется через injectable fake selector в `InteractiveMatrixSelection`.

## Миграция документации

| Файл | Изменение |
|------|-----------|
| `.env.example` | Комментарий: `SCHEDULED_MATRIX_NAMES` — fallback для `deploy scheduled` |
| `docs/specs/2026-06-10-global-rewrite-design.md` | Пометка: CLI entry points устарели, см. этот спек |

## Вне scope (YAGNI)

- `--names` для `deploy interactive`
- JSON-файл с выбором (как `--batches-file` в snanck)
- Webhook selection
- Изменения `MatrixSelectionPort` или use cases
- Сохранение команды `run --mode` для обратной совместимости

## Удаляемый код

- `src/infrastructure/selection/interactive_selector.py` (`InteractiveSelector`)
- `argparse` логика в `main.py` (заменяется делегированием в typer app)
- `src/interfaces/cli/run_interactive.py` / `run_scheduled.py` (переименование)
