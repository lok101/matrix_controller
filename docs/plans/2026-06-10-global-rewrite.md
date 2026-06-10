# План реализации: Глобальное переписывание matrix-controller

> **Для агентов:** Используй скилл executing-plans для реализации этого плана задача за задачей. Шаги используют синтаксис чекбоксов (`- [ ]`) для отслеживания.

**Цель:** Переписать проект с нуля (big bang) с сохранением бизнес-сути, единым pipeline оркестрации, тестами P0+P1 и entry points для interactive / scheduled режимов.

**Архитектура:** Clean Architecture — `domain` (entities, ports, repositories, services) → `application` (use cases) → `infrastructure` (kit_vending, google_sheets, persistence) → `interfaces` (cli, http stub) → `bootstrap` (settings, container). `kit_vending/` переносится as-is с обновлением импортов.

**Ключевые файлы / стек:** Python 3.12+, `uv`, `aiohttp`, `pydantic`, `pydantic-settings`, `beartype`, sync pytest + `asyncio.run()`.

**Спек:** [docs/specs/2026-06-10-global-rewrite-design.md](../specs/2026-06-10-global-rewrite-design.md)

---

## Карта файлов (целевое состояние)

| Путь | Ответственность |
|------|-----------------|
| `src/domain/exceptions.py` | `SynchronizationError`, `MatrixValidationError`, `UploadMatrixError`, `JobRunError` |
| `src/domain/project_timezone.py` | `PROJECT_TIMEZONE` |
| `src/domain/entities/*.py` | `Matrix`, `MatrixCell`, `Product`, `VendingMachine`, `JobRun` |
| `src/domain/value_objects/*.py` | `Money`, `CommandResult`, ID value objects |
| `src/domain/repositories/*.py` | ABC: Matrix, Product, VendingMachine, JobRun |
| `src/domain/services/matrix_validator.py` | Валидация матрицы |
| `src/domain/ports/*.py` | Kit, Sheets, GetVendingMachines, MatrixSelection |
| `src/application/use_cases/sync/*.py` | SyncProducts, SyncMatrices, SyncVendingMachines, SyncAllCaches |
| `src/application/use_cases/deploy/*.py` | UploadAndApplyMatrix, DeployMatrices |
| `src/application/use_cases/orchestration/run_deployment_job.py` | Единый pipeline |
| `src/infrastructure/persistence/in_memory/*.py` | In-memory repos + JobRun |
| `src/infrastructure/persistence/sqlite/job_run_repository.py` | Заглушка NotImplementedError |
| `src/infrastructure/google_sheets/` | Client + adapters |
| `src/infrastructure/kit_vending/` | As-is (обновить импорты) |
| `src/infrastructure/selection/*.py` | Interactive, Configured selection |
| `src/infrastructure/logging.py` | configure_logging |
| `src/interfaces/cli/*.py` | interactive, scheduled handlers |
| `src/interfaces/http/__init__.py` | Заглушка webhook |
| `src/bootstrap/settings.py` | pydantic-settings |
| `src/bootstrap/container.py` | DI composition root |
| `main.py` | argparse → container → dispatch |
| `tests/domain/`, `tests/application/`, … | TDD-тесты |

**Удалить после завершения:**

- `src/controllers/`
- `src/application/repositories/`
- `src/application/services/`
- `src/application/exceptions.py`
- `src/domain/entites/` (опечатка)
- `src/infrastructure/adapters/`
- `src/infrastructure/repositories/`
- `src/infrastructure/interactive_matrices_selector.py`
- `src/infrastructure/google_sheets_api_client.py` (после переноса)
- `src/infrastructure/logger.py` (после переноса)

---

### Задача 1: Зависимости и каркас пакетов

**Файлы:**
- Изменить: `pyproject.toml`
- Создать: пустые `__init__.py` для новых пакетов

- [ ] **Шаг 1: Добавить `pydantic-settings` в `pyproject.toml`**

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
    "pydantic-settings>=2.0.0",
    "beartype>=0.22.9",
    "tzlocal>=5.3.1",
]

[dependency-groups]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Шаг 2: Создать пустые пакеты**

Создать пустые файлы:

```
src/domain/entities/__init__.py
src/domain/services/__init__.py
src/application/use_cases/sync/__init__.py
src/application/use_cases/deploy/__init__.py
src/application/use_cases/orchestration/__init__.py
src/infrastructure/persistence/__init__.py
src/infrastructure/persistence/in_memory/__init__.py
src/infrastructure/persistence/sqlite/__init__.py
src/infrastructure/google_sheets/__init__.py
src/infrastructure/selection/__init__.py
src/interfaces/__init__.py
src/interfaces/cli/__init__.py
src/interfaces/http/__init__.py
src/bootstrap/__init__.py
tests/domain/__init__.py
tests/application/__init__.py
tests/infrastructure/persistence/__init__.py
tests/interfaces/__init__.py
tests/interfaces/cli/__init__.py
```

- [ ] **Шаг 3: Синхронизировать зависимости**

Запуск: `uv sync --group dev`  
Ожидается: exit 0

---

### Задача 2: Domain — exceptions, timezone, value objects

**Файлы:**
- Создать: `src/domain/exceptions.py`, `src/domain/project_timezone.py`
- Создать: `src/domain/value_objects/money.py`, `command_result.py`, IDs
- Тест: `tests/domain/test_value_objects.py`

- [ ] **Шаг 1: Написать падающий тест value objects**

```python
# tests/domain/test_value_objects.py
from src.domain.value_objects.money import Money
from src.domain.value_objects.ids.product_id import ProductId
from src.domain.value_objects.ids.vending_machine_id import VMId
from src.domain.value_objects.command_result import CommandResult


def test_money_from_rubles():
    money = Money(rubles=10.50)
    assert money.as_ruble() == 10.50


def test_money_from_kopecks():
    money = Money(kopecks=1050)
    assert money.as_ruble() == 10.50


def test_command_result_fields():
    result = CommandResult(success=False, step="send_command", message="timeout", attempts=3)
    assert result.success is False
    assert result.attempts == 3


def test_product_id_value():
    assert ProductId(42).value == 42


def test_vm_id_value():
    assert VMId(101).value == 101
```

- [ ] **Шаг 2: Запустить тест и убедиться что он падает**

Запуск: `uv run pytest tests/domain/test_value_objects.py -q`  
Ожидается: FAIL (ModuleNotFoundError)

- [ ] **Шаг 3: Создать `src/domain/exceptions.py`**

```python
class SynchronizationError(Exception):
    pass


class MatrixValidationError(Exception):
    pass


class UploadMatrixError(Exception):
    pass


class JobRunError(Exception):
    pass
```

- [ ] **Шаг 4: Создать `src/domain/project_timezone.py`**

```python
from zoneinfo import ZoneInfo

PROJECT_TIMEZONE: ZoneInfo = ZoneInfo("Asia/Yekaterinburg")
```

- [ ] **Шаг 5: Создать value objects**

`src/domain/value_objects/money.py` — скопировать из `src/domain/value_objects/money.py` (текущий файл без изменений).

`src/domain/value_objects/command_result.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class CommandResult:
    success: bool
    step: Literal["send_command", "verify_status"]
    message: str
    attempts: int
```

`src/domain/value_objects/ids/product_id.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProductId:
    value: int
```

`src/domain/value_objects/ids/vending_machine_id.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VMId:
    value: int
```

`src/domain/value_objects/ids/vending_machine_kit_id.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VMKitId:
    value: int
```

`src/domain/value_objects/ids/matrix_kit_id.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MatrixKitId:
    value: int
```

`src/domain/value_objects/ids/job_run_id.py`:

```python
from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class JobRunId:
    value: str

    @classmethod
    def generate(cls) -> JobRunId:
        return cls(value=str(uuid.uuid4()))
```

- [ ] **Шаг 6: Запустить тест и убедиться что он проходит**

