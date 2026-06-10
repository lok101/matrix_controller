# Inline kit-api + улучшение надёжности

**Дата:** 2026-06-10  
**Статус:** утверждён  
**Вариант:** 2 — inlining `kit-api` + надёжность, без смены общей архитектуры

## Цель

Убрать зависимость от внешней библиотеки `kit-api` (git), перенести в проект только используемый код API Kit Vending, и повысить надёжность обработки ошибок при загрузке и применении матриц — без перестройки слоёв `domain` / `application` / `controllers`.

## Контекст

Проект — CLI-утилита для загрузки матриц товаров из Google Sheets в Kit Vending API и применения на торговых аппаратах. Архитектура уже следует ports & adapters.

Из `kit-api` используется только часть:

| Метод API | Назначение |
|-----------|------------|
| `get_vending_machines` | синхронизация кэша аппаратов |
| `get_vending_machine_states` | проверка статуса load/apply |
| `create_matrix` | создание матрицы в Kit |
| `bound_matrix_to_vending_machine` | привязка матрицы к аппарату |
| `send_command_to_vending_machine` | команды LOAD_MATRIX / APPLY_MATRIX |

Не переносим: `get_sales`, `get_products`, `get_recipes`, `get_product_matrices` и связанные модели.

## Выбранный подход

**Вариант B:** inlining + выделение общей логики команд (`MatrixCommandWorkflow`), типизированные внутренние результаты, тесты на клиент, workflow и адаптеры.

Отклонённые альтернативы:

- **A (прямой перенос):** быстрее, но сохраняет дублирование retry/poll в `download` и `apply`.
- **C (порт для Kit API клиента):** избыточен — адаптеры уже являются портами domain.

## Структура файлов

```
src/infrastructure/kit_vending/
├── api/
│   ├── client.py              # KitVendingAPIClient (5 методов + auth + retry)
│   ├── account.py             # KitAPIAccount
│   ├── config.py              # KitAPIConfig (dataclass из env)
│   ├── enums.py               # ResultCode, VendingMachineCommand, VendingMachineStatus
│   ├── exceptions.py          # KitAPIError, KitAPIResponseError, ...
│   ├── models/
│   │   ├── vending_machines.py
│   │   └── vending_machine_state.py
│   ├── rate_limiter.py
│   ├── timestamp.py           # TimestampAPI
│   └── utils.py               # extract_statuses, extract_vending_machine_id
├── adapters/
│   ├── upload_matrix.py
│   ├── bind_matrix_to_machine.py
│   ├── download_matrix_to_vending_machine.py
│   └── apply_matrix_to_vending_machine.py
└── matrix_command_workflow.py # общая логика load/apply
```

Существующие адаптеры из `src/infrastructure/adapters/kit_vending/` переносятся в `src/infrastructure/kit_vending/adapters/`. Импорты в `main.py` и use cases обновляются.

## Переносимый код из kit-api

### API client

- Базовый URL: `https://api2.kit-invest.ru/APIService.svc`
- Авторизация: MD5(`{company_id}{password}{request_id}`)
- `RequestId` — timestamp с внешнего сервиса (TimestampAPI)
- Rate limiter: декоратор класса, параметры из env (`KIT_API_REQUEST_PER_WINDOW`, `KIT_API_WINDOW_SECONDS`, `KIT_API_BACKOFF_SECONDS`)
- Retry на `ResultCode.TOO_MANY_REQUEST` (27) с глобальным backoff

### Модели (Pydantic)

- `VendingMachinesCollection`, `ActiveVendingMachineModel`, `NotActiveVendingMachineModel`
- `VendingMachinesStatesCollection`, `VendingMachineStateModel`
- Утилиты: `extract_statuses`, `extract_vending_machine_id`

### Enum'ы

- `ResultCode`: SUCCESS=0, TOO_MANY_REQUEST=27
- `VendingMachineCommand`: LOAD_MATRIX=3, APPLY_MATRIX=4
- `VendingMachineStatus`: MATRIX_LOADED=21, NO_CONNECTION=1

### Исключения

- `KitAPIError` (базовый)
- `KitAPIAuthError`, `KitAPINetworkError`, `KitAPIResponseError` (с `result_code`), `KitAPIValidationError`

## Улучшение обработки ошибок

### Проблема

Адаптеры `download` и `apply` дублируют логику retry/poll. Ошибки глотаются с `return False`, в логах нет контекста шага.

### Решение

Внутренний тип в infrastructure (порты domain не меняются):

