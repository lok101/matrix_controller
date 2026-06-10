# Глобальное переписывание matrix-controller

**Дата:** 2026-06-10  
**Статус:** утверждён  
**Подход:** A — уточнённый Clean Architecture  
**Стратегия:** big bang в той же ветке

## Цель

Переписать проект с нуля с сохранением бизнес-сути, заложить тестируемую архитектуру под автоматизацию (расписание сейчас, webhook позже) и подготовить расширение без накопления техдолга.

## Контекст

**Проект** — CLI-утилита: Google Sheets → матрицы товаров → Kit Vending API (upload → bind → load → apply).

**Текущее состояние:**
- Слои `domain` / `application` / `infrastructure` / `controllers`, ports & adapters
- `kit_vending` недавно переписан inline с тестами (~5 файлов в `tests/infrastructure/kit_vending/`)
- Тестов на domain, application, Google Sheets, controllers — нет
- Техдолг: опечатка `entites`, дубли старых адаптеров, `main.py` как composition root (~140 строк), `MatrixValidator` отключён, репозитории размазаны между domain и application

**Требования пользователя:**
- Тестируемость, качество архитектуры, готовность к расширению
- Автоматизация: расписание сейчас, webhook в будущем
- Интерактивный режим сохранить как отдельный entry point
- Persistent-хранилище: архитектура под БД, первая реализация in-memory (+ SQLite-ready заглушка)
- Big bang в той же ветке

## Отклонённые альтернативы

| Вариант | Почему отклонён |
|---------|-----------------|
| B — feature-slices | Избыточен для текущего размера; дороже при big bang |
| C — тонкое ядро без портов | Противоречит цели тестируемости и расширения |
| Strangler / слой за слоем | Пользователь выбрал big bang |
| SQLite/PostgreSQL сразу | Достаточно in-memory + готовый port; SQLite позже |

## Архитектура и структура

```
src/
├── domain/
│   ├── entities/              # entites → entities
│   ├── value_objects/
│   ├── ports/                 # Kit, Sheets, selection policy
│   ├── repositories/          # Matrix, Product, VendingMachine, JobRun
│   ├── services/              # MatrixValidator (domain rules)
│   └── exceptions.py
├── application/
│   └── use_cases/
│       ├── sync/              # SyncProducts, SyncMatrices, SyncVendingMachines
│       ├── deploy/            # UploadAndApplyMatrix, DeployMatrices (batch)
│       └── orchestration/     # RunDeploymentJob — единая точка для всех триггеров
├── infrastructure/
│   ├── google_sheets/
│   ├── kit_vending/           # существующий код + тесты (перенос as-is)
│   └── persistence/
│       ├── in_memory/         # текущее поведение
│       └── sqlite/            # заглушка под JobRun / audit
├── interfaces/
│   ├── cli/
│   │   ├── interactive.py     # ручной выбор матриц
│   │   └── scheduled.py       # запуск по конфигу расписания
│   └── http/                  # модуль-заглушка под webhook
└── bootstrap/
    ├── container.py           # DI-сборка зависимостей
    └── settings.py            # pydantic-settings из env
main.py                        # тонкий: argparse → container → command
```

### Ключевые принципы

| Принцип | Решение |
|---------|---------|
| Один pipeline для всех режимов | `RunDeploymentJobUseCase`: sync caches → select matrices → deploy |
| Разные триггеры | Только entry points различаются; ядро одно |
| Selection policy | Порт `MatrixSelectionPort`: `InteractiveSelection`, `ConfiguredSelection`, позже `WebhookSelection` |
| Состояние job'ов | `JobRun` entity + `JobRunRepository` port; первая реализация — in-memory |
| Composition root | Вся ручная проводка из `main.py` → `bootstrap/container.py` |
| Kit Vending | Не переписываем — переносим `kit_vending/` и существующие тесты |

### Big bang порядок

1. Domain (entities, ports, repositories, services, exceptions)
2. Application use cases (TDD)
3. Infrastructure (persistence, google_sheets, kit_vending migrate)
4. Bootstrap (settings, container)
5. Interfaces (CLI, http stub)
6. Тонкий `main.py`
7. Удаление старой структуры