Запуск: `uv run pytest tests/domain/test_value_objects.py -q`  
Ожидается: PASS

---

### Задача 3: Domain — entities

**Файлы:**
- Создать: `src/domain/entities/product.py`, `cell.py`, `matrix.py`, `vending_machine.py`, `job_run.py`

- [ ] **Шаг 1: Создать entities**

`src/domain/entities/product.py`:

```python
from dataclasses import dataclass

from beartype import beartype

from src.domain.value_objects.ids.product_id import ProductId
from src.domain.value_objects.money import Money


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class Product:
    id: ProductId
    name: str
    purchase_price: Money
```

`src/domain/entities/cell.py`:

```python
from dataclasses import dataclass

from src.domain.entities.product import Product
from src.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True, kw_only=True)
class MatrixCell:
    line_number: int
    product: Product
    price: Money
```

`src/domain/entities/matrix.py`:

```python
from dataclasses import dataclass

from src.domain.entities.cell import MatrixCell
from src.domain.value_objects.ids.vending_machine_id import VMId


@dataclass(frozen=True, slots=True, kw_only=True)
class Matrix:
    name: str
    cells: list[MatrixCell]
    vending_machines_ids: list[VMId]
```

`src/domain/entities/vending_machine.py`:

```python
from dataclasses import dataclass

from src.domain.value_objects.ids.vending_machine_id import VMId
from src.domain.value_objects.ids.vending_machine_kit_id import VMKitId


@dataclass(frozen=True)
class VendingMachine:
    id: VMId
    kit_id: VMKitId
    name: str
```

`src/domain/entities/job_run.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from src.domain.value_objects.ids.job_run_id import JobRunId

JobRunTrigger = Literal["interactive", "scheduled", "webhook"]
JobRunStatus = Literal["running", "completed", "failed", "partial"]


@dataclass(frozen=True, slots=True, kw_only=True)
class JobRun:
    id: JobRunId
    trigger: JobRunTrigger
    status: JobRunStatus
    started_at: datetime
    finished_at: datetime | None
    matrices_total: int
    matrices_success: int
    matrices_failed: int
    error_summary: str | None
```

- [ ] **Шаг 2: Проверить импорты**

Запуск: `uv run python -c "from src.domain.entities.matrix import Matrix; print('ok')"`  
Ожидается: `ok`

---

### Задача 4: Domain — MatrixValidator (TDD)

**Файлы:**
- Создать: `src/domain/services/matrix_validator.py`
- Тест: `tests/domain/test_matrix_validator.py`

- [ ] **Шаг 1: Написать падающий тест**

```python
# tests/domain/test_matrix_validator.py
import pytest

from src.domain.entities.cell import MatrixCell
from src.domain.entities.matrix import Matrix
from src.domain.entities.product import Product
from src.domain.exceptions import MatrixValidationError
from src.domain.services.matrix_validator import MatrixValidator
from src.domain.value_objects.ids.product_id import ProductId
from src.domain.value_objects.ids.vending_machine_id import VMId
from src.domain.value_objects.money import Money


def _product(name: str = "Cola", purchase: float = 50.0) -> Product:
    return Product(id=ProductId(1), name=name, purchase_price=Money(rubles=purchase))


def _matrix(cells: list[MatrixCell]) -> Matrix:
    return Matrix(name="Test", cells=cells, vending_machines_ids=[VMId(1)])


def test_validate_passes_when_prices_ok():
    cell = MatrixCell(line_number=1, product=_product(), price=Money(rubles=100))
    MatrixValidator.validate(_matrix([cell]))


def test_validate_raises_when_sale_below_purchase():
    cell = MatrixCell(line_number=1, product=_product(purchase=100), price=Money(rubles=50))
    with pytest.raises(MatrixValidationError, match="Неверная цена продажи"):
        MatrixValidator.validate(_matrix([cell]))


def test_validate_raises_when_purchase_zero():
    cell = MatrixCell(line_number=2, product=_product(purchase=0), price=Money(rubles=10))
    with pytest.raises(MatrixValidationError, match="Неверная закупочная цена"):
        MatrixValidator.validate(_matrix([cell]))


def test_validate_raises_when_no_cells():
    with pytest.raises(MatrixValidationError, match="не содержит ни одной ячейки"):
        MatrixValidator.validate(_matrix([]))
```

- [ ] **Шаг 2: Запустить тест и убедиться что он падает**

Запуск: `uv run pytest tests/domain/test_matrix_validator.py -q`  
Ожидается: FAIL

- [ ] **Шаг 3: Реализовать `MatrixValidator`**

```python
# src/domain/services/matrix_validator.py
from dataclasses import dataclass

from beartype import beartype

from src.domain.entities.matrix import Matrix
from src.domain.exceptions import MatrixValidationError


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class MatrixValidator:

    @classmethod
    def validate(cls, matrix: Matrix) -> None:
        if not matrix.cells:
            raise MatrixValidationError(
                f"Матрица '{matrix.name}' не содержит ни одной ячейки."
            )

        bad_price_cells: list[str] = []
        bad_purchase_price_cells: list[str] = []

        for cell in matrix.cells:
            price_rub: float = cell.price.as_ruble()
            purchase_price_rub: float = cell.product.purchase_price.as_ruble()

            if price_rub < purchase_price_rub:
                bad_price_cells.append(
                    f"строка={cell.line_number}, товар='{cell.product.name}', цена={price_rub}"
                )

            if purchase_price_rub <= 0:
                bad_purchase_price_cells.append(
                    f"строка={cell.line_number}, товар='{cell.product.name}', "
                    f"закупочная_цена={purchase_price_rub}"
                )

        if not bad_price_cells and not bad_purchase_price_cells:
            return

        messages: list[str] = []

        if bad_price_cells:
            messages.append(
                "Неверная цена продажи (ниже закупочной): " + "; ".join(bad_price_cells)
            )

        if bad_purchase_price_cells:
            messages.append(
                "Неверная закупочная цена (<= 0): " + "; ".join(bad_purchase_price_cells)
            )

        raise MatrixValidationError(
            f"Матрица '{matrix.name}' не прошла валидацию.\n" + "\n".join(messages)
        )
```

- [ ] **Шаг 4: Запустить тест и убедиться что он проходит**

Запуск: `uv run pytest tests/domain/test_matrix_validator.py -q`  
Ожидается: PASS

---

### Задача 5: Domain — repositories и ports

**Файлы:**
- Создать: `src/domain/repositories/*.py`
- Создать: `src/domain/ports/*.py`

- [ ] **Шаг 1: Создать repository ABCs**

`src/domain/repositories/matrix_repository.py`:

```python
from abc import ABC, abstractmethod

from src.domain.entities.matrix import Matrix


class MatrixRepository(ABC):
    @abstractmethod
    def get_by_name(self, matrix_name: str) -> Matrix | None: ...

    @abstractmethod
    def get_all(self) -> list[Matrix]: ...

    @abstractmethod
    def add(self, matrix: Matrix) -> None: ...

    @abstractmethod
    def clear(self) -> None: ...

    @abstractmethod
    def get_size(self) -> int: ...
```

`src/domain/repositories/product_repository.py`:

```python
from abc import ABC, abstractmethod

from src.domain.entities.product import Product


class ProductRepository(ABC):
    @abstractmethod
    def get_by_name(self, product_name: str) -> Product | None: ...

    @abstractmethod
    def add(self, product: Product) -> None: ...

    @abstractmethod
    def clear(self) -> None: ...

    @abstractmethod
    def get_size(self) -> int: ...
```

`src/domain/repositories/vending_machine_repository.py`:

