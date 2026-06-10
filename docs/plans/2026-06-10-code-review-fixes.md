# План реализации: исправления по код-ревью global rewrite

> **Для агентов:** Используй скилл executing-plans для реализации этого плана задача за задачей. Шаги используют синтаксис чекбоксов (`- [ ]`) для отслеживания.

**Цель:** Закрыть замечания код-ревью от 2026-06-10: корректный статус JobRun при пропуске матриц, единый конфиг, валидация Google credentials, исправление слоёв CLI, покрытие error-path тестами, валидация данных Sheets.

**Архитектура:** Изменения в основном в `application` (учёт skipped-матриц, финализация JobRun) и `bootstrap` (wiring selection, Google credentials). Domain-исключения без изменений. Infrastructure — только адаптер products и удаление `KitAPIConfig.from_env()`.

**Ключевые файлы / стек:** Python 3.12, uv, pytest (sync), pydantic-settings, gspread, beartype.

**Основание:** код-ревью global rewrite (не отдельный спек; согласовано со `docs/specs/2026-06-10-global-rewrite-design.md` § JobRun / Deploy / Settings).

---

## Карта файлов

| Файл | Действие | Ответственность |
|------|----------|-----------------|
| `src/application/use_cases/deploy/deploy_matrices.py` | Изменить | Возврат `(success, failed, skipped)` |
| `src/application/use_cases/orchestration/run_deployment_job.py` | Изменить | Статус JobRun с учётом `skipped` |
| `tests/application/test_deploy_matrices.py` | Изменить + добавить тесты | TDD skipped-матриц |
| `tests/application/test_run_deployment_job.py` | Добавить тесты | sync fail, partial, skipped |
| `tests/application/conftest.py` | Изменить | `FakeDeployMatrices` → 3-tuple |
| `src/infrastructure/kit_vending/api/config.py` | Изменить | Удалить `from_env()` |
| `src/bootstrap/settings.py` | Изменить | `google_application_credentials` |
| `src/bootstrap/container.py` | Изменить | credentials + selection wiring |
| `.env.example` | Изменить | Комментарий про обязательность credentials |
| `src/interfaces/cli/run_interactive.py` | Изменить | Только `Container`, без infrastructure |
| `src/interfaces/cli/run_scheduled.py` | Изменить | Только `Container`, без infrastructure |
| `src/infrastructure/google_sheets/adapters/get_products.py` | Изменить | Валидация name/price |
| `tests/infrastructure/google_sheets/test_get_products_adapter.py` | Создать | TDD валидации products |
| `src/application/use_cases/sync/sync_products_cache.py` | Изменить | `SynchronizationError` при пустом списке |
| `tests/application/test_sync_all_caches.py` | Добавить тест | Пустые products → ошибка |
| `main.py` | Изменить | `import logging` наверх, типы |
| `src/interfaces/cli/run_interactive.py` | Изменить | Аннотация `Container` |

---

### Задача 1: DeployMatricesUseCase — учёт пропущенных матриц

**Файлы:**
- Изменить: `src/application/use_cases/deploy/deploy_matrices.py`
- Изменить: `tests/application/test_deploy_matrices.py`

- [ ] **Шаг 1: Написать падающий тест**

В `tests/application/test_deploy_matrices.py` добавить:

```python
def test_deploy_matrices_counts_skipped_when_matrix_not_found():
    matrix_repo = InMemoryMatrixRepository()
    matrix_repo.add(make_matrix("M1"))
    vm_repo = InMemoryVendingMachineRepository()
    vm_repo.add(make_machine())

    uc = DeployMatricesUseCase(
        matrix_repository=matrix_repo,
        vending_machine_repository=vm_repo,
        upload_and_apply_matrix_uc=FakeUploadAndApply([(1, 0)]),
    )

    success, failed, skipped = asyncio.run(
        uc.execute(["M1", "MISSING"], datetime(2026, 6, 10))
    )
    assert success == 1
    assert failed == 0
    assert skipped == 1
```

- [ ] **Шаг 2: Запустить тест и убедиться что он падает**

Запуск: `uv run pytest tests/application/test_deploy_matrices.py::test_deploy_matrices_counts_skipped_when_matrix_not_found -q`