## Компоненты и поток данных

### Общий pipeline

Все режимы (interactive, scheduled, будущий webhook) вызывают один use case:

```
RunDeploymentJobUseCase
  ├── 1. SyncAllCachesUseCase
  ├── 2. MatrixSelectionPort.select() → list[MatrixName]
  └── 3. DeployMatricesUseCase(names, timestamp)
        └── для каждой матрицы параллельно:
              UploadAndApplyMatrixUseCase
                ├── MatrixValidator.validate()   # флаг settings.validate_matrices
                ├── UploadMatrixPort
                ├── BindMatrixPort
                ├── DownloadMatrixPort  (load)
                └── ApplyMatrixPort
```

### Domain

| Сущность / порт | Назначение |
|-----------------|------------|
| `Matrix`, `MatrixCell`, `Product`, `VendingMachine` | Бизнес-модель без изменений сути |
| `MatrixRepository`, `ProductRepository`, `VendingMachineRepository` | Кэш после sync; все интерфейсы в `domain/repositories/` |
| `JobRun`, `JobRunStatus` | id, trigger, started_at, finished_at, status, summary |
| `JobRunRepository` | Audit / idempotency (in-memory → SQLite позже) |
| `MatrixSelectionPort` | `select(available: list[Matrix]) → list[str]` |
| Kit-порты | `UploadMatrixPort`, `BindMatrixPort`, `DownloadMatrixPort`, `ApplyMatrixPort` — контракты без изменений |
| Sheets-порты | `GetAllMatricesPort`, `GetAllProductsPort` |
| `GetVendingMachinesPort` | Новый — убираем прямую зависимость sync от `KitVendingAPIClient` |
| `MatrixValidator` | `domain/services/` — чистые правила без I/O |

### Application use cases

| Use case | Ответственность |
|----------|-----------------|
| `SyncProductsCache` | Sheets → ProductRepository |
| `SyncMatricesCache` | Sheets → MatrixRepository |
| `SyncVendingMachinesCache` | Kit → VendingMachineRepository (через `GetVendingMachinesPort`) |
| `SyncAllCachesUseCase` | Последовательно: products → vending machines → matrices |
| `UploadAndApplyMatrixUseCase` | Одна matrix → N machines (последовательно per machine) |
| `DeployMatricesUseCase` | N matrices параллельно через `asyncio.gather` |
| `RunDeploymentJobUseCase` | JobRun lifecycle + sync → select → deploy |

**Порядок sync:** products → vending machines → matrices (матрицы резолвят товары из ProductRepository).

### Selection policies

| Реализация | Когда |
|------------|-------|
| `InteractiveMatrixSelection` | `main.py run --mode interactive` |
| `ConfiguredMatrixSelection` | `main.py run --mode scheduled` — имена из `settings.scheduled_matrix_names` или `*` (= все) |
| `WebhookMatrixSelection` | Заглушка в `interfaces/http/` — парсит payload → names (реализация позже) |

### JobRun — модель (фаза 1)

```python
@dataclass(frozen=True)
class JobRun:
    id: JobRunId
    trigger: Literal["interactive", "scheduled", "webhook"]
    status: Literal["running", "completed", "failed", "partial"]
    started_at: datetime
    finished_at: datetime | None
    matrices_total: int
    matrices_success: int
    matrices_failed: int
    error_summary: str | None
```

- Старт job → `create()` со status `running`
- Завершение → `update()` с итогами
- In-memory достаточно для cron; SQLite позже для истории и webhook dedup по `idempotency_key`

### CLI entry points (фаза 1)

```bash
uv run python main.py run --mode interactive
uv run python main.py run --mode scheduled
uv run python main.py sync    # только sync без deploy
```

Cron/Task Scheduler вызывает `run --mode scheduled`.

## Обработка ошибок

### Иерархия исключений (domain)

| Исключение | Когда |
|------------|-------|
| `SynchronizationError` | Sync не получил данные |
| `MatrixValidationError` | MatrixValidator — цена ниже закупочной, закупочная ≤ 0 |
| `UploadMatrixError` | Критический сбой deploy |
| `JobRunError` | Job не может стартовать (sync упал до deploy) |