```python
from abc import ABC, abstractmethod

from src.domain.entities.vending_machine import VendingMachine
from src.domain.value_objects.ids.vending_machine_id import VMId


class VendingMachineRepository(ABC):
    @abstractmethod
    def get_by_id(self, machine_id: VMId) -> VendingMachine | None: ...

    @abstractmethod
    def add(self, vending_machine: VendingMachine) -> None: ...

    @abstractmethod
    def clear(self) -> None: ...

    @abstractmethod
    def get_size(self) -> int: ...
```

`src/domain/repositories/job_run_repository.py`:

```python
from abc import ABC, abstractmethod

from src.domain.entities.job_run import JobRun
from src.domain.value_objects.ids.job_run_id import JobRunId


class JobRunRepository(ABC):
    @abstractmethod
    def create(self, job_run: JobRun) -> None: ...

    @abstractmethod
    def update(self, job_run: JobRun) -> None: ...

    @abstractmethod
    def get_by_id(self, job_run_id: JobRunId) -> JobRun | None: ...
```

- [ ] **Шаг 2: Создать ports**

`src/domain/ports/get_products.py`:

```python
from abc import ABC, abstractmethod

from src.domain.entities.product import Product


class GetAllProductsPort(ABC):
    @abstractmethod
    def execute(self) -> list[Product]: ...
```

`src/domain/ports/get_matrices.py`:

```python
from abc import ABC, abstractmethod

from src.domain.entities.matrix import Matrix


class GetAllMatricesPort(ABC):
    @abstractmethod
    def execute(self) -> list[Matrix]: ...
```

`src/domain/ports/get_vending_machines.py`:

```python
from abc import ABC, abstractmethod

from src.domain.entities.vending_machine import VendingMachine


class GetVendingMachinesPort(ABC):
    @abstractmethod
    async def execute(self) -> list[VendingMachine]: ...
```

`src/domain/ports/upload_machine_matrix.py`:

```python
from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.entities.matrix import Matrix
from src.domain.value_objects.ids.matrix_kit_id import MatrixKitId


class UploadMatrixPort(ABC):
    @abstractmethod
    async def execute(self, matrix: Matrix, timestamp: datetime) -> MatrixKitId | None: ...
```

`src/domain/ports/bind_matrix_to_vending_machine.py`:

```python
from abc import ABC, abstractmethod

from src.domain.entities.vending_machine import VendingMachine
from src.domain.value_objects.ids.matrix_kit_id import MatrixKitId


class BindMatrixToVendingMachinePort(ABC):
    @abstractmethod
    async def execute(
        self, vending_machine: VendingMachine, matrix_kit_id: MatrixKitId
    ) -> bool: ...
```

`src/domain/ports/download_matrix_to_vending_machine.py`:

```python
from abc import ABC, abstractmethod

from src.domain.entities.vending_machine import VendingMachine
from src.domain.value_objects.command_result import CommandResult


class DownloadMatrixToVendingMachinePort(ABC):
    @abstractmethod
    async def execute(self, vending_machine: VendingMachine) -> CommandResult: ...
```

`src/domain/ports/apply_matrix_to_vending_machine.py`:

```python
from abc import ABC, abstractmethod

from src.domain.entities.vending_machine import VendingMachine
from src.domain.value_objects.command_result import CommandResult


class ApplyMatrixToVendingMachinePort(ABC):
    @abstractmethod
    async def execute(self, vending_machine: VendingMachine) -> CommandResult: ...
```

`src/domain/ports/matrix_selection.py`:

```python
from abc import ABC, abstractmethod

from src.domain.entities.matrix import Matrix


class MatrixSelectionPort(ABC):
    @abstractmethod
    def select(self, available: list[Matrix]) -> list[str]: ...
```

---

### Задача 6: Infrastructure — in-memory persistence (TDD)

**Файлы:**
- Создать: `src/infrastructure/persistence/in_memory/*.py`
- Создать: `src/infrastructure/persistence/sqlite/job_run_repository.py`
- Тест: `tests/infrastructure/persistence/test_in_memory_repositories.py`

- [ ] **Шаг 1: Написать падающий тест JobRun repository**

```python
# tests/infrastructure/persistence/test_in_memory_repositories.py
from datetime import datetime

from src.domain.entities.job_run import JobRun
from src.domain.value_objects.ids.job_run_id import JobRunId
from src.infrastructure.persistence.in_memory.job_run_repository import InMemoryJobRunRepository


def test_job_run_create_and_update():
    repo = InMemoryJobRunRepository()
    job_id = JobRunId.generate()
    running = JobRun(
        id=job_id,
        trigger="scheduled",
        status="running",
        started_at=datetime(2026, 6, 10, 12, 0, 0),
        finished_at=None,
        matrices_total=0,
        matrices_success=0,
        matrices_failed=0,
        error_summary=None,
    )
    repo.create(running)

    finished = JobRun(
        id=job_id,
        trigger="scheduled",
        status="completed",
        started_at=running.started_at,
        finished_at=datetime(2026, 6, 10, 12, 5, 0),
        matrices_total=2,
        matrices_success=2,
        matrices_failed=0,
        error_summary=None,
    )
    repo.update(finished)

    stored = repo.get_by_id(job_id)
    assert stored is not None
    assert stored.status == "completed"
    assert stored.matrices_success == 2
```

- [ ] **Шаг 2: Запустить тест и убедиться что он падает**

Запуск: `uv run pytest tests/infrastructure/persistence/test_in_memory_repositories.py -q`  
Ожидается: FAIL

- [ ] **Шаг 3: Реализовать in-memory repos**

`src/infrastructure/persistence/in_memory/matrix_repository.py`:

```python
from src.domain.entities.matrix import Matrix
from src.domain.repositories.matrix_repository import MatrixRepository


class InMemoryMatrixRepository(MatrixRepository):
    def __init__(self) -> None:
        self._storage: dict[str, Matrix] = {}

    def get_by_name(self, matrix_name: str) -> Matrix | None:
        return self._storage.get(matrix_name)

    def get_all(self) -> list[Matrix]:
        return list(self._storage.values())

    def add(self, matrix: Matrix) -> None:
        self._storage[matrix.name] = matrix

    def clear(self) -> None:
        self._storage.clear()

    def get_size(self) -> int:
        return len(self._storage)
```

`src/infrastructure/persistence/in_memory/product_repository.py`:

```python
from src.domain.entities.product import Product
from src.domain.repositories.product_repository import ProductRepository


class InMemoryProductRepository(ProductRepository):
    def __init__(self) -> None:
        self._storage: dict[str, Product] = {}

    def get_by_name(self, product_name: str) -> Product | None:
        return self._storage.get(product_name)

    def add(self, product: Product) -> None:
        self._storage[product.name] = product

    def clear(self) -> None:
        self._storage.clear()

    def get_size(self) -> int:
        return len(self._storage)
```

`src/infrastructure/persistence/in_memory/vending_machine_repository.py`:

```python
from src.domain.entities.vending_machine import VendingMachine
from src.domain.repositories.vending_machine_repository import VendingMachineRepository
from src.domain.value_objects.ids.vending_machine_id import VMId


class InMemoryVendingMachineRepository(VendingMachineRepository):
    def __init__(self) -> None:
        self._storage: dict[int, VendingMachine] = {}

    def get_by_id(self, machine_id: VMId) -> VendingMachine | None:
        return self._storage.get(machine_id.value)

    def add(self, vending_machine: VendingMachine) -> None:
        self._storage[vending_machine.id.value] = vending_machine

    def clear(self) -> None:
        self._storage.clear()

    def get_size(self) -> int:
        return len(self._storage)
```

`src/infrastructure/persistence/in_memory/job_run_repository.py`:

```python
from src.domain.entities.job_run import JobRun
from src.domain.repositories.job_run_repository import JobRunRepository
from src.domain.value_objects.ids.job_run_id import JobRunId


class InMemoryJobRunRepository(JobRunRepository):
    def __init__(self) -> None:
        self._storage: dict[str, JobRun] = {}

    def create(self, job_run: JobRun) -> None:
        self._storage[job_run.id.value] = job_run

    def update(self, job_run: JobRun) -> None:
        self._storage[job_run.id.value] = job_run

    def get_by_id(self, job_run_id: JobRunId) -> JobRun | None:
        return self._storage.get(job_run_id.value)
```