```python
@dataclass(frozen=True, slots=True)
class CommandResult:
    success: bool
    step: Literal["send_command", "wait", "verify_status"]
    message: str
    attempts: int
```

`MatrixCommandWorkflow` инкапсулирует паттерн:

1. Отправить команду (`send_command_to_vending_machine`)
2. Подождать (`matrix_load_timeout` / `matrix_apply_timeout`)
3. Проверить статус (`get_vending_machine_states` + predicate по `VendingMachineStatus`)

Параметры workflow (из текущих адаптеров):

- `max_retry_attempts`: 3
- `max_command_send_attempts`: 3
- `retry_send_command_timeout`: 10 сек
- `matrix_load_timeout` / `matrix_apply_timeout`: 120 сек

Retry-политика:

- `KitAPINetworkError`, `ResultCode.TOO_MANY_REQUEST` — retry отправки команды
- Остальные `KitAPIResponseError` — без retry, лог + `CommandResult(success=False)`

Адаптеры `DownloadMatrixToVendingMachineAdapter` и `ApplyMatrixToVendingMachineAdapter` делегируют в workflow, сами остаются тонкими, наружу по-прежнему `-> bool`.

`UploadAndApplyMatrixUseCase`: при ошибке на аппарате логирует `critical` с контекстом (шаг, попытки из workflow через адаптер) и продолжает остальные аппараты. Итоговая сводка в конце (успех / частичный / полный провал) — через существующий `asyncio.gather` + подсчёт ошибок.

## Конфигурация

Вынести Kit API настройки в `src/infrastructure/kit_vending/api/config.py`:

- `KIT_API_COMPANY_ID`, `KIT_API_LOGIN`, `KIT_API_PASSWORD`
- `KIT_API_REQUEST_PER_WINDOW`, `KIT_API_WINDOW_SECONDS`, `KIT_API_BACKOFF_SECONDS`

`main.py` читает конфиг один раз и передаёт в клиент. Полный `pydantic-settings` для всего проекта — за рамками этого этапа.

## Зависимости

Удалить из `pyproject.toml`:

```toml
"kit-api @ git+https://github.com/lok101/kit-vending-api.git",
```

Добавить в dev-зависимости:

```toml
[dependency-groups]
dev = ["pytest>=8.0"]
```

Остаются: `aiohttp`, `pydantic`, `beartype`, `dotenv`.

## Тесты

Стиль: sync `def test_`, async через `asyncio.run()`, без `pytest-asyncio`. Паттерн AAA.

| Файл | Что проверяем |
|------|---------------|
| `tests/infrastructure/kit_vending/test_client.py` | auth sign, успешный ответ, `ResultCode != 0`, retry на code 27, сетевые ошибки |
| `tests/infrastructure/kit_vending/test_models.py` | парсинг `VendingMachines`, `extract_statuses`, `extract_vending_machine_id` |
| `tests/infrastructure/kit_vending/test_matrix_command_workflow.py` | happy path, timeout, retry send, статус не совпал |
| `tests/infrastructure/kit_vending/test_adapters.py` | upload/create_matrix, bind — с fake client |

Моки: `unittest.mock.AsyncMock` для `aiohttp.ClientSession.post`, без реальных HTTP-запросов.

## Вне скоупа

- Смена структуры `domain` / `application` / `controllers`
- Google Sheets адаптеры
- Интерактивный селектор
- Параллельный `asyncio.gather` в `SelectAndUploadMatricesUseCase`
- Раскомментирование валидации матриц (`MatrixValidator`)
- Полный `pydantic-settings` для всего проекта
- Integration-тесты с реальным Kit API

## Критерии готовности

1. `kit-api` удалён из зависимостей, `uv sync` проходит
2. Проект запускается, все 5 API-методов работают как раньше
3. `uv run pytest` — зелёный
4. Логи при ошибке load/apply содержат шаг и номер попытки
5. Нет импортов `from kit_api import ...` в коде проекта

## Порядок реализации (ориентир для плана)

1. Создать `src/infrastructure/kit_vending/api/` — enums, exceptions, utils, models, rate_limiter, timestamp, config, client
2. Написать тесты client + models (TDD red/green)
3. Создать `MatrixCommandWorkflow` + тесты
4. Перенести адаптеры, подключить workflow в download/apply
5. Обновить `main.py`, `sync_vending_machines_cache.py`, импорты
6. Удалить `kit-api` из `pyproject.toml`, `uv sync`
7. Тесты адаптеров, финальная верификация