Infrastructure-исключения (`KitAPIError`, сетевые) не пробрасываются в application — адаптеры переводят в `CommandResult(success=False)` или `None`.

### Политика

- **SyncAllCaches:** `SynchronizationError` → JobRun `failed`, deploy не стартует
- **DeployMatrices:** `asyncio.gather(return_exceptions=True)` — ошибка одной матрицы не блокирует остальные; итог `completed` | `partial` | `failed`
- **UploadAndApplyMatrix:** per-machine fail → log critical, continue; итог матрицы как сейчас
- **RunDeploymentJob:** всегда финализирует JobRun с summary

### Exit codes CLI

| Код | Значение |
|-----|----------|
| 0 | Job completed (включая partial — warning в логах) |
| 1 | Job failed |
| 2 | Misconfiguration |

Логи на русском, structured context: `matrix_name`, `machine_name`, `step`, `attempts`, `trigger`.

## Конфигурация

Единый `Settings` через `pydantic-settings` в `bootstrap/settings.py`:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    google_sheets_matrix_table_id: str

    kit_api_company_id: int
    kit_api_login: str
    kit_api_password: str
    kit_api_request_per_window: int = 5
    kit_api_window_seconds: int = 1
    kit_api_backoff_seconds: float = 1.0

    validate_matrices: bool = True
    matrix_load_timeout: int = 120
    matrix_apply_timeout: int = 120

    scheduled_matrix_names: str = "*"   # "*" или "matrix_a,matrix_b"

    log_level: str = "INFO"
```

`bootstrap/container.py` читает `Settings` один раз и собирает зависимости.

Зависимость: добавить `pydantic-settings` в `pyproject.toml`.

## Тестирование

### Стиль

- sync `def test_`, async через `asyncio.run()`
- AAA, без `pytest-asyncio`
- fakes/mocks на границах портов, без реальных HTTP/Sheets

### Структура

```
tests/
├── domain/
│   ├── test_matrix_validator.py
│   └── test_value_objects.py
├── application/
│   ├── conftest.py
│   ├── test_sync_all_caches.py
│   ├── test_upload_and_apply_matrix.py
│   ├── test_deploy_matrices.py
│   └── test_run_deployment_job.py
├── infrastructure/
│   ├── kit_vending/           # существующие — перенос as-is
│   ├── google_sheets/
│   └── persistence/
│       └── test_in_memory_job_run_repository.py
└── interfaces/
    └── cli/
        └── test_scheduled_selection.py
```

### Приоритет покрытия (TDD в плане)

| Приоритет | Область |
|-----------|---------|
| P0 | `MatrixValidator`, value objects |
| P0 | `UploadAndApplyMatrixUseCase` |
| P0 | `RunDeploymentJobUseCase` |
| P1 | Sync use cases, `DeployMatricesUseCase`, `kit_vending/*` |
| P2 | Google Sheets adapters, selection policies |
| P3 | CLI smoke |

Integration-тесты с реальным Kit API и Google Sheets — вне скоупа.

## Вне скоупа

- HTTP-сервер и webhook endpoint (только заглушка модуля)
- SQLite-реализация `JobRunRepository` (только интерфейс + in-memory)
- Параллельная обработка аппаратов внутри одной матрицы
- Обновление `AGENTS.md` (отдельная задача после реализации)
- CI/CD pipeline

## Критерии готовности

1. Старая структура `src/` заменена новой
2. `uv run python main.py run --mode interactive` — работает как раньше
3. `uv run python main.py run --mode scheduled` — deploy по конфигу
4. `uv run pytest` — зелёный, покрытие ≥ P0+P1
5. Старые пути импортов и дубли адаптеров отсутствуют
6. `MatrixValidator` включается через `VALIDATE_MATRICES=true` (default)
7. `JobRun` создаётся и финализируется на каждый запуск

## Связанные документы

- [Inline kit-api + надёжность](./2026-06-10-inline-kit-api-reliability-design.md) — `kit_vending/` переносится as-is