- [ ] **Шаг 4: Создать SQLite-заглушку**

```python
# src/infrastructure/persistence/sqlite/job_run_repository.py
from src.domain.entities.job_run import JobRun
from src.domain.repositories.job_run_repository import JobRunRepository
from src.domain.value_objects.ids.job_run_id import JobRunId


class SqliteJobRunRepository(JobRunRepository):
    """Заглушка — реализация запланирована на следующий этап."""

    def create(self, job_run: JobRun) -> None:
        raise NotImplementedError("SQLite JobRunRepository ещё не реализован")

    def update(self, job_run: JobRun) -> None:
        raise NotImplementedError("SQLite JobRunRepository ещё не реализован")

    def get_by_id(self, job_run_id: JobRunId) -> JobRun | None:
        raise NotImplementedError("SQLite JobRunRepository ещё не реализован")
```

- [ ] **Шаг 5: Запустить тест и убедиться что он проходит**

Запуск: `uv run pytest tests/infrastructure/persistence/test_in_memory_repositories.py -q`  
Ожидается: PASS

---

### Задача 7: Application — UploadAndApplyMatrixUseCase (TDD)

**Файлы:**
- Создать: `src/application/use_cases/deploy/upload_and_apply_matrix.py`
- Создать: `tests/application/conftest.py`
- Тест: `tests/application/test_upload_and_apply_matrix.py`

- [ ] **Шаг 1: Создать fakes в conftest**

```python
# tests/application/conftest.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.domain.entities.cell import MatrixCell
from src.domain.entities.matrix import Matrix
from src.domain.entities.product import Product
from src.domain.entities.vending_machine import VendingMachine
from src.domain.value_objects.command_result import CommandResult
from src.domain.value_objects.ids.matrix_kit_id import MatrixKitId
from src.domain.value_objects.ids.product_id import ProductId
from src.domain.value_objects.ids.vending_machine_id import VMId
from src.domain.value_objects.ids.vending_machine_kit_id import VMKitId
from src.domain.value_objects.money import Money


def make_product() -> Product:
    return Product(id=ProductId(1), name="Cola", purchase_price=Money(rubles=50))


def make_cell() -> MatrixCell:
    return MatrixCell(line_number=1, product=make_product(), price=Money(rubles=100))


def make_matrix(name: str = "M1") -> Matrix:
    return Matrix(name=name, cells=[make_cell()], vending_machines_ids=[VMId(101)])


def make_machine(name: str = "VM-1") -> VendingMachine:
    return VendingMachine(id=VMId(101), kit_id=VMKitId(1001), name=name)


@dataclass
class FakeUploadPort:
    result: MatrixKitId | None = MatrixKitId(999)
    calls: list[tuple[Matrix, datetime]] = field(default_factory=list)

    async def execute(self, matrix: Matrix, timestamp: datetime) -> MatrixKitId | None:
        self.calls.append((matrix, timestamp))
        return self.result


@dataclass
class FakeBindPort:
    result: bool = True
    calls: int = 0

    async def execute(self, vending_machine: VendingMachine, matrix_kit_id: MatrixKitId) -> bool:
        self.calls += 1
        return self.result


@dataclass
class FakeCommandPort:
    result: CommandResult = CommandResult(success=True, step="verify_status", message="ok", attempts=1)
    calls: int = 0

    async def execute(self, vending_machine: VendingMachine) -> CommandResult:
        self.calls += 1
        return self.result
```

- [ ] **Шаг 2: Написать падающий тест**

```python
# tests/application/test_upload_and_apply_matrix.py
import asyncio
from datetime import datetime

from src.application.use_cases.deploy.upload_and_apply_matrix import UploadAndApplyMatrixUseCase
from src.domain.exceptions import UploadMatrixError
from tests.application.conftest import (
    FakeBindPort,
    FakeCommandPort,
    FakeUploadPort,
    make_machine,
    make_matrix,
)


def test_upload_and_apply_happy_path():
    upload = FakeUploadPort()
    bind = FakeBindPort()
    download = FakeCommandPort()
    apply_port = FakeCommandPort()
    uc = UploadAndApplyMatrixUseCase(
        upload_matrix_port=upload,
        bind_matrix_to_machine_port=bind,
        download_matrix_to_machine_port=download,
        apply_matrix_to_machine_port=apply_port,
        validate_matrices=True,
    )
    asyncio.run(uc.execute(make_matrix(), [make_machine()], datetime(2026, 6, 10)))
    assert len(upload.calls) == 1
    assert bind.calls == 1
    assert download.calls == 1
    assert apply_port.calls == 1


def test_upload_failure_raises():
    upload = FakeUploadPort(result=None)
    uc = UploadAndApplyMatrixUseCase(
        upload_matrix_port=upload,
        bind_matrix_to_machine_port=FakeBindPort(),
        download_matrix_to_machine_port=FakeCommandPort(),
        apply_matrix_to_machine_port=FakeCommandPort(),
        validate_matrices=False,
    )
    try:
        asyncio.run(uc.execute(make_matrix(), [make_machine()], datetime(2026, 6, 10)))
        assert False, "expected UploadMatrixError"
    except UploadMatrixError:
        pass
```

- [ ] **Шаг 3: Запустить тест и убедиться что он падает**

Запуск: `uv run pytest tests/application/test_upload_and_apply_matrix.py -q`  
Ожидается: FAIL

- [ ] **Шаг 4: Реализовать use case**

```python
# src/application/use_cases/deploy/upload_and_apply_matrix.py
import logging
from dataclasses import dataclass
from datetime import datetime

from beartype import beartype

from src.domain.entities.matrix import Matrix
from src.domain.entities.vending_machine import VendingMachine
from src.domain.exceptions import MatrixValidationError, UploadMatrixError
from src.domain.ports.apply_matrix_to_vending_machine import ApplyMatrixToVendingMachinePort
from src.domain.ports.bind_matrix_to_vending_machine import BindMatrixToVendingMachinePort
from src.domain.ports.download_matrix_to_vending_machine import DownloadMatrixToVendingMachinePort
from src.domain.ports.upload_machine_matrix import UploadMatrixPort
from src.domain.services.matrix_validator import MatrixValidator
from src.domain.value_objects.command_result import CommandResult
from src.domain.value_objects.ids.matrix_kit_id import MatrixKitId

logger = logging.getLogger(__name__)


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class UploadAndApplyMatrixUseCase:
    upload_matrix_port: UploadMatrixPort
    bind_matrix_to_machine_port: BindMatrixToVendingMachinePort
    download_matrix_to_machine_port: DownloadMatrixToVendingMachinePort
    apply_matrix_to_machine_port: ApplyMatrixToVendingMachinePort
    validate_matrices: bool = True

    async def execute(
        self, matrix: Matrix, machines: list[VendingMachine], timestamp: datetime
    ) -> tuple[int, int]:
        if not machines:
            raise UploadMatrixError("Не переданы аппараты для применения матрицы.")

        if self.validate_matrices:
            MatrixValidator.validate(matrix)

        matrix_id: MatrixKitId | None = await self.upload_matrix_port.execute(matrix, timestamp)
        if matrix_id is None:
            raise UploadMatrixError("Не удалось создать матрицу.")

        success_count = 0
        failure_count = 0

        for machine in machines:
            if not await self.bind_matrix_to_machine_port.execute(machine, matrix_id):
                failure_count += 1
                logger.critical(
                    "Не удалось привязать матрицу. Матрица: %s, аппарат: %s.",
                    matrix.name,
                    machine.name,
                )
                continue

            download_result: CommandResult = await self.download_matrix_to_machine_port.execute(
                machine
            )
            if not download_result.success:
                failure_count += 1
                logger.critical(
                    "Не удалось загрузить матрицу. Матрица: %s, аппарат: %s, "
                    "шаг: %s, попытка: %s, причина: %s.",
                    matrix.name,
                    machine.name,
                    download_result.step,
                    download_result.attempts,
                    download_result.message,
                )
                continue

            apply_result: CommandResult = await self.apply_matrix_to_machine_port.execute(machine)
            if not apply_result.success:
                failure_count += 1
                logger.critical(
                    "Не удалось применить матрицу. Матрица: %s, аппарат: %s, "
                    "шаг: %s, попытка: %s, причина: %s.",
                    matrix.name,
                    machine.name,
                    apply_result.step,
                    apply_result.attempts,
                    apply_result.message,
                )
                continue

            success_count += 1

        if failure_count == 0:
            logger.info(
                "Матрица '%s': все %s аппаратов обработаны успешно.",
                matrix.name,
                success_count,
            )
        elif success_count == 0:
            logger.critical(
                "Матрица '%s': полный провал — 0 из %s аппаратов.",
                matrix.name,
                len(machines),
            )
        else:
            logger.warning(
                "Матрица '%s': частичный успех — %s из %s аппаратов, ошибок: %s.",
                matrix.name,
                success_count,
                len(machines),
                failure_count,
            )

        return success_count, failure_count
```