Ожидается: FAIL (`ValueError: not enough values to unpack` или `assert skipped == 1`)

- [ ] **Шаг 3: Обновить существующий тест и реализовать логику**

В `tests/application/test_deploy_matrices.py` изменить существующий тест:

```python
    success, failed, skipped = asyncio.run(
        uc.execute(["M1", "M2"], datetime(2026, 6, 10))
    )
    assert success == 1
    assert failed == 1
    assert skipped == 0
```

В `src/application/use_cases/deploy/deploy_matrices.py`:

```python
    async def execute(
        self, selected_matrix_names: list[str], timestamp: datetime
    ) -> tuple[int, int, int]:
        if not selected_matrix_names:
            raise UploadMatrixError("Не выбрано ни одной матрицы для загрузки")

        tasks = []
        names: list[str] = []
        skipped = 0

        for name in selected_matrix_names:
            matrix = self.matrix_repository.get_by_name(name)
            if matrix is None:
                logger.error("Матрица с именем '%s' не найдена", name)
                skipped += 1
                continue

            machines = self._get_vending_machines(matrix.vending_machines_ids)
            if not machines:
                logger.warning("Не найдено ни одной машины для матрицы '%s'", name)
                skipped += 1
                continue

            tasks.append(self.upload_and_apply_matrix_uc.execute(matrix, machines, timestamp))
            names.append(name)

        if not tasks:
            raise UploadMatrixError("Не удалось создать ни одной задачи для загрузки матриц")

        results = await asyncio.gather(*tasks, return_exceptions=True)

        matrices_success = 0
        matrices_failed = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                matrices_failed += 1
                logger.error("Ошибка при загрузке матрицы '%s': %s", names[i], result)
                continue

            success_count, failure_count = result
            if failure_count == 0:
                matrices_success += 1
            elif success_count == 0:
                matrices_failed += 1
            else:
                matrices_success += 1

        return matrices_success, matrices_failed, skipped
```

- [ ] **Шаг 4: Запустить тесты deploy и убедиться что проходят**

Запуск: `uv run pytest tests/application/test_deploy_matrices.py -q`

Ожидается: PASS

- [ ] **Шаг 5: Убедиться что все юнит-тесты проходят**

Запуск: `uv run pytest -q`

Ожидается: FAIL (сломан `run_deployment_job` — распаковка 2 значений). Это нормально до Задачи 2.

---

### Задача 2: RunDeploymentJobUseCase — статус JobRun с учётом skipped

**Файлы:**
- Изменить: `src/application/use_cases/orchestration/run_deployment_job.py`
- Изменить: `tests/application/conftest.py`
- Изменить: `tests/application/test_run_deployment_job.py`

- [ ] **Шаг 1: Написать падающий тест**

В `tests/application/test_run_deployment_job.py` добавить:

```python
def test_run_deployment_job_partial_when_matrices_skipped():
    job_repo = InMemoryJobRunRepository()
    matrix_repo = InMemoryMatrixRepository()
    matrix_repo.add(make_matrix("M1"))
    product_repo = InMemoryProductRepository()
    vm_repo = InMemoryVendingMachineRepository()

    sync_all = SyncAllCachesUseCase(
        sync_products=SyncProductsCache(get_products=FakeProductsPort(), product_repository=product_repo),
        sync_vending_machines=SyncVendingMachinesCache(
            get_vending_machines=FakeVendingMachinesPort(), vending_machine_repository=vm_repo
        ),
        sync_matrices=SyncMatricesCache(get_all_matrices=FakeMatricesPort(), matrix_repository=matrix_repo),
    )

    deploy = FakeDeployMatrices(
        return_value=(1, 0, 1),
        matrix_repository=matrix_repo,
        vending_machine_repository=vm_repo,
        upload_and_apply_matrix_uc=FakeUploadAndApply([(1, 0)]),
    )

    uc = RunDeploymentJobUseCase(
        job_run_repository=job_repo,
        sync_all_caches=sync_all,
        matrix_selection=FakeSelection(),
        matrix_repository=matrix_repo,
        deploy_matrices=deploy,
    )

    job_run = asyncio.run(uc.execute(trigger="scheduled"))

    assert job_run.status == "partial"
    assert job_run.matrices_total == 1
    assert job_run.matrices_success == 1
    assert job_run.matrices_failed == 0
    assert job_run.error_summary is not None
    assert "Пропущено" in job_run.error_summary
```

