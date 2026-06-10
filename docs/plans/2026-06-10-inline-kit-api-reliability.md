# План реализации: Inline kit-api + надёжность команд

> **Для агентов:** Используй скилл executing-plans для реализации этого плана задача за задачей. Шаги используют синтаксис чекбоксов (`- [ ]`) для отслеживания.

**Цель:** Убрать зависимость `kit-api`, перенести используемый код Kit Vending API в `src/infrastructure/kit_vending/`, выделить `MatrixCommandWorkflow` и покрыть тестами.

**Архитектура:** Порты domain не меняются (`-> bool` / `MatrixKitId | None`). Новый код живёт в infrastructure: `api/` (клиент, модели, enum'ы), `adapters/` (перенесённые адаптеры), `matrix_command_workflow.py` (общая логика load/apply). `UploadAndApplyMatrixUseCase` получает сводку по аппаратам; детали шага/попыток логирует workflow через адаптеры.

**Ключевые файлы / стек:** Python 3.12+, `uv`, `aiohttp`, `pydantic`, `beartype`, sync pytest + `asyncio.run()`.

**Спек:** [docs/specs/2026-06-10-inline-kit-api-reliability-design.md](../specs/2026-06-10-inline-kit-api-reliability-design.md)

---

## Карта файлов

| Файл | Ответственность |
|------|-----------------|
| `src/infrastructure/kit_vending/api/enums.py` | `ResultCode`, `VendingMachineCommand`, `VendingMachineStatus` |
| `src/infrastructure/kit_vending/api/exceptions.py` | Иерархия `KitAPI*` исключений |
| `src/infrastructure/kit_vending/api/utils.py` | `extract_statuses`, `extract_vending_machine_id` |
| `src/infrastructure/kit_vending/api/models/vending_machines.py` | Модели аппаратов |
| `src/infrastructure/kit_vending/api/models/vending_machine_state.py` | Модели состояний |
| `src/infrastructure/kit_vending/api/rate_limiter.py` | `RateLimiter`, `GlobalBackoff` |
| `src/infrastructure/kit_vending/api/timestamp.py` | `TimestampAPI` |
| `src/infrastructure/kit_vending/api/account.py` | `KitAPIAccount` |
| `src/infrastructure/kit_vending/api/config.py` | `KitAPIConfig.from_env()` |
| `src/infrastructure/kit_vending/api/client.py` | `KitVendingAPIClient` (5 методов) |
| `src/infrastructure/kit_vending/command_result.py` | `CommandResult` |
| `src/infrastructure/kit_vending/matrix_command_workflow.py` | Общий workflow load/apply |
| `src/infrastructure/kit_vending/adapters/*.py` | 4 адаптера (перенос + workflow) |
| `tests/infrastructure/kit_vending/test_*.py` | Юнит-тесты |
| `main.py` | Новые импорты + `KitAPIConfig` |
| `pyproject.toml` | Удалить `kit-api`, добавить `pytest` |

Удалить после переноса: `src/infrastructure/adapters/kit_vending/` (4 файла).

---

### Задача 1: Инфраструктура тестов и зависимостей

**Файлы:**
- Изменить: `pyproject.toml`
- Создать: `tests/__init__.py`

- [ ] **Шаг 1: Обновить `pyproject.toml`**

```toml
[project]
name = "matrix-controller"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "aiohttp>=3.12.15",
    "dotenv>=0.9.9",
    "gspread-asyncio>=2.0.0",
    "pydantic>=2.11.9",
    "beartype>=0.22.9",
    "tzlocal>=5.3.1",
]

[dependency-groups]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

> `kit-api` удаляем в задаче 12 — пока оставь зависимость, чтобы проект собирался до финального шага.

- [ ] **Шаг 2: Создать `tests/__init__.py`**

```python
```

- [ ] **Шаг 3: Установить dev-зависимости**

Запуск: `uv sync --group dev`
Ожидается: exit 0

- [ ] **Шаг 4: Проверить pytest**

Запуск: `uv run pytest -q`
Ожидается: `no tests ran` или exit 0 (0 failed)

---

### Задача 2: Enum'ы и исключения Kit API

**Файлы:**
- Создать: `src/infrastructure/kit_vending/__init__.py`
- Создать: `src/infrastructure/kit_vending/api/__init__.py`
- Создать: `src/infrastructure/kit_vending/api/enums.py`
- Создать: `src/infrastructure/kit_vending/api/exceptions.py`

- [ ] **Шаг 1: Создать пакеты**

`src/infrastructure/kit_vending/__init__.py` и `src/infrastructure/kit_vending/api/__init__.py` — пустые файлы.

- [ ] **Шаг 2: Создать `enums.py`**

```python
from __future__ import annotations

from enum import IntEnum


class ResultCode(IntEnum):
    SUCCESS = 0
    TOO_MANY_REQUEST = 27


class VendingMachineCommand(IntEnum):
    LOAD_MATRIX = 3
    APPLY_MATRIX = 4


class VendingMachineStatus(IntEnum):
    MATRIX_LOADED = 21
    NO_CONNECTION = 1
```

- [ ] **Шаг 3: Создать `exceptions.py`**

```python
from __future__ import annotations


class KitAPIError(Exception):
    """Базовое исключение для ошибок Kit API."""


class KitAPIAuthError(KitAPIError):
    """Ошибка аутентификации."""


class KitAPINetworkError(KitAPIError):
    """Ошибка сети."""


class KitAPIResponseError(KitAPIError):
    """Ошибка ответа от API."""

    def __init__(self, message: str, result_code: int) -> None:
        self.result_code = result_code
        super().__init__(message)


class KitAPIValidationError(KitAPIError):
    """Ошибка валидации данных или конфигурации."""
```

- [ ] **Шаг 4: Smoke-import**

Запуск: `uv run python -c "from src.infrastructure.kit_vending.api.enums import ResultCode; from src.infrastructure.kit_vending.api.exceptions import KitAPIError; print(ResultCode.SUCCESS)"`
Ожидается: `0`

---

### Задача 3: Утилиты парсинга (TDD)

**Файлы:**
- Создать: `src/infrastructure/kit_vending/api/utils.py`
- Создать: `tests/infrastructure/kit_vending/__init__.py`
- Создать: `tests/infrastructure/kit_vending/test_models.py` (только тесты utils на этом этапе)

- [ ] **Шаг 1: Написать падающие тесты utils**

```python
from __future__ import annotations

from src.infrastructure.kit_vending.api.enums import VendingMachineStatus
from src.infrastructure.kit_vending.api.utils import extract_statuses, extract_vending_machine_id


def test_extract_statuses_parses_comma_separated_codes() -> None:
    result = extract_statuses("21,1,999")

    assert result == [VendingMachineStatus.MATRIX_LOADED, VendingMachineStatus.NO_CONNECTION]


def test_extract_statuses_empty_string_returns_empty_list() -> None:
    assert extract_statuses("") == []


def test_extract_vending_machine_id_from_bracketed_name() -> None:
    assert extract_vending_machine_id("[42] Кофе") == 42


def test_extract_vending_machine_id_returns_none_when_missing() -> None:
    assert extract_vending_machine_id("Без кода") is None
```

- [ ] **Шаг 2: Запустить тесты и убедиться что падают**

Запуск: `uv run pytest tests/infrastructure/kit_vending/test_models.py -q`
Ожидается: FAIL (`ModuleNotFoundError`)

- [ ] **Шаг 3: Реализовать `utils.py`**

```python
from __future__ import annotations

import re

from src.infrastructure.kit_vending.api.enums import VendingMachineStatus


def extract_statuses(statuses_str: str) -> list[VendingMachineStatus]:
    result: list[VendingMachineStatus] = []

    if statuses_str:
        for status in statuses_str.split(","):
            try:
                result.append(VendingMachineStatus(int(status)))
            except ValueError:
                continue

    return result


def extract_vending_machine_id(vending_machine_name: str) -> int | None:
    match = re.search(r"\[(\d+)\]", vending_machine_name)
    if match:
        return int(match.group(1))
    return None
```

- [ ] **Шаг 4: Запустить тесты и убедиться что проходят**

Запуск: `uv run pytest tests/infrastructure/kit_vending/test_models.py -q`
Ожидается: 4 passed

---

### Задача 4: Pydantic-модели (TDD)

**Файлы:**
- Создать: `src/infrastructure/kit_vending/api/models/__init__.py`
- Создать: `src/infrastructure/kit_vending/api/models/vending_machines.py`
- Создать: `src/infrastructure/kit_vending/api/models/vending_machine_state.py`
- Изменить: `tests/infrastructure/kit_vending/test_models.py`

- [ ] **Шаг 1: Дописать падающие тесты моделей**

Добавить в `test_models.py`:

```python
from src.infrastructure.kit_vending.api.models.vending_machine_state import (
    VendingMachineStateModel,
    VendingMachinesStatesCollection,
)
from src.infrastructure.kit_vending.api.models.vending_machines import (
    ActiveVendingMachineModel,
    VendingMachinesCollection,
)


def test_vending_machines_collection_parses_active_machine() -> None:
    raw = {
        "VendingMachines": [
            {
                "VendingMachineId": 100,
                "VendingMachineName": "[7] Кофе",
                "GoodsMatrix": 5,
                "CompanyId": 1,
                "ModemSerialNumber": 12345,
            }
        ]
    }

    collection = VendingMachinesCollection.model_validate(raw)
    active = collection.get_active()

    assert len(active) == 1
    assert isinstance(active[0], ActiveVendingMachineModel)
    assert active[0].id == 100
    assert active[0].number == 7
    assert active[0].name == "[7] Кофе"


def test_vending_machine_state_model_parses_statuses() -> None:
    raw = {"VendingMachineId": 100, "Statuses": "21,1"}

    model = VendingMachineStateModel.model_validate(raw)

    assert model.id == 100
    assert model.statuses == [VendingMachineStatus.MATRIX_LOADED, VendingMachineStatus.NO_CONNECTION]


def test_vending_machine_states_collection_get_all() -> None:
    raw = {
        "VendingMachines": [
            {"VendingMachineId": 1, "Statuses": "21"},
            {"VendingMachineId": 2, "Statuses": "1"},
        ]
    }

    collection = VendingMachinesStatesCollection.model_validate(raw)

    assert len(collection.get_all()) == 2
```

- [ ] **Шаг 2: Запустить и убедиться что падают**

Запуск: `uv run pytest tests/infrastructure/kit_vending/test_models.py -q`
Ожидается: FAIL

- [ ] **Шаг 3: Реализовать модели**

`src/infrastructure/kit_vending/api/models/__init__.py`:

```python
from src.infrastructure.kit_vending.api.models.vending_machine_state import (
    VendingMachineStateModel,
    VendingMachinesStatesCollection,
)
from src.infrastructure.kit_vending.api.models.vending_machines import (
    ActiveVendingMachineModel,
    NotActiveVendingMachineModel,
    VendingMachineModel,
    VendingMachinesCollection,
)

__all__ = [
    "ActiveVendingMachineModel",
    "NotActiveVendingMachineModel",
    "VendingMachineModel",
    "VendingMachinesCollection",
    "VendingMachineStateModel",
    "VendingMachinesStatesCollection",
]
```

`vending_machines.py` — перенос из `kit_api.models.vending_machines` с заменой импортов на `src.infrastructure.kit_vending.api.*`.

`vending_machine_state.py` — перенос из `kit_api.models.vending_machine_state` с заменой импортов.

- [ ] **Шаг 4: Запустить и убедиться что проходят**

Запуск: `uv run pytest tests/infrastructure/kit_vending/test_models.py -q`
Ожидается: 7 passed

---

### Задача 5: Rate limiter, timestamp, account, config

**Файлы:**
- Создать: `src/infrastructure/kit_vending/api/rate_limiter.py`
- Создать: `src/infrastructure/kit_vending/api/timestamp.py`
- Создать: `src/infrastructure/kit_vending/api/account.py`
- Создать: `src/infrastructure/kit_vending/api/config.py`

- [ ] **Шаг 1: Создать `rate_limiter.py`**

Перенести `GlobalBackoff` и `RateLimiter` из `kit_api.rate_limiter` без декоратора класса (лимитер будет instance-level в клиенте).

- [ ] **Шаг 2: Создать `timestamp.py`**

Перенести `TimestampAPI` из `kit_api.timestamp_api` с импортами `KitAPINetworkError`, `KitAPIError` из локальных `exceptions`.

- [ ] **Шаг 3: Создать `account.py`**

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class KitAPIAccount:
    login: str
    password: str
    company_id: int
```

- [ ] **Шаг 4: Создать `config.py`**

```python
from __future__ import annotations

import os
from dataclasses import dataclass

from src.infrastructure.kit_vending.api.exceptions import KitAPIValidationError


@dataclass(frozen=True, slots=True, kw_only=True)
class KitAPIConfig:
    company_id: int
    login: str
    password: str
    request_per_window: int = 1
    window_seconds: int = 10
    backoff_seconds: float = 60.0

    @classmethod
    def from_env(cls) -> KitAPIConfig:
        login = os.getenv("KIT_API_LOGIN")
        password = os.getenv("KIT_API_PASSWORD")
        company_id_raw = os.getenv("KIT_API_COMPANY_ID")

        if login is None or password is None or company_id_raw is None:
            raise KitAPIValidationError(
                "KIT_API_LOGIN, KIT_API_PASSWORD и KIT_API_COMPANY_ID обязательны в .env"
            )

        try:
            company_id = int(company_id_raw)
            request_per_window = int(os.getenv("KIT_API_REQUEST_PER_WINDOW", "1"))
            window_seconds = int(os.getenv("KIT_API_WINDOW_SECONDS", "10"))
            backoff_seconds = float(os.getenv("KIT_API_BACKOFF_SECONDS", "60.0"))
        except ValueError as exc:
            raise KitAPIValidationError(
                "KIT_API_COMPANY_ID, KIT_API_REQUEST_PER_WINDOW, "
                "KIT_API_WINDOW_SECONDS и KIT_API_BACKOFF_SECONDS должны быть числами."
            ) from exc

        return cls(
            company_id=company_id,
            login=login,
            password=password,
            request_per_window=request_per_window,
            window_seconds=window_seconds,
            backoff_seconds=backoff_seconds,
        )
```

- [ ] **Шаг 5: Smoke-import**

Запуск: `uv run python -c "from src.infrastructure.kit_vending.api.config import KitAPIConfig; print(KitAPIConfig)"`
Ожидается: exit 0

---

### Задача 6: KitVendingAPIClient (TDD)

**Файлы:**
- Создать: `src/infrastructure/kit_vending/api/client.py`
- Создать: `tests/infrastructure/kit_vending/test_client.py`

- [ ] **Шаг 1: Написать падающий тест auth sign**

```python
from __future__ import annotations

import asyncio
import hashlib
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.kit_vending.api.account import KitAPIAccount
from src.infrastructure.kit_vending.api.client import KitVendingAPIClient
from src.infrastructure.kit_vending.api.config import KitAPIConfig
from src.infrastructure.kit_vending.api.enums import ResultCode
from src.infrastructure.kit_vending.api.exceptions import KitAPIResponseError, KitAPINetworkError


_CONFIG = KitAPIConfig(
    company_id=99,
    login="user",
    password="secret",
    request_per_window=10,
    window_seconds=1,
    backoff_seconds=0.01,
)
_ACCOUNT = KitAPIAccount(login="user", password="secret", company_id=99)
_REQUEST_ID = 1700000000


def _make_client() -> KitVendingAPIClient:
    timestamp = AsyncMock()
    timestamp.async_get_now = AsyncMock(return_value=_REQUEST_ID)
    return KitVendingAPIClient(
        account=_ACCOUNT,
        config=_CONFIG,
        timestamp_provider=timestamp,
    )


def _mock_post_response(payload: dict) -> AsyncMock:
    response = AsyncMock()
    response.raise_for_status = MagicMock()
    response.json = AsyncMock(return_value=payload)
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=False)
    return response


def test_build_auth_sign_is_md5_of_company_password_request_id() -> None:
    client = _make_client()

    auth = client._build_auth(_REQUEST_ID, None)

    expected_sign = hashlib.md5(
        f"{_ACCOUNT.company_id}{_ACCOUNT.password}{_REQUEST_ID}".encode("utf-8")
    ).hexdigest()

    assert auth["Sign"] == expected_sign
    assert auth["CompanyId"] == 99
    assert auth["RequestId"] == _REQUEST_ID
    assert auth["UserLogin"] == "user"
```

- [ ] **Шаг 2: Запустить и убедиться что падает**

Запуск: `uv run pytest tests/infrastructure/kit_vending/test_client.py::test_build_auth_sign_is_md5_of_company_password_request_id -q`
Ожидается: FAIL

- [ ] **Шаг 3: Реализовать минимальный `client.py`**

Клиент содержит только 5 публичных методов из спека + `_build_auth`, `_async_send_post_request`, `_get_session`, `close`, context manager.

Ключевые отличия от оригинала:
- Принимает `config: KitAPIConfig` и `account: KitAPIAccount`
- `self._limiter = RateLimiter(config.request_per_window, config.window_seconds)`
- `self._backoff = GlobalBackoff(timeout=config.backoff_seconds)`
- В начале `_async_send_post_request`: `await self._limiter.wait()`
- Retry на `ResultCode.TOO_MANY_REQUEST` (до 2 попыток) с `await self._backoff.trigger_backoff()`
- Без методов `get_sales`, `get_products`, `get_recipes`, `get_product_matrices`

Скелет публичного API:

```python
async def get_vending_machines(self, account: KitAPIAccount | None = None) -> VendingMachinesCollection: ...
async def get_vending_machine_states(self, account: KitAPIAccount | None = None) -> VendingMachinesStatesCollection: ...
async def create_matrix(self, positions: list[dict], matrix_name: str, account: KitAPIAccount | None = None) -> int: ...
async def bound_matrix_to_vending_machine(self, matrix_id: int, machine_id: int, account: KitAPIAccount | None = None) -> ResultCode: ...
async def send_command_to_vending_machine(self, machine_id: int, command: VendingMachineCommand, account: KitAPIAccount | None = None) -> ResultCode: ...
```

- [ ] **Шаг 4: Запустить auth-тест**

Запуск: `uv run pytest tests/infrastructure/kit_vending/test_client.py::test_build_auth_sign_is_md5_of_company_password_request_id -q`
Ожидается: PASS

- [ ] **Шаг 5: Добавить тест успешного ответа**

```python
def test_get_vending_machines_success() -> None:
    payload = {
        "ResultCode": 0,
        "VendingMachines": [
            {
                "VendingMachineId": 1,
                "VendingMachineName": "[1] Тест",
                "GoodsMatrix": None,
                "CompanyId": 99,
                "ModemSerialNumber": 111,
            }
        ],
    }
    post_response = _mock_post_response(payload)
    session = AsyncMock()
    session.post = MagicMock(return_value=post_response)
    session.closed = False

    client = _make_client()
    client._session = session
    client._own_session = False

    collection = asyncio.run(client.get_vending_machines())

    assert len(collection.get_active()) == 1
```

- [ ] **Шаг 6: Запустить — PASS**

Запуск: `uv run pytest tests/infrastructure/kit_vending/test_client.py::test_get_vending_machines_success -q`
Ожидается: PASS

- [ ] **Шаг 7: Добавить тест `ResultCode != 0`**

```python
def test_send_command_raises_on_non_zero_result_code() -> None:
    payload = {"ResultCode": 5, "ErrorMessage": "Ошибка"}
    post_response = _mock_post_response(payload)
    session = AsyncMock()
    session.post = MagicMock(return_value=post_response)
    session.closed = False

    client = _make_client()
    client._session = session
    client._own_session = False

    with pytest.raises(KitAPIResponseError) as exc_info:
        asyncio.run(
            client.send_command_to_vending_machine(
                machine_id=1,
                command=__import__(
                    "src.infrastructure.kit_vending.api.enums",
                    fromlist=["VendingMachineCommand"],
                ).VendingMachineCommand.LOAD_MATRIX,
            )
        )

    assert exc_info.value.result_code == 5
```

- [ ] **Шаг 8: Запустить — PASS**

- [ ] **Шаг 9: Добавить тест retry на code 27**

```python
def test_async_send_post_retries_on_too_many_requests() -> None:
    ok_payload = {"ResultCode": 0, "VendingMachines": []}
    rate_limit_payload = {"ResultCode": 27, "ErrorMessage": "Too many"}

    responses = [_mock_post_response(rate_limit_payload), _mock_post_response(ok_payload)]
    session = AsyncMock()
    session.post = MagicMock(side_effect=responses)
    session.closed = False

    client = _make_client()
    client._session = session
    client._own_session = False

    collection = asyncio.run(client.get_vending_machines())

    assert collection.get_all() == []
    assert session.post.call_count == 2
```

- [ ] **Шаг 10: Запустить — PASS**

- [ ] **Шаг 11: Добавить тест сетевой ошибки**

```python
def test_async_send_post_raises_network_error() -> None:
    from aiohttp import ClientError

    session = AsyncMock()
    session.post = MagicMock(side_effect=ClientError("connection reset"))
    session.closed = False

    client = _make_client()
    client._session = session
    client._own_session = False

    with pytest.raises(KitAPINetworkError, match="Ошибка сети"):
        asyncio.run(client.get_vending_machines())
```

- [ ] **Шаг 12: Запустить все client-тесты**

Запуск: `uv run pytest tests/infrastructure/kit_vending/test_client.py -q`
Ожидается: 5 passed

---

### Задача 7: CommandResult + MatrixCommandWorkflow (TDD)

**Файлы:**
- Создать: `src/infrastructure/kit_vending/command_result.py`
- Создать: `src/infrastructure/kit_vending/matrix_command_workflow.py`
- Создать: `tests/infrastructure/kit_vending/test_matrix_command_workflow.py`

- [ ] **Шаг 1: Создать `command_result.py`**

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class CommandResult:
    success: bool
    step: Literal["send_command", "wait", "verify_status"]
    message: str
    attempts: int
```

- [ ] **Шаг 2: Написать падающий тест happy path load**

```python
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

from src.infrastructure.kit_vending.api.enums import VendingMachineCommand, VendingMachineStatus
from src.infrastructure.kit_vending.api.models.vending_machine_state import (
    VendingMachineStateModel,
    VendingMachinesStatesCollection,
)
from src.infrastructure.kit_vending.matrix_command_workflow import MatrixCommandWorkflow


def test_workflow_load_matrix_happy_path() -> None:
    client = AsyncMock()
    client.send_command_to_vending_machine = AsyncMock(return_value=0)
    client.get_vending_machine_states = AsyncMock(
        return_value=VendingMachinesStatesCollection.model_validate(
            {
                "VendingMachines": [
                    {"VendingMachineId": 10, "Statuses": "21"},
                ]
            }
        )
    )

    workflow = MatrixCommandWorkflow(
        kit_api_client=client,
        command=VendingMachineCommand.LOAD_MATRIX,
        status_predicate=lambda statuses: VendingMachineStatus.MATRIX_LOADED in statuses,
        wait_timeout_seconds=0,
        max_retry_attempts=3,
        max_command_send_attempts=3,
        retry_send_command_timeout_seconds=0,
    )

    result = asyncio.run(workflow.run(machine_kit_id=10, machine_name="[10] Кофе"))

    assert result.success is True
    assert result.step == "verify_status"
    assert result.attempts >= 1
```

- [ ] **Шаг 3: Запустить — FAIL**

Запуск: `uv run pytest tests/infrastructure/kit_vending/test_matrix_command_workflow.py::test_workflow_load_matrix_happy_path -q`
Ожидается: FAIL

- [ ] **Шаг 4: Реализовать `MatrixCommandWorkflow`**

```python
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass

from beartype import beartype

from src.infrastructure.kit_vending.api.client import KitVendingAPIClient
from src.infrastructure.kit_vending.api.enums import ResultCode, VendingMachineCommand, VendingMachineStatus
from src.infrastructure.kit_vending.api.exceptions import KitAPIError, KitAPIResponseError, KitAPINetworkError
from src.infrastructure.kit_vending.api.models.vending_machine_state import (
    VendingMachinesStatesCollection,
    VendingMachineStateModel,
)
from src.infrastructure.kit_vending.command_result import CommandResult

logger = logging.getLogger(__name__)


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class MatrixCommandWorkflow:
    kit_api_client: KitVendingAPIClient
    command: VendingMachineCommand
    status_predicate: Callable[[list[VendingMachineStatus]], bool]
    wait_timeout_seconds: int = 120
    max_retry_attempts: int = 3
    max_command_send_attempts: int = 3
    retry_send_command_timeout_seconds: int = 10

    async def run(self, machine_kit_id: int, machine_name: str) -> CommandResult:
        cycle_attempt = 0
        send_attempts = 0

        while cycle_attempt < self.max_retry_attempts:
            try:
                await self.kit_api_client.send_command_to_vending_machine(
                    machine_id=machine_kit_id,
                    command=self.command,
                )
                send_attempts += 1

            except (KitAPINetworkError, KitAPIResponseError) as exc:
                send_attempts += 1
                if isinstance(exc, KitAPIResponseError) and exc.result_code != ResultCode.TOO_MANY_REQUEST:
                    message = f"Ошибка API без retry: {exc}"
                    logger.error(
                        "%s. Аппарат %s, шаг send_command, попытка #%s.",
                        message,
                        machine_name,
                        send_attempts,
                    )
                    return CommandResult(
                        success=False,
                        step="send_command",
                        message=message,
                        attempts=send_attempts,
                    )

                logger.warning(
                    "Не удалось отправить команду %s для %s. Попытка #%s/%s.",
                    self.command.name,
                    machine_name,
                    send_attempts,
                    self.max_command_send_attempts,
                )

                if send_attempts >= self.max_command_send_attempts:
                    message = "Достигнут лимит попыток отправки команды"
                    logger.error(
                        "%s. Аппарат %s, шаг send_command, попытка #%s.",
                        message,
                        machine_name,
                        send_attempts,
                    )
                    return CommandResult(
                        success=False,
                        step="send_command",
                        message=message,
                        attempts=send_attempts,
                    )

                await asyncio.sleep(self.retry_send_command_timeout_seconds)
                continue

            except KitAPIError as exc:
                send_attempts += 1
                message = f"Неожиданная ошибка Kit API: {exc}"
                logger.error(
                    "%s. Аппарат %s, шаг send_command, попытка #%s.",
                    message,
                    machine_name,
                    send_attempts,
                )
                return CommandResult(
                    success=False,
                    step="send_command",
                    message=message,
                    attempts=send_attempts,
                )

            send_attempts = 0
            logger.info(
                "Команда %s отправлена для %s. Ожидание %s сек.",
                self.command.name,
                machine_name,
                self.wait_timeout_seconds,
            )
            await asyncio.sleep(self.wait_timeout_seconds)

            verify_result = await self._verify_status(machine_kit_id, machine_name, cycle_attempt + 1)
            if verify_result.success:
                return verify_result

            cycle_attempt += 1
            logger.warning(
                "Статус не совпал для %s. Цикл #%s/%s.",
                machine_name,
                cycle_attempt,
                self.max_retry_attempts,
            )

        message = "Достигнут лимит циклов ожидания/проверки статуса"
        return CommandResult(
            success=False,
            step="verify_status",
            message=message,
            attempts=self.max_retry_attempts,
        )

    async def _verify_status(
        self,
        machine_kit_id: int,
        machine_name: str,
        attempt: int,
    ) -> CommandResult:
        try:
            states: VendingMachinesStatesCollection = (
                await self.kit_api_client.get_vending_machine_states()
            )
            states_map: dict[int, VendingMachineStateModel] = {
                state.id: state for state in states.get_all()
            }
            machine_state = states_map.get(machine_kit_id)

            if machine_state is None:
                message = "Состояние аппарата не найдено в ответе API"
                logger.error(
                    "%s. Аппарат %s, шаг verify_status, попытка #%s.",
                    message,
                    machine_name,
                    attempt,
                )
                return CommandResult(
                    success=False,
                    step="verify_status",
                    message=message,
                    attempts=attempt,
                )

            if self.status_predicate(machine_state.statuses):
                return CommandResult(
                    success=True,
                    step="verify_status",
                    message="Статус подтверждён",
                    attempts=attempt,
                )

            return CommandResult(
                success=False,
                step="verify_status",
                message="Статус не соответствует ожидаемому",
                attempts=attempt,
            )

        except KitAPIError as exc:
            message = f"Ошибка API при проверке статуса: {exc}"
            logger.error(
                "%s. Аппарат %s, шаг verify_status, попытка #%s.",
                message,
                machine_name,
                attempt,
            )
            return CommandResult(
                success=False,
                step="verify_status",
                message=message,
                attempts=attempt,
            )
```

- [ ] **Шаг 5: Запустить happy path — PASS**

- [ ] **Шаг 6: Добавить тест timeout (статус не совпал)**

```python
def test_workflow_fails_after_max_retry_when_status_never_matches() -> None:
    client = AsyncMock()
    client.send_command_to_vending_machine = AsyncMock(return_value=0)
    client.get_vending_machine_states = AsyncMock(
        return_value=VendingMachinesStatesCollection.model_validate(
            {"VendingMachines": [{"VendingMachineId": 10, "Statuses": "1"}]}
        )
    )

    workflow = MatrixCommandWorkflow(
        kit_api_client=client,
        command=VendingMachineCommand.LOAD_MATRIX,
        status_predicate=lambda statuses: VendingMachineStatus.MATRIX_LOADED in statuses,
        wait_timeout_seconds=0,
        max_retry_attempts=2,
        max_command_send_attempts=3,
        retry_send_command_timeout_seconds=0,
    )

    result = asyncio.run(workflow.run(machine_kit_id=10, machine_name="[10] Кофе"))

    assert result.success is False
    assert result.step == "verify_status"
    assert client.send_command_to_vending_machine.await_count == 2
```

- [ ] **Шаг 7: Запустить — PASS**

- [ ] **Шаг 8: Добавить тест retry send на network error**

```python
def test_workflow_retries_send_on_network_error() -> None:
    client = AsyncMock()
    client.send_command_to_vending_machine = AsyncMock(
        side_effect=[
            __import__(
                "src.infrastructure.kit_vending.api.exceptions",
                fromlist=["KitAPINetworkError"],
            ).KitAPINetworkError("timeout"),
            0,
        ]
    )
    client.get_vending_machine_states = AsyncMock(
        return_value=VendingMachinesStatesCollection.model_validate(
            {"VendingMachines": [{"VendingMachineId": 10, "Statuses": "21"}]}
        )
    )

    workflow = MatrixCommandWorkflow(
        kit_api_client=client,
        command=VendingMachineCommand.LOAD_MATRIX,
        status_predicate=lambda statuses: VendingMachineStatus.MATRIX_LOADED in statuses,
        wait_timeout_seconds=0,
        max_retry_attempts=1,
        max_command_send_attempts=3,
        retry_send_command_timeout_seconds=0,
    )

    result = asyncio.run(workflow.run(machine_kit_id=10, machine_name="[10] Кофе"))

    assert result.success is True
    assert client.send_command_to_vending_machine.await_count == 2
```

- [ ] **Шаг 9: Добавить тест без retry на обычный KitAPIResponseError**

```python
def test_workflow_does_not_retry_on_non_rate_limit_response_error() -> None:
    from src.infrastructure.kit_vending.api.exceptions import KitAPIResponseError

    client = AsyncMock()
    client.send_command_to_vending_machine = AsyncMock(
        side_effect=KitAPIResponseError("bad request", result_code=5)
    )

    workflow = MatrixCommandWorkflow(
        kit_api_client=client,
        command=VendingMachineCommand.APPLY_MATRIX,
        status_predicate=lambda statuses: VendingMachineStatus.MATRIX_LOADED not in statuses,
        wait_timeout_seconds=0,
        max_retry_attempts=3,
        max_command_send_attempts=3,
        retry_send_command_timeout_seconds=0,
    )

    result = asyncio.run(workflow.run(machine_kit_id=10, machine_name="[10] Кофе"))

    assert result.success is False
    assert result.step == "send_command"
    assert client.send_command_to_vending_machine.await_count == 1
```

- [ ] **Шаг 10: Запустить все workflow-тесты**

Запуск: `uv run pytest tests/infrastructure/kit_vending/test_matrix_command_workflow.py -q`
Ожидается: 4 passed

---

### Задача 8: Перенос адаптеров и подключение workflow

**Файлы:**
- Создать: `src/infrastructure/kit_vending/adapters/__init__.py`
- Создать: `src/infrastructure/kit_vending/adapters/upload_matrix.py`
- Создать: `src/infrastructure/kit_vending/adapters/bind_matrix_to_machine.py`
- Создать: `src/infrastructure/kit_vending/adapters/download_matrix_to_vending_machine.py`
- Создать: `src/infrastructure/kit_vending/adapters/apply_matrix_to_vending_machine.py`
- Удалить: `src/infrastructure/adapters/kit_vending/` (после переноса)

- [ ] **Шаг 1: Создать `upload_matrix.py` и `bind_matrix_to_machine.py`**

Скопировать логику из текущих адаптеров, заменить импорты:

```python
from src.infrastructure.kit_vending.api.client import KitVendingAPIClient
from src.infrastructure.kit_vending.api.exceptions import KitAPIError, KitAPIResponseError
```

Поведение и сигнатуры портов — без изменений.

- [ ] **Шаг 2: Создать `download_matrix_to_vending_machine.py`**

```python
from __future__ import annotations

import logging
from dataclasses import dataclass

from beartype import beartype

from src.infrastructure.kit_vending.api.client import KitVendingAPIClient
from src.infrastructure.kit_vending.api.enums import VendingMachineCommand, VendingMachineStatus
from src.infrastructure.kit_vending.matrix_command_workflow import MatrixCommandWorkflow
from src.domain.entites.vending_machine import VendingMachine
from src.domain.ports.download_matrix_to_vending_machine import DownloadMatrixToVendingMachinePort

logger = logging.getLogger(__name__)


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class DownloadMatrixToVendingMachineAdapter(DownloadMatrixToVendingMachinePort):
    kit_api_client: KitVendingAPIClient
    matrix_load_timeout: int = 120
    max_retry_attempts: int = 3
    retry_send_command_timeout: int = 10

    async def execute(self, vending_machine: VendingMachine) -> bool:
        workflow = MatrixCommandWorkflow(
            kit_api_client=self.kit_api_client,
            command=VendingMachineCommand.LOAD_MATRIX,
            status_predicate=lambda statuses: VendingMachineStatus.MATRIX_LOADED in statuses,
            wait_timeout_seconds=self.matrix_load_timeout,
            max_retry_attempts=self.max_retry_attempts,
            max_command_send_attempts=3,
            retry_send_command_timeout_seconds=self.retry_send_command_timeout,
        )
        result = await workflow.run(
            machine_kit_id=vending_machine.kit_id.value,
            machine_name=vending_machine.name,
        )
        if not result.success:
            logger.error(
                "Загрузка матрицы не удалась для %s: шаг=%s, попытка=%s, %s",
                vending_machine.name,
                result.step,
                result.attempts,
                result.message,
            )
        return result.success
```

- [ ] **Шаг 3: Создать `apply_matrix_to_vending_machine.py`**

Аналогично download, но:
- `command=VendingMachineCommand.APPLY_MATRIX`
- `status_predicate=lambda statuses: VendingMachineStatus.MATRIX_LOADED not in statuses`
- поле `matrix_apply_timeout` вместо `matrix_load_timeout`

- [ ] **Шаг 4: Убедиться что нет импортов `kit_api` в новых адаптерах**

Запуск: `rg "kit_api" src/infrastructure/kit_vending`
Ожидается: нет совпадений

---

### Задача 9: Обновить wiring (`main.py`, use case sync)

**Файлы:**
- Изменить: `main.py`
- Изменить: `src/application/use_cases/sync/sync_vending_machines_cache.py`
- Изменить: `src/application/use_cases/upload_machine_matrix.py`

- [ ] **Шаг 1: Обновить `main.py`**

Заменить импорты:

```python
from src.infrastructure.kit_vending.api.account import KitAPIAccount
from src.infrastructure.kit_vending.api.client import KitVendingAPIClient
from src.infrastructure.kit_vending.api.config import KitAPIConfig
from src.infrastructure.kit_vending.adapters.apply_matrix_to_vending_machine import ApplyMatrixToVendingMachineAdapter
from src.infrastructure.kit_vending.adapters.bind_matrix_to_machine import BindMatrixToVendingMachineAdapter
from src.infrastructure.kit_vending.adapters.download_matrix_to_vending_machine import DownloadMatrixToVendingMachineAdapter
from src.infrastructure.kit_vending.adapters.upload_matrix import UploadMatrixAdapter
```

Убрать чтение env вручную; использовать:

```python
kit_config = KitAPIConfig.from_env()
account = KitAPIAccount(
    login=kit_config.login,
    password=kit_config.password,
    company_id=kit_config.company_id,
)
async with KitVendingAPIClient(account=account, config=kit_config) as kit_api_client:
    ...
```

- [ ] **Шаг 2: Обновить `sync_vending_machines_cache.py`**

```python
from src.infrastructure.kit_vending.api.client import KitVendingAPIClient
from src.infrastructure.kit_vending.api.models.vending_machines import (
    ActiveVendingMachineModel,
    VendingMachinesCollection,
)
```

- [ ] **Шаг 3: Улучшить `upload_machine_matrix.py` — сводка по аппаратам**

Добавить счётчики и итоговый лог:

```python
success_count = 0
failure_count = 0

for machine in machines:
    ...
    if not is_success:
        failure_count += 1
        logger.critical(
            f"Не удалось привязать матрицу. "
            f"Матрица: {matrix.name}, аппарат: {machine.name}."
        )
        continue
    ...
    # аналогично для download/apply

if failure_count == 0:
    logger.info(
        f"Матрица '{matrix.name}': все {success_count} аппаратов обработаны успешно."
    )
elif success_count == 0:
    logger.critical(
        f"Матрица '{matrix.name}': полный провал — 0 из {len(machines)} аппаратов."
    )
else:
    logger.warning(
        f"Матрица '{matrix.name}': частичный успех — "
        f"{success_count} из {len(machines)} аппаратов, ошибок: {failure_count}."
    )
```

Увеличивать `success_count` только когда все 3 шага (bind, download, apply) для аппарата прошли успешно.

- [ ] **Шаг 4: Удалить старую папку адаптеров**

Удалить `src/infrastructure/adapters/kit_vending/` целиком.

- [ ] **Шаг 5: Проверить отсутствие `kit_api` в `src/` и `main.py`**

Запуск: `rg "kit_api" src main.py`
Ожидается: нет совпадений (до задачи 12 в `pyproject.toml` зависимость ещё может быть)

---

### Задача 10: Тесты адаптеров (TDD)

**Файлы:**
- Создать: `tests/infrastructure/kit_vending/test_adapters.py`

- [ ] **Шаг 1: Написать падающие тесты**

```python
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from src.domain.entites.cell import Cell
from src.domain.entites.matrix import Matrix
from src.domain.entites.product import Product
from src.domain.entites.vending_machine import VendingMachine
from src.domain.value_objects.ids.matrix_kit_id import MatrixKitId
from src.domain.value_objects.ids.product_id import ProductId
from src.domain.value_objects.ids.vending_machine_id import VMId
from src.domain.value_objects.ids.vending_machine_kit_id import VMKitId
from src.domain.value_objects.money import Money
from src.infrastructure.kit_vending.adapters.bind_matrix_to_machine import BindMatrixToVendingMachineAdapter
from src.infrastructure.kit_vending.adapters.upload_matrix import UploadMatrixAdapter


def _sample_matrix() -> Matrix:
    product = Product(id=ProductId(1), name="Эспрессо")
    cell = Cell(line_number=1, price=Money.from_ruble(50), product=product)
    return Matrix(name="Тест", cells=[cell], vending_machines_ids=[VMId(7)])


def _sample_machine() -> VendingMachine:
    return VendingMachine(id=VMId(7), kit_id=VMKitId(100), name="[7] Кофе")


def test_upload_matrix_adapter_returns_matrix_kit_id() -> None:
    client = AsyncMock()
    client.create_matrix = AsyncMock(return_value=555)

    adapter = UploadMatrixAdapter(kit_api_client=client)
    result = asyncio.run(
        adapter.execute(_sample_matrix(), datetime(2026, 6, 10, tzinfo=timezone.utc))
    )

    assert result == MatrixKitId(555)
    client.create_matrix.assert_awaited_once()


def test_bind_matrix_adapter_returns_true_on_success() -> None:
    client = AsyncMock()
    client.bound_matrix_to_vending_machine = AsyncMock(return_value=0)

    adapter = BindMatrixToVendingMachineAdapter(kit_api_client=client)
    result = asyncio.run(adapter.execute(_sample_machine(), MatrixKitId(555)))

    assert result is True
    client.bound_matrix_to_vending_machine.assert_awaited_once_with(
        machine_id=100,
        matrix_id=555,
    )
```

- [ ] **Шаг 2: Запустить — FAIL если адаптеры не готовы, иначе PASS**

Запуск: `uv run pytest tests/infrastructure/kit_vending/test_adapters.py -q`
Ожидается: 2 passed

- [ ] **Шаг 3: Добавить тест download через workflow (fake client)**

```python
from src.infrastructure.kit_vending.adapters.download_matrix_to_vending_machine import (
    DownloadMatrixToVendingMachineAdapter,
)
from src.infrastructure.kit_vending.api.enums import VendingMachineStatus
from src.infrastructure.kit_vending.api.models.vending_machine_state import (
    VendingMachinesStatesCollection,
)


def test_download_adapter_returns_true_when_matrix_loaded() -> None:
    client = AsyncMock()
    client.send_command_to_vending_machine = AsyncMock(return_value=0)
    client.get_vending_machine_states = AsyncMock(
        return_value=VendingMachinesStatesCollection.model_validate(
            {"VendingMachines": [{"VendingMachineId": 100, "Statuses": "21"}]}
        )
    )

    adapter = DownloadMatrixToVendingMachineAdapter(
        kit_api_client=client,
        matrix_load_timeout=0,
    )
    result = asyncio.run(adapter.execute(_sample_machine()))

    assert result is True
```

- [ ] **Шаг 4: Запустить все adapter-тесты**

Запуск: `uv run pytest tests/infrastructure/kit_vending/test_adapters.py -q`
Ожидается: 3 passed

---

### Задача 11: Удалить зависимость `kit-api`

**Файлы:**
- Изменить: `pyproject.toml`

- [ ] **Шаг 1: Удалить строку `kit-api @ git+...` из dependencies**

Финальный блок `dependencies` — без `kit-api` (как в задаче 1).

- [ ] **Шаг 2: Пересобрать окружение**

Запуск: `uv sync --group dev`
Ожидается: exit 0, пакет `kit_api` отсутствует в `.venv`

- [ ] **Шаг 3: Проверить импорты**

Запуск: `rg "kit_api" . --glob "!*.md" --glob "!.venv/**"`
Ожидается: нет совпадений в `src/`, `main.py`, `tests/`

---

### Задача 12: Финальная верификация

- [ ] **Шаг 1: Полный прогон юнит-тестов**

Запуск: `uv run pytest -q`
Ожидается: все тесты PASS, 0 failed

- [ ] **Шаг 2: Smoke-import приложения**

Запуск: `uv run python -c "import main; print('ok')"`
Ожидается: `ok` (без запуска `main()`)

- [ ] **Шаг 3: Проверка критериев готовности из спека**

| Критерий | Команда / действие |
|----------|-------------------|
| `kit-api` удалён, `uv sync` проходит | задача 11 |
| 5 API-методов в локальном клиенте | `rg "async def (get_vending_machines|get_vending_machine_states|create_matrix|bound_matrix_to_vending_machine|send_command_to_vending_machine)" src/infrastructure/kit_vending/api/client.py` |
| Логи содержат шаг и попытку | тесты workflow + ручная проверка сообщений в `MatrixCommandWorkflow` и адаптерах |
| Нет `from kit_api` | `rg "kit_api" src main.py tests` |

---

## Само-ревью плана

### Покрытие спека

| Требование спека | Задача |
|------------------|--------|
| Inlining 5 методов API | 5–6 |
| Модели + utils | 3–4 |
| Enum'ы, исключения | 2 |
| Rate limiter, timestamp, config | 5–6 |
| MatrixCommandWorkflow + CommandResult | 7 |
| Адаптеры тонкие, `-> bool` | 8 |
| Перенос адаптеров в `kit_vending/adapters/` | 8–9 |
| `main.py` + sync imports | 9 |
| Сводка в UploadAndApplyMatrixUseCase | 9 |
| Удаление `kit-api` | 11 |
| Тесты client, models, workflow, adapters | 3–4, 6–7, 10 |
| Retry-политика | 6–7 |

Пробелов нет.

### Плейсхолдеры

Задачи 4 и 5 содержат «перенести из kit_api» — исполнитель копирует код из `.venv/Lib/site-packages/kit_api/` с заменой импортов; это допустимо, т.к. исходник фиксирован и доступен локально.

### Согласованность имён

- `KitAPIConfig.from_env()` → `KitVendingAPIClient(account=..., config=...)`
- `MatrixCommandWorkflow.run(machine_kit_id, machine_name)` → адаптеры
- `CommandResult.step` / `attempts` → логи адаптеров

---