- [ ] **Шаг 5: Запустить тест и убедиться что он проходит**

Запуск: `uv run pytest tests/application/test_upload_and_apply_matrix.py -q`  
Ожидается: PASS

---

### Задача 8: Application — DeployMatricesUseCase (TDD)

**Файлы:**
- Создать: `src/application/use_cases/deploy/deploy_matrices.py`
- Тест: `tests/application/test_deploy_matrices.py`

- [ ] **Шаг 1: Написать падающий тест**

```python
# tests/application/test_deploy_matrices.py
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock

from src.application.use_cases.deploy.deploy_matrices import DeployMatricesUseCase
from src.domain.entities.matrix import Matrix
from src.domain.entities.vending_machine import VendingMachine
from tests.application.conftest import make_matrix, make_machine


def test_deploy_matrices_returns_success_and_failure_counts():
    upload_uc = AsyncMock()
    upload_uc.execute = AsyncMock(side_effect=[(1, 0), (0, 1)])

    matrix_repo = type("Repo", (), {})()
    matrix_repo.get_by_name = lambda name: make_matrix(name)
    vm_repo = type("Repo", (), {})()
    vm_repo.get_by_id = lambda _id: make_machine()

    uc = DeployMatricesUseCase(
        matrix_repository=matrix_repo,
        vending_machine_repository=vm_repo,
        upload_and_apply_matrix_uc=upload_uc,
    )

    success, failed = asyncio.run(
        uc.execute(["M1", "M2"], datetime(2026, 6, 10))
    )
    assert success == 1
    assert failed == 1
```

- [ ] **Шаг 2: Запустить тест и убедиться что он падает**

Запуск: `uv run pytest tests/application/test_deploy_matrices.py -q`  
Ожидается: FAIL

- [ ] **Шаг 3: Реализовать use case**

```python
# src/application/use_cases/deploy/deploy_matrices.py
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from beartype import beartype

from src.application.use_cases.deploy.upload_and_apply_matrix import UploadAndApplyMatrixUseCase
from src.domain.entities.vending_machine import VendingMachine
from src.domain.exceptions import UploadMatrixError
from src.domain.repositories.matrix_repository import MatrixRepository
from src.domain.repositories.vending_machine_repository import VendingMachineRepository
from src.domain.value_objects.ids.vending_machine_id import VMId

logger = logging.getLogger(__name__)


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class DeployMatricesUseCase:
    matrix_repository: MatrixRepository
    vending_machine_repository: VendingMachineRepository
    upload_and_apply_matrix_uc: UploadAndApplyMatrixUseCase

    async def execute(
        self, selected_matrix_names: list[str], timestamp: datetime
    ) -> tuple[int, int]:
        if not selected_matrix_names:
            raise UploadMatrixError("Не выбрано ни одной матрицы для загрузки")

        tasks = []
        names: list[str] = []

        for name in selected_matrix_names:
            matrix = self.matrix_repository.get_by_name(name)
            if matrix is None:
                logger.error("Матрица с именем '%s' не найдена", name)
                continue

            machines = self._get_vending_machines(matrix.vending_machines_ids)
            if not machines:
                logger.warning("Не найдено ни одной машины для матрицы '%s'", name)
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

        return matrices_success, matrices_failed

    def _get_vending_machines(self, machines_ids: list[VMId]) -> list[VendingMachine]:
        res: list[VendingMachine] = []
        for machine_id in machines_ids:
            vm = self.vending_machine_repository.get_by_id(machine_id)
            if vm is None:
                logger.error("Не была получена машина с Id: %s.", machine_id.value)
                continue
            res.append(vm)
        return res
```

- [ ] **Шаг 4: Запустить тест и убедиться что он проходит**

Запуск: `uv run pytest tests/application/test_deploy_matrices.py -q`  
Ожидается: PASS

---

### Задача 9: Application — Sync use cases (TDD)

**Файлы:**
- Создать: `src/application/use_cases/sync/sync_products_cache.py`
- Создать: `src/application/use_cases/sync/sync_matrices_cache.py`
- Создать: `src/application/use_cases/sync/sync_vending_machines_cache.py`
- Создать: `src/application/use_cases/sync/sync_all_caches.py`
- Тест: `tests/application/test_sync_all_caches.py`

- [ ] **Шаг 1: Написать падающий тест**

```python
# tests/application/test_sync_all_caches.py
import asyncio
from dataclasses import dataclass, field
from unittest.mock import MagicMock

from src.application.use_cases.sync.sync_all_caches import SyncAllCachesUseCase
from src.domain.entities.product import Product
from src.domain.entities.matrix import Matrix
from src.domain.entities.vending_machine import VendingMachine
from src.domain.exceptions import SynchronizationError
from src.infrastructure.persistence.in_memory.matrix_repository import InMemoryMatrixRepository
from src.infrastructure.persistence.in_memory.product_repository import InMemoryProductRepository
from src.infrastructure.persistence.in_memory.vending_machine_repository import InMemoryVendingMachineRepository
from tests.application.conftest import make_matrix, make_machine, make_product


@dataclass
class FakeProductsPort:
    products: list[Product] = field(default_factory=lambda: [make_product()])

    def execute(self) -> list[Product]:
        return self.products


@dataclass
class FakeMatricesPort:
    matrices: list[Matrix] = field(default_factory=lambda: [make_matrix()])

    def execute(self) -> list[Matrix]:
        return self.matrices


@dataclass
class FakeVendingMachinesPort:
    machines: list[VendingMachine] = field(default_factory=lambda: [make_machine()])

    async def execute(self) -> list[VendingMachine]:
        return self.machines


def test_sync_all_caches_populates_repositories():
    product_repo = InMemoryProductRepository()
    matrix_repo = InMemoryMatrixRepository()
    vm_repo = InMemoryVendingMachineRepository()

    uc = SyncAllCachesUseCase(
        sync_products=MagicMock(side_effect=lambda: product_repo.add(make_product()) or product_repo.clear() or [product_repo.add(make_product())]),
    )
```

Упростить тест — вызвать три отдельных sync UC напрямую:

```python
# tests/application/test_sync_all_caches.py
import asyncio

from src.application.use_cases.sync.sync_all_caches import SyncAllCachesUseCase
from src.application.use_cases.sync.sync_matrices_cache import SyncMatricesCache
from src.application.use_cases.sync.sync_products_cache import SyncProductsCache
from src.application.use_cases.sync.sync_vending_machines_cache import SyncVendingMachinesCache
from src.infrastructure.persistence.in_memory.matrix_repository import InMemoryMatrixRepository
from src.infrastructure.persistence.in_memory.product_repository import InMemoryProductRepository
from src.infrastructure.persistence.in_memory.vending_machine_repository import InMemoryVendingMachineRepository
from tests.application.conftest import make_matrix, make_machine, make_product


class FakeProductsPort:
    def execute(self):
        return [make_product()]


class FakeMatricesPort:
    def execute(self):
        return [make_matrix()]


class FakeVendingMachinesPort:
    async def execute(self):
        return [make_machine()]


def test_sync_all_caches_populates_repositories():
    product_repo = InMemoryProductRepository()
    matrix_repo = InMemoryMatrixRepository()
    vm_repo = InMemoryVendingMachineRepository()

    sync_all = SyncAllCachesUseCase(
        sync_products=SyncProductsCache(
            get_products=FakeProductsPort(),
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

    asyncio.run(sync_all.execute())

    assert product_repo.get_size() == 1
    assert vm_repo.get_size() == 1
    assert matrix_repo.get_size() == 1
```

- [ ] **Шаг 2: Запустить тест и убедиться что он падает**

Запуск: `uv run pytest tests/application/test_sync_all_caches.py -q`  
Ожидается: FAIL

- [ ] **Шаг 3: Реализовать sync use cases**

`src/application/use_cases/sync/sync_products_cache.py`:

```python
import logging
from dataclasses import dataclass

from beartype import beartype

from src.domain.ports.get_products import GetAllProductsPort
from src.domain.repositories.product_repository import ProductRepository

logger = logging.getLogger(__name__)


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class SyncProductsCache:
    get_products: GetAllProductsPort
    product_repository: ProductRepository

    def execute(self) -> None:
        self.product_repository.clear()
        products = self.get_products.execute()
        for product in products:
            self.product_repository.add(product)
        logger.info(
            "Синхронизация товаров завершена. Товаров в репозитории: %s.",
            self.product_repository.get_size(),
        )
```

`src/application/use_cases/sync/sync_matrices_cache.py`:

```python
import logging
from dataclasses import dataclass

from beartype import beartype

from src.domain.exceptions import SynchronizationError
from src.domain.ports.get_matrices import GetAllMatricesPort
from src.domain.repositories.matrix_repository import MatrixRepository

logger = logging.getLogger(__name__)


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class SyncMatricesCache:
    get_all_matrices: GetAllMatricesPort
    matrix_repository: MatrixRepository

    async def execute(self) -> None:
        self.matrix_repository.clear()
        matrices = self.get_all_matrices.execute()
        if not matrices:
            raise SynchronizationError("При попытке синхронизации не были получены матрицы.")
        for matrix in matrices:
            self.matrix_repository.add(matrix)
        logger.info(
            "Синхронизация матриц завершена. Матриц в репозитории: %s.",
            self.matrix_repository.get_size(),
        )
```

`src/application/use_cases/sync/sync_vending_machines_cache.py`:

```python
import logging
from dataclasses import dataclass

from beartype import beartype

from src.domain.exceptions import SynchronizationError
from src.domain.ports.get_vending_machines import GetVendingMachinesPort
from src.domain.repositories.vending_machine_repository import VendingMachineRepository

logger = logging.getLogger(__name__)


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class SyncVendingMachinesCache:
    get_vending_machines: GetVendingMachinesPort
    vending_machine_repository: VendingMachineRepository

    async def execute(self) -> None:
        self.vending_machine_repository.clear()
        machines = await self.get_vending_machines.execute()
        if not machines:
            raise SynchronizationError("При попытке синхронизации не были получены аппараты.")
        for machine in machines:
            self.vending_machine_repository.add(machine)
        logger.info(
            "Синхронизация аппаратов завершена. Аппаратов в репозитории: %s.",
            self.vending_machine_repository.get_size(),
        )
```

`src/application/use_cases/sync/sync_all_caches.py`:

```python
from dataclasses import dataclass

from beartype import beartype

from src.application.use_cases.sync.sync_matrices_cache import SyncMatricesCache
from src.application.use_cases.sync.sync_products_cache import SyncProductsCache
from src.application.use_cases.sync.sync_vending_machines_cache import SyncVendingMachinesCache


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class SyncAllCachesUseCase:
    sync_products: SyncProductsCache
    sync_vending_machines: SyncVendingMachinesCache
    sync_matrices: SyncMatricesCache

    async def execute(self) -> None:
        self.sync_products.execute()
        await self.sync_vending_machines.execute()
        await self.sync_matrices.execute()
```

- [ ] **Шаг 4: Запустить тест и убедиться что он проходит**

Запуск: `uv run pytest tests/application/test_sync_all_caches.py -q`  
Ожидается: PASS

---

### Задача 10: Application — RunDeploymentJobUseCase (TDD)

**Файлы:**
- Создать: `src/application/use_cases/orchestration/run_deployment_job.py`
- Тест: `tests/application/test_run_deployment_job.py`

- [ ] **Шаг 1: Написать падающий тест**

```python
# tests/application/test_run_deployment_job.py
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock

from src.application.use_cases.orchestration.run_deployment_job import RunDeploymentJobUseCase
from src.domain.entities.job_run import JobRunTrigger
from src.infrastructure.persistence.in_memory.job_run_repository import InMemoryJobRunRepository
from tests.application.conftest import make_matrix


class FakeSelection:
    def select(self, available):
        return [m.name for m in available]


def test_run_deployment_job_creates_and_finalizes_job_run():
    job_repo = InMemoryJobRunRepository()
    sync_all = AsyncMock()
    deploy = AsyncMock(return_value=(2, 0))
    matrix_repo = type("R", (), {"get_all": lambda self: [make_matrix()]})()

    uc = RunDeploymentJobUseCase(
        job_run_repository=job_repo,
        sync_all_caches=sync_all,
        matrix_selection=FakeSelection(),
        matrix_repository=matrix_repo,
        deploy_matrices=deploy,
    )

    job_run = asyncio.run(uc.execute(trigger="scheduled"))

    assert job_run.status == "completed"
    assert job_run.matrices_success == 2
    assert job_repo.get_by_id(job_run.id) is not None
```

- [ ] **Шаг 2: Запустить тест и убедиться что он падает**

Запуск: `uv run pytest tests/application/test_run_deployment_job.py -q`  
Ожидается: FAIL

- [ ] **Шаг 3: Реализовать use case**