- [ ] **Шаг 2: Запустить тест и убедиться что он падает**

Запуск: `uv run pytest tests/application/test_run_deployment_job.py::test_run_deployment_job_partial_when_matrices_skipped -q`

Ожидается: FAIL

- [ ] **Шаг 3: Обновить conftest и реализовать финализацию**

В `tests/application/conftest.py` изменить `FakeDeployMatrices`:

```python
class FakeDeployMatrices(DeployMatricesUseCase):
    def __init__(
        self,
        return_value: tuple[int, int, int],
        matrix_repository,
        vending_machine_repository,
        upload_and_apply_matrix_uc,
    ) -> None:
        super().__init__(
            matrix_repository=matrix_repository,
            vending_machine_repository=vending_machine_repository,
            upload_and_apply_matrix_uc=upload_and_apply_matrix_uc,
        )
        object.__setattr__(self, "_return_value", return_value)

    async def execute(self, selected_matrix_names: list[str], timestamp: datetime) -> tuple[int, int, int]:
        return self._return_value
```

В существующем `test_run_deployment_job_creates_and_finalizes_job_run` заменить `return_value=(2, 0)` на `return_value=(2, 0, 0)`.

В `src/application/use_cases/orchestration/run_deployment_job.py` заменить блок после deploy:

```python
        try:
            success, failed, skipped = await self.deploy_matrices.execute(
                selected_names, datetime.now(tz=PROJECT_TIMEZONE)
            )
        except Exception as exc:
            return self._finalize(
                job_run,
                status="failed",
                matrices_total=len(selected_names),
                matrices_success=0,
                matrices_failed=len(selected_names),
                error_summary=str(exc),
            )

        total = len(selected_names)
        if failed == 0 and skipped == 0:
            status = "completed"
        elif success == 0:
            status = "failed"
        else:
            status = "partial"

        summary_parts: list[str] = []
        if failed:
            summary_parts.append(f"Ошибок: {failed} из {total}")
        if skipped:
            summary_parts.append(f"Пропущено: {skipped} из {total}")
        error_summary = "; ".join(summary_parts) if summary_parts else None

        return self._finalize(
            job_run,
            status=status,
            matrices_total=total,
            matrices_success=success,
            matrices_failed=failed,
            error_summary=error_summary,
        )
```

- [ ] **Шаг 4: Запустить тесты orchestration**

Запуск: `uv run pytest tests/application/test_run_deployment_job.py -q`

Ожидается: PASS

- [ ] **Шаг 5: Полный прогон**

Запуск: `uv run pytest -q`

Ожидается: PASS (все тесты)

---

### Задача 3: Тесты error-path RunDeploymentJob

**Файлы:**
- Изменить: `tests/application/test_run_deployment_job.py`
- Изменить: `tests/application/conftest.py`

- [ ] **Шаг 1: Добавить FakeSyncAllRaises в conftest**

В `tests/application/conftest.py`:

```python
class FakeSyncAllRaises(SyncAllCachesUseCase):
    def __init__(self) -> None:
        pass

    async def execute(self) -> None:
        raise SynchronizationError("sync failed")
```

(Добавить импорт `SynchronizationError` и `SyncAllCachesUseCase`.)

- [ ] **Шаг 2: Написать тест sync failure**

В `tests/application/test_run_deployment_job.py`:

```python
def test_run_deployment_job_failed_when_sync_raises():
    job_repo = InMemoryJobRunRepository()
    matrix_repo = InMemoryMatrixRepository()

    uc = RunDeploymentJobUseCase(
        job_run_repository=job_repo,
        sync_all_caches=FakeSyncAllRaises(),
        matrix_selection=FakeSelection(),
        matrix_repository=matrix_repo,
        deploy_matrices=FakeDeployMatrices(
            return_value=(0, 0, 0),
            matrix_repository=matrix_repo,
            vending_machine_repository=InMemoryVendingMachineRepository(),
            upload_and_apply_matrix_uc=FakeUploadAndApply([]),
        ),
    )

    job_run = asyncio.run(uc.execute(trigger="scheduled"))

    assert job_run.status == "failed"
    assert "sync failed" in (job_run.error_summary or "")
```

- [ ] **Шаг 3: Написать тест all deploy failed**

```python
def test_run_deployment_job_failed_when_all_matrices_fail():
    job_repo = InMemoryJobRunRepository()
    matrix_repo = InMemoryMatrixRepository()
    matrix_repo.add(make_matrix())
    product_repo = InMemoryProductRepository()
    vm_repo = InMemoryVendingMachineRepository()

    sync_all = SyncAllCachesUseCase(
        sync_products=SyncProductsCache(get_products=FakeProductsPort(), product_repository=product_repo),
        sync_vending_machines=SyncVendingMachinesCache(
            get_vending_machines=FakeVendingMachinesPort(), vending_machine_repository=vm_repo
        ),
        sync_matrices=SyncMatricesCache(get_all_matrices=FakeMatricesPort(), matrix_repository=matrix_repo),
    )

    deploy = FakeDeployMatrices(
        return_value=(0, 2, 0),
        matrix_repository=matrix_repo,
        vending_machine_repository=vm_repo,
        upload_and_apply_matrix_uc=FakeUploadAndApply([]),
    )

    uc = RunDeploymentJobUseCase(
        job_run_repository=job_repo,
        sync_all_caches=sync_all,
        matrix_selection=FakeSelection(),
        matrix_repository=matrix_repo,
        deploy_matrices=deploy,
    )

    job_run = asyncio.run(uc.execute(trigger="scheduled"))

    assert job_run.status == "failed"
    assert job_run.matrices_success == 0
    assert job_run.matrices_failed == 2
```

- [ ] **Шаг 4: Запустить тесты**

Запуск: `uv run pytest tests/application/test_run_deployment_job.py -q`

Ожидается: PASS

---

### Задача 4: Удалить дублирующий KitAPIConfig.from_env()

**Файлы:**
- Изменить: `src/infrastructure/kit_vending/api/config.py`

- [ ] **Шаг 1: Удалить метод и импорт os**

В `src/infrastructure/kit_vending/api/config.py` оставить только dataclass:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class KitAPIConfig:
    company_id: int
    login: str
    password: str
    request_per_window: int = 1
    window_seconds: int = 10
    backoff_seconds: float = 60.0
```

Удалить `import os`, `KitAPIValidationError` (если больше не используется в этом файле), метод `from_env`.

- [ ] **Шаг 2: Проверить что from_env нигде не вызывается**

Запуск: `rg "from_env" src tests`

Ожидается: 0 совпадений в `src/` и `tests/`

- [ ] **Шаг 3: Прогон тестов**

Запуск: `uv run pytest -q`

Ожидается: PASS

---

### Задача 5: Google credentials в Settings

**Файлы:**
- Изменить: `src/bootstrap/settings.py`
- Изменить: `src/bootstrap/container.py`
- Изменить: `.env.example`

- [ ] **Шаг 1: Добавить поле в Settings**

В `src/bootstrap/settings.py`:

```python
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

from src.infrastructure.kit_vending.api.config import KitAPIConfig


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    google_sheets_matrix_table_id: str
    google_application_credentials: str | None = None

    kit_api_company_id: int
    # ... остальные поля без изменений
```

- [ ] **Шаг 2: Использовать credentials в Container**

В `src/bootstrap/container.py` заменить создание spreadsheet:

```python
        if self._settings.google_application_credentials:
            sa = gspread.service_account(filename=self._settings.google_application_credentials)
        else:
            sa = gspread.service_account()
        spreadsheet = sa.open_by_key(self._settings.google_sheets_matrix_table_id)