```python
# src/application/use_cases/orchestration/run_deployment_job.py
import logging
from dataclasses import dataclass
from datetime import datetime

from beartype import beartype

from src.application.use_cases.deploy.deploy_matrices import DeployMatricesUseCase
from src.application.use_cases.sync.sync_all_caches import SyncAllCachesUseCase
from src.domain.entities.job_run import JobRun, JobRunTrigger
from src.domain.exceptions import SynchronizationError
from src.domain.ports.matrix_selection import MatrixSelectionPort
from src.domain.project_timezone import PROJECT_TIMEZONE
from src.domain.repositories.job_run_repository import JobRunRepository
from src.domain.repositories.matrix_repository import MatrixRepository
from src.domain.value_objects.ids.job_run_id import JobRunId

logger = logging.getLogger(__name__)


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class RunDeploymentJobUseCase:
    job_run_repository: JobRunRepository
    sync_all_caches: SyncAllCachesUseCase
    matrix_selection: MatrixSelectionPort
    matrix_repository: MatrixRepository
    deploy_matrices: DeployMatricesUseCase

    async def execute(self, trigger: JobRunTrigger) -> JobRun:
        started_at = datetime.now(tz=PROJECT_TIMEZONE)
        job_id = JobRunId.generate()
        job_run = JobRun(
            id=job_id,
            trigger=trigger,
            status="running",
            started_at=started_at,
            finished_at=None,
            matrices_total=0,
            matrices_success=0,
            matrices_failed=0,
            error_summary=None,
        )
        self.job_run_repository.create(job_run)

        try:
            await self.sync_all_caches.execute()
        except SynchronizationError as exc:
            failed = self._finalize(
                job_run,
                status="failed",
                matrices_total=0,
                matrices_success=0,
                matrices_failed=0,
                error_summary=str(exc),
            )
            return failed

        selected_names = self.matrix_selection.select(self.matrix_repository.get_all())
        if not selected_names:
            return self._finalize(
                job_run,
                status="completed",
                matrices_total=0,
                matrices_success=0,
                matrices_failed=0,
                error_summary=None,
            )

        try:
            success, failed = await self.deploy_matrices.execute(
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
        if failed == 0:
            status = "completed"
        elif success == 0:
            status = "failed"
        else:
            status = "partial"

        return self._finalize(
            job_run,
            status=status,
            matrices_total=total,
            matrices_success=success,
            matrices_failed=failed,
            error_summary=None if failed == 0 else f"Ошибок: {failed} из {total}",
        )

    def _finalize(
        self,
        job_run: JobRun,
        *,
        status: JobRun["status"],
        matrices_total: int,
        matrices_success: int,
        matrices_failed: int,
        error_summary: str | None,
    ) -> JobRun:
        finished = JobRun(
            id=job_run.id,
            trigger=job_run.trigger,
            status=status,
            started_at=job_run.started_at,
            finished_at=datetime.now(tz=PROJECT_TIMEZONE),
            matrices_total=matrices_total,
            matrices_success=matrices_success,
            matrices_failed=matrices_failed,
            error_summary=error_summary,
        )
        self.job_run_repository.update(finished)
        logger.info(
            "Job %s завершён: status=%s, success=%s, failed=%s, trigger=%s",
            finished.id.value,
            finished.status,
            finished.matrices_success,
            finished.matrices_failed,
            finished.trigger,
        )
        return finished
```

- [ ] **Шаг 4: Запустить тест и убедиться что он проходит**

Запуск: `uv run pytest tests/application/test_run_deployment_job.py -q`  
Ожидается: PASS

- [ ] **Шаг 5: Убедиться что все application/domain тесты проходят**

Запуск: `uv run pytest tests/domain tests/application tests/infrastructure/persistence -q`  
Ожидается: 0 failed

---

### Задача 11: Infrastructure — kit_vending (обновление импортов)

**Файлы:**
- Изменить: все файлы в `src/infrastructure/kit_vending/` с импортами `entites`

- [ ] **Шаг 1: Заменить импорты во всех адаптерах и workflow**

В каждом файле `src/infrastructure/kit_vending/**/*.py` заменить:

```
src.domain.entites.          → src.domain.entities.
src.application.exceptions.  → src.domain.exceptions.   (если есть)
```

Конкретные файлы:
- `adapters/upload_matrix.py`
- `adapters/bind_matrix_to_machine.py`
- `adapters/download_matrix_to_vending_machine.py`
- `adapters/apply_matrix_to_vending_machine.py`
- `matrix_command_workflow.py`

- [ ] **Шаг 2: Создать GetVendingMachinesAdapter**

```python
# src/infrastructure/kit_vending/adapters/get_vending_machines.py
import logging
from dataclasses import dataclass

from beartype import beartype

from src.domain.entities.vending_machine import VendingMachine
from src.domain.ports.get_vending_machines import GetVendingMachinesPort
from src.domain.value_objects.ids.vending_machine_id import VMId
from src.domain.value_objects.ids.vending_machine_kit_id import VMKitId
from src.infrastructure.kit_vending.api.client import KitVendingAPIClient
from src.infrastructure.kit_vending.api.models.vending_machines import ActiveVendingMachineModel

logger = logging.getLogger(__name__)


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class GetVendingMachinesAdapter(GetVendingMachinesPort):
    kit_api_client: KitVendingAPIClient

    async def execute(self) -> list[VendingMachine]:
        collection = await self.kit_api_client.get_vending_machines()
        active = collection.get_active()
        result: list[VendingMachine] = []
        for item in active:
            mapped = self._map_to_domain(item)
            if mapped is not None:
                result.append(mapped)
        return result

    @staticmethod
    def _map_to_domain(model: ActiveVendingMachineModel) -> VendingMachine | None:
        if model.number is None:
            logger.warning("Для аппарата не удалось определить код: %s", model)
            return None
        return VendingMachine(
            id=VMId(model.number),
            kit_id=VMKitId(model.id),
            name=model.name,
        )
```

- [ ] **Шаг 3: Обновить импорты в тестах kit_vending**

Запуск: `uv run pytest tests/infrastructure/kit_vending -q`  
Ожидается: PASS (0 failed)

---

### Задача 12: Infrastructure — google_sheets

**Файлы:**
- Перенести: `src/infrastructure/google_sheets_api_client.py` → `src/infrastructure/google_sheets/client.py`
- Перенести: adapters → `src/infrastructure/google_sheets/adapters/`

- [ ] **Шаг 1: Перенести client**

Скопировать содержимое `src/infrastructure/google_sheets_api_client.py` в `src/infrastructure/google_sheets/client.py` без изменений логики.

- [ ] **Шаг 2: Создать `get_products` adapter**

```python
# src/infrastructure/google_sheets/adapters/get_products.py
import logging
from dataclasses import dataclass

from beartype import beartype

from src.domain.entities.product import Product
from src.domain.ports.get_products import GetAllProductsPort
from src.domain.value_objects.ids.product_id import ProductId
from src.domain.value_objects.money import Money
from src.infrastructure.google_sheets.client import GoogleSheetsAPIClient

logger = logging.getLogger(__name__)


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class GetAllProductsAdapter(GetAllProductsPort):
    google_table_api_client: GoogleSheetsAPIClient

    def execute(self) -> list[Product]:
        res: list[Product] = []
        products_data = self.google_table_api_client.get_all_products()
        if not products_data:
            logger.warning("Не были найдены товары.")
        for product_model in products_data:
            res.append(
                Product(
                    id=ProductId(product_model.id),
                    name=product_model.name,
                    purchase_price=Money(rubles=product_model.price),
                )
            )
        return res
```

- [ ] **Шаг 3: Создать `get_matrices` adapter**

Скопировать логику из `src/infrastructure/adapters/google_sheets/get_matrices.py`, заменив импорты:

```
src.domain.entites.           → src.domain.entities.
src.application.exceptions.   → src.domain.exceptions.
src.application.repositories. → src.domain.repositories.
src.infrastructure.google_sheets_api_client → src.infrastructure.google_sheets.client
```

- [ ] **Шаг 4: Перенести logging**

Скопировать `src/infrastructure/logger.py` → `src/infrastructure/logging.py`, обновить импорт:

```python
from src.domain.project_timezone import PROJECT_TIMEZONE
```

---

### Задача 13: Infrastructure — selection policies (TDD)

**Файлы:**
- Перенести: `InteractiveSelector` → `src/infrastructure/selection/interactive_selector.py`
- Создать: `src/infrastructure/selection/configured_selection.py`
- Тест: `tests/interfaces/cli/test_configured_selection.py`

- [ ] **Шаг 1: Перенести InteractiveSelector**

Скопировать класс `InteractiveSelector` из `src/infrastructure/interactive_matrices_selector.py` в `src/infrastructure/selection/interactive_selector.py`.

- [ ] **Шаг 2: Написать падающий тест ConfiguredSelection**

```python
# tests/interfaces/cli/test_configured_selection.py
from src.domain.entities.matrix import Matrix
from src.infrastructure.selection.configured_selection import ConfiguredMatrixSelection
from tests.application.conftest import make_matrix


def test_configured_selection_all():
    sel = ConfiguredMatrixSelection(names="*")
    matrices = [make_matrix("A"), make_matrix("B")]
    assert sel.select(matrices) == ["A", "B"]


def test_configured_selection_filtered():
    sel = ConfiguredMatrixSelection(names="A")
    matrices = [make_matrix("A"), make_matrix("B")]
    assert sel.select(matrices) == ["A"]
```

- [ ] **Шаг 3: Реализовать ConfiguredMatrixSelection и InteractiveMatrixSelection**

```python
# src/infrastructure/selection/configured_selection.py
from dataclasses import dataclass

from beartype import beartype

from src.domain.entities.matrix import Matrix
from src.domain.ports.matrix_selection import MatrixSelectionPort


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class ConfiguredMatrixSelection(MatrixSelectionPort):
    names: str

    def select(self, available: list[Matrix]) -> list[str]:
        if self.names.strip() == "*":
            return [m.name for m in available]
        wanted = {n.strip() for n in self.names.split(",") if n.strip()}
        return [m.name for m in available if m.name in wanted]
```

```python
# src/infrastructure/selection/interactive_selection.py
from dataclasses import dataclass

from beartype import beartype

from src.domain.entities.matrix import Matrix
from src.domain.ports.matrix_selection import MatrixSelectionPort
from src.infrastructure.selection.interactive_selector import InteractiveSelector


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class InteractiveMatrixSelection(MatrixSelectionPort):
    interactive_selector: InteractiveSelector

    def select(self, available: list[Matrix]) -> list[str]:
        names = [m.name for m in available]
        return self.interactive_selector.select_items(names)
```

- [ ] **Шаг 4: Запустить тест**

Запуск: `uv run pytest tests/interfaces/cli/test_configured_selection.py -q`  
Ожидается: PASS

---

### Задача 14: Bootstrap — settings и container

**Файлы:**
- Создать: `src/bootstrap/settings.py`
- Создать: `src/bootstrap/container.py`

- [ ] **Шаг 1: Создать Settings**

```python
# src/bootstrap/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.infrastructure.kit_vending.api.config import KitAPIConfig


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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

    scheduled_matrix_names: str = "*"
    log_level: str = "INFO"

    def to_kit_api_config(self) -> KitAPIConfig:
        return KitAPIConfig(
            company_id=self.kit_api_company_id,
            login=self.kit_api_login,
            password=self.kit_api_password,
            request_per_window=self.kit_api_request_per_window,
            window_seconds=self.kit_api_window_seconds,
            backoff_seconds=self.kit_api_backoff_seconds,
        )
```

- [ ] **Шаг 2: Создать Container**

`src/bootstrap/container.py` собирает:

- In-memory repos (matrix, product, vm, job_run)
- KitVendingAPIClient через async context manager (метод `async def __aenter__`)
- Google Sheets client
- Все adapters и use cases
- Методы:
  - `async def run_deployment(trigger: JobRunTrigger) -> JobRun`
  - `async def sync_only() -> None`

Container принимает `Settings` и `MatrixSelectionPort` (передаётся из CLI handler).

- [ ] **Шаг 3: Проверить импорт container**

Запуск: `uv run python -c "from src.bootstrap.settings import Settings; print('ok')"`  
Ожидается: `ok`

---

### Задача 15: Interfaces — CLI и main.py

**Файлы:**
- Создать: `src/interfaces/cli/run_interactive.py`, `run_scheduled.py`
- Создать: `src/interfaces/http/__init__.py` (заглушка)
- Переписать: `main.py`

- [ ] **Шаг 1: HTTP заглушка**

```python
# src/interfaces/http/__init__.py
"""Webhook entry point — реализация запланирована на следующий этап.

Будущий контракт:
  POST /deploy  → RunDeploymentJobUseCase(trigger="webhook")
"""
```

- [ ] **Шаг 2: CLI handlers**

```python
# src/interfaces/cli/run_interactive.py
from src.application.use_cases.orchestration.run_deployment_job import RunDeploymentJobUseCase
from src.infrastructure.selection.interactive_selection import InteractiveMatrixSelection
from src.infrastructure.selection.interactive_selector import InteractiveSelector


async def run_interactive(container) -> int:
    selection = InteractiveMatrixSelection(interactive_selector=InteractiveSelector())
    container.set_matrix_selection(selection)
    job = await container.run_deployment(trigger="interactive")
    return 0 if job.status in ("completed", "partial") else 1
```

```python
# src/interfaces/cli/run_scheduled.py
from src.infrastructure.selection.configured_selection import ConfiguredMatrixSelection


async def run_scheduled(container, scheduled_matrix_names: str) -> int:
    selection = ConfiguredMatrixSelection(names=scheduled_matrix_names)
    container.set_matrix_selection(selection)
    job = await container.run_deployment(trigger="scheduled")
    return 0 if job.status in ("completed", "partial") else 1
```

- [ ] **Шаг 3: Переписать main.py**

```python
# main.py
import argparse
import asyncio
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
    # apply log level
    import logging
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
```

- [ ] **Шаг 4: Smoke-test CLI help**

Запуск: `uv run python main.py --help`  
Ожидается: вывод subcommands `run`, `sync`

---

### Задача 16: Удаление legacy-кода

- [ ] **Шаг 1: Удалить устаревшие директории и файлы**

```powershell
Remove-Item -Recurse -Force src/controllers
Remove-Item -Recurse -Force src/application/repositories
Remove-Item -Recurse -Force src/application/services
Remove-Item -Recurse -Force src/application/exceptions.py
Remove-Item -Recurse -Force src/domain/entites
Remove-Item -Recurse -Force src/infrastructure/adapters
Remove-Item -Recurse -Force src/infrastructure/repositories
Remove-Item -Force src/infrastructure/interactive_matrices_selector.py
Remove-Item -Force src/infrastructure/google_sheets_api_client.py
Remove-Item -Force src/infrastructure/logger.py
Remove-Item -Force src/application/use_cases/select_and_upload_matrices.py
Remove-Item -Force src/application/use_cases/upload_machine_matrix.py
Remove-Item -Force src/application/use_cases/sync/sync_products_cache.py
Remove-Item -Force src/application/use_cases/sync/sync_matrices_cache.py
Remove-Item -Force src/application/use_cases/sync/sync_vending_machines_cache.py
```

> Удалять только после того, как новые файлы на месте и импорты обновлены.

- [ ] **Шаг 2: Проверить отсутствие старых импортов**

Запуск: `rg "domain\.entites|application\.repositories|application\.exceptions|controllers\." src tests main.py`  
Ожидается: нет совпадений

---

### Задача 17: Финальная верификация

- [ ] **Шаг 1: Полный прогон тестов**

Запуск: `uv run pytest -q`  
Ожидается: 0 failed

- [ ] **Шаг 2: Проверка CLI**

Запуск: `uv run python main.py run --help`  
Ожидается: `--mode {interactive,scheduled}`

- [ ] **Шаг 3: Ручной smoke (при наличии .env)**

Запуск: `uv run python main.py sync`  
Ожидается: sync завершается без traceback (при валидном `.env` и Google credentials)

---

## Само-ревью покрытия спека

| Требование спека | Задача |
|------------------|--------|
| Структура domain/application/infrastructure/interfaces/bootstrap | 1–16 |
| entites → entities | 2–3, 11–12, 16 |
| RunDeploymentJob pipeline | 10, 14–15 |
| Interactive + scheduled modes | 13, 15 |
| JobRun + in-memory repo | 3, 6, 10 |
| SQLite stub | 6 |
| HTTP stub | 15 |
| GetVendingMachinesPort | 5, 11 |
| MatrixValidator enabled by default | 7, 14 |
| pydantic-settings | 1, 14 |
| kit_vending as-is | 11 |
| TDD P0+P1 | 4, 7–10 |
| Big bang cleanup | 16 |
| Exit codes | 15 |
| Критерии готовности | 17 |

Пробелов нет.

---