```

- [ ] **Шаг 3: Обновить .env.example**

Строку 7 изменить на:

```
# Рекомендуется указать явно; иначе gspread ищет service_account.json в CWD
GOOGLE_APPLICATION_CREDENTIALS=
```

- [ ] **Шаг 4: Прогон тестов**

Запуск: `uv run pytest -q`

Ожидается: PASS

---

### Задача 6: Selection wiring — убрать зависимость interfaces → infrastructure

**Файлы:**
- Изменить: `src/bootstrap/container.py`
- Изменить: `src/interfaces/cli/run_interactive.py`
- Изменить: `src/interfaces/cli/run_scheduled.py`

- [ ] **Шаг 1: Добавить методы в Container**

В `src/bootstrap/container.py` добавить импорты и методы:

```python
from src.infrastructure.selection.configured_selection import ConfiguredMatrixSelection
from src.infrastructure.selection.interactive_selection import InteractiveMatrixSelection
from src.infrastructure.selection.interactive_selector import InteractiveSelector

    def configure_interactive_selection(self) -> None:
        self.set_matrix_selection(
            InteractiveMatrixSelection(interactive_selector=InteractiveSelector())
        )

    def configure_scheduled_selection(self, names: str) -> None:
        self.set_matrix_selection(ConfiguredMatrixSelection(names=names))
```

- [ ] **Шаг 2: Упростить CLI entry points**

`src/interfaces/cli/run_interactive.py`:

```python
from __future__ import annotations

from src.bootstrap.container import Container


async def run_interactive(container: Container) -> int:
    container.configure_interactive_selection()
    job = await container.run_deployment(trigger="interactive")
    return 0 if job.status in ("completed", "partial") else 1
```

`src/interfaces/cli/run_scheduled.py`:

```python
from __future__ import annotations

from src.bootstrap.container import Container


async def run_scheduled(container: Container, scheduled_matrix_names: str) -> int:
    container.configure_scheduled_selection(scheduled_matrix_names)
    job = await container.run_deployment(trigger="scheduled")
    return 0 if job.status in ("completed", "partial") else 1
```

- [ ] **Шаг 3: Проверить отсутствие infrastructure-импортов в interfaces**

Запуск: `rg "src\.infrastructure" src/interfaces`

Ожидается: 0 совпадений

- [ ] **Шаг 4: Прогон тестов**

Запуск: `uv run pytest -q`

Ожидается: PASS

---

### Задача 7: GetAllProductsAdapter — валидация name и price

**Файлы:**
- Создать: `tests/infrastructure/google_sheets/test_get_products_adapter.py`
- Изменить: `src/infrastructure/google_sheets/adapters/get_products.py`

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/infrastructure/google_sheets/test_get_products_adapter.py`:

```python
from __future__ import annotations

import pytest

from src.domain.exceptions import SynchronizationError
from src.infrastructure.google_sheets.adapters.get_products import GetAllProductsAdapter
from src.infrastructure.google_sheets.client import GoogleSheetsAPIClient, ProductModel


class FakeSheetsClient:
    def __init__(self, products: list[ProductModel]) -> None:
        self._products = products

    def get_all_products(self) -> list[ProductModel]:
        return self._products


def test_get_products_raises_when_price_missing():
    client = FakeSheetsClient(
        [ProductModel(id=1, name="Cola", price=None)]
    )
    adapter = GetAllProductsAdapter(google_table_api_client=client)  # type: ignore[arg-type]

    with pytest.raises(SynchronizationError, match="не указана закупочная цена"):
        adapter.execute()
```

- [ ] **Шаг 2: Запустить тест и убедиться что он падает**

Запуск: `uv run pytest tests/infrastructure/google_sheets/test_get_products_adapter.py::test_get_products_raises_when_price_missing -q`

Ожидается: FAIL (нет SynchronizationError)

- [ ] **Шаг 3: Реализовать валидацию**

В `src/infrastructure/google_sheets/adapters/get_products.py` в цикле перед созданием `Product`:

```python
            if product_model.name is None:
                raise SynchronizationError(
                    f"Товар id={product_model.id}: не указано имя."
                )
            if product_model.price is None:
                raise SynchronizationError(
                    f"Товар '{product_model.name}': не указана закупочная цена."
                )
```

- [ ] **Шаг 4: Добавить тест на missing name и прогнать файл**

```python
def test_get_products_raises_when_name_missing():
    client = FakeSheetsClient(
        [ProductModel(id=2, name=None, price=50.0)]
    )
    adapter = GetAllProductsAdapter(google_table_api_client=client)  # type: ignore[arg-type]

    with pytest.raises(SynchronizationError, match="не указано имя"):
        adapter.execute()
```

Запуск: `uv run pytest tests/infrastructure/google_sheets/test_get_products_adapter.py -q`

Ожидается: PASS

---

### Задача 8: SyncProductsCache — ошибка при пустом списке товаров

**Файлы:**
- Изменить: `src/application/use_cases/sync/sync_products_cache.py`
- Изменить: `tests/application/test_sync_all_caches.py`
- Изменить: `tests/application/conftest.py`

- [ ] **Шаг 1: Добавить FakeProductsPortEmpty в conftest**

```python
class FakeProductsPortEmpty(GetAllProductsPort):
    def execute(self) -> list[Product]:
        return []
```

- [ ] **Шаг 2: Написать падающий тест**

В `tests/application/test_sync_all_caches.py`:

```python
def test_sync_all_caches_raises_when_products_empty():
    product_repo = InMemoryProductRepository()
    matrix_repo = InMemoryMatrixRepository()
    vm_repo = InMemoryVendingMachineRepository()

    sync_all = SyncAllCachesUseCase(
        sync_products=SyncProductsCache(
            get_products=FakeProductsPortEmpty(),
            product_repository=product_repo,
        ),
        sync_vending_machines=SyncVendingMachinesCache(
            get_vending_machines=FakeVendingMachinesPort(),
            vending_machine_repository=vm_repo,
        ),
        sync_matrices=SyncMatricesCache(
            get_all_matrices=FakeMatricesPort(),
            matrix_repository=matrix_repo,
        ),
    )

    with pytest.raises(SynchronizationError, match="не были получены товары"):
        asyncio.run(sync_all.execute())
```

(Добавить `import pytest` и `SynchronizationError`, импорт `FakeProductsPortEmpty`.)

- [ ] **Шаг 3: Запустить тест и убедиться что он падает**

Запуск: `uv run pytest tests/application/test_sync_all_caches.py::test_sync_all_caches_raises_when_products_empty -q`

Ожидается: FAIL

- [ ] **Шаг 4: Реализовать проверку**

В `src/application/use_cases/sync/sync_products_cache.py`:

```python
from src.domain.exceptions import SynchronizationError

    def execute(self) -> None:
        self.product_repository.clear()
        products = self.get_products.execute()
        if not products:
            raise SynchronizationError("При попытке синхронизации не были получены товары.")
        for product in products:
            self.product_repository.add(product)
```

- [ ] **Шаг 5: Прогон**

Запуск: `uv run pytest tests/application/test_sync_all_caches.py -q`

Ожидается: PASS

---

### Задача 9: Мелкие правки стиля (main.py)

**Файлы:**
- Изменить: `main.py`

- [ ] **Шаг 1: Вынести import logging наверх**

```python
import argparse
import asyncio
import logging
import sys

from src.bootstrap.container import Container
# ...

async def async_main(argv: list[str] | None = None) -> int:
    ...
    configure_logging()
    logging.getLogger().setLevel(settings.log_level)
```

Удалить `import logging` из тела функции.

- [ ] **Шаг 2: Прогон**

Запуск: `uv run pytest -q`

Ожидается: PASS

---

## Само-ревью плана

### Покрытие замечаний код-ревью

| Замечание | Задача |
|-----------|--------|
| JobRun `completed` при пропуске матриц | 1, 2 |
| Дублирование KitAPIConfig.from_env | 4 |
| Google credentials не в Settings | 5 |
| interfaces → infrastructure | 6 |
| Пробелы в тестах application | 2, 3 |
| GetAllProductsAdapter хрупкость | 7 |
| SyncProductsCache пустой список | 8 |
| main.py import logging | 9 |

**Не включено намеренно (низкий приоритет):** массовое добавление `from __future__ import annotations` во все файлы; подключение ruff/mypy в pyproject — отдельная задача tooling.

### Проверка плейсхолдеров

Плейсхолдеров нет: каждый шаг содержит конкретный код или команду с ожидаемым выводом.

### Согласованность имён

- `DeployMatricesUseCase.execute` → `tuple[int, int, int]` во всех задачах 1–3
- `FakeDeployMatrices.return_value` → 3-tuple с задачи 2
- `google_application_credentials` — env-имя pydantic-settings (uppercase в .env)

---
