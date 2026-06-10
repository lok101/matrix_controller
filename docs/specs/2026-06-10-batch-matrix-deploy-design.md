# Batch-deploy матриц с опросом статусов Kit API

**Дата:** 2026-06-10  
**Статус:** на проверке  
**Контекст:** сбой deploy 14:48 — LOAD прошёл, APPLY не снял статус 21; Kit ненадёжен, лимиты API ~10 req/min

## Цель

Повысить надёжность загрузки и применения матриц на торговых аппаратах при нестабильном Kit Vending API: меньше запросов к API, раннее обнаружение готовности аппарата, независимые таймауты на аппарат.

## Диагностика инцидента (2026-06-10, 14:48)

Запуск для `[512] - Общежитие УРФУ`:

1. `LOAD_MATRIX` → успех (статус 21 появился, иначе APPLY не стартовал бы).
2. `APPLY_MATRIX` × 3 цикла по 120 сек → статус 21 не снялся.
3. В UI Kit статус «Товарная матрица загружена» висит; вручную снимается с задержкой и не всегда.

**Вывод:** предикаты статусов корректны (`MATRIX_LOADED = 21`). Проблема — модель ожидания (слепой sleep + одна проверка) и лимиты API, а не перепутанные коды.

| Шаг | Предикат | Смысл |
|-----|----------|-------|
| Загрузка | `21 in statuses` | «Товарная матрица загружена» |
| Применение | `21 not in statuses` | статус снят → матрица применена |

## Выбранный подход

**Вариант B+ (batch polling + per-machine deadline):**

- Один запрос `GetVMStates` проверяет **все** ожидающие аппараты за раз.
- Опрос каждые `MATRIX_STATUS_POLL_INTERVAL` секунд вместо слепого sleep.
- Таймаут считается **отдельно для каждого аппарата**; зависший аппарат не блокирует остальных.
- Команды `send_command` отправляются последовательно с троттлингом.
- Матрицы обрабатываются последовательно (без `asyncio.gather`).

### Отклонённые альтернативы

| Вариант | Почему нет |
|---------|------------|
| Только увеличить таймауты | Слепое ожидание; лишние повторные команды |
| Per-machine polling (N запросов) | Превышает лимит API при нескольких аппаратах |
| Жёсткий «все или никто» | Один зависший аппарат блокирует весь deploy |

## Архитектура

### Новый компонент: `BatchMatrixDeployCoordinator`

Расположение: `src/infrastructure/kit_vending/batch_matrix_deploy_coordinator.py`

Ответственность: фазовый pipeline для всего deploy-job (все выбранные матрицы).

```
DeployMatricesUseCase
    └── BatchMatrixDeployCoordinator.deploy(matrices_with_machines)
            ├── phase_prepare_and_send_load()
            ├── phase_poll_load()
            ├── phase_send_apply()
            └── phase_poll_apply()
```

`MatrixCommandWorkflow` сохраняется для unit-тестов предикатов и как fallback не используется в production-path после миграции.

### Модель состояния аппарата

```python
@dataclass
class MachineDeployTask:
    machine: VendingMachine
    matrix_name: str
    phase: Literal["pending_load", "loaded", "pending_apply", "applied", "failed"]
    phase_started_at: datetime
    last_seen_statuses: list[VendingMachineStatus]
    failure_step: str | None
    failure_message: str | None
```

Ключ в словаре задач: `machine.kit_id.value`.

### Фазы pipeline

#### Фаза 0 — подготовка (последовательно, с троттлингом команд)

Для каждой матрицы (по порядку из `selected_matrix_names`):

1. `upload_matrix` → `MatrixKitId`
2. Для каждого аппарата матрицы:
   - `bound_matrix_to_vending_machine`
   - `send_command LOAD_MATRIX`
   - создать `MachineDeployTask(phase="pending_load")`
   - пауза `MATRIX_COMMAND_SEND_DELAY` сек между `send_command`

Ошибка bind/send → задача сразу `phase="failed"`, остальные аппараты продолжают.

#### Фаза 1 — batch-poll загрузки

Пока есть задачи в `pending_load`:

1. `await asyncio.sleep(MATRIX_STATUS_POLL_INTERVAL)`
2. Один вызов `get_vending_machine_states()`
3. Для каждого `pending_load`:
   - если `21 in statuses` → `phase="loaded"`, лог успеха с elapsed
   - если `now - phase_started_at > MATRIX_LOAD_TIMEOUT` → `phase="failed"`, лог с `last_seen_statuses`
   - иначе обновить `last_seen_statuses`, продолжить ждать

При ошибке API на poll — retry poll (не сбрасывать таймеры аппаратов), с учётом rate limiter клиента.

#### Фаза 2 — отправка APPLY

Для каждой задачи в `phase="loaded"`:

1. `send_command APPLY_MATRIX`
2. `phase="pending_apply"`, обновить `phase_started_at`
3. пауза `MATRIX_COMMAND_SEND_DELAY`

#### Фаза 3 — batch-poll применения

Аналогично фазе 1, предикат: `21 not in statuses` → `phase="applied"`.

Таймаут: `MATRIX_APPLY_TIMEOUT` per-machine.

При провале apply — `phase="failed"`, остальные продолжают.

#### Итог

Координатор возвращает структуру результатов по матрицам: `(success_count, failure_count)` — совместимо с текущим `DeployMatricesUseCase`.

### Схема потока

```
[Матрица 1] upload → bind+LOAD × M₁ ─┐
[Матрица 2] upload → bind+LOAD × M₂ ─┼→ poll GetVMStates (все pending_load)
                                     │       ↓ per-machine deadline
                                     ├→ APPLY × loaded
                                     └→ poll GetVMStates (все pending_apply)
                                             ↓
                                        итог по матрицам
```

## Ограничения Kit API

- Заявленный лимит: ~10 req/min; на практике ощущается ниже.
- `GetVMStates` — один запрос на все аппараты компании (используем для batch-poll).
- `send_command` — отдельный запрос на аппарат; троттлинг обязателен.

### Бюджет запросов (пример: 5 аппаратов, 5 мин ожидания, poll 15 сек)

| Тип | Количество |
|-----|------------|
| `GetVMStates` (load + apply) | ~40 (20+20) |
| `send_command` | 10 (5 load + 5 apply) |
| `bound_matrix` + `create_matrix` | 5 + 5 |

Polling: ~4 req/min — в пределах лимита. Команды размазаны по времени отправки.

## Конфигурация

Новые/изменённые переменные в `Settings` и `.env.example`:

| Переменная | Default | Описание |
|------------|---------|----------|
| `MATRIX_LOAD_TIMEOUT` | `300` | Per-machine deadline фазы load (сек) |
| `MATRIX_APPLY_TIMEOUT` | `300` | Per-machine deadline фазы apply (сек) |
| `MATRIX_STATUS_POLL_INTERVAL` | `15` | Интервал batch-poll (сек) |
| `MATRIX_COMMAND_SEND_DELAY` | `7` | Пауза между `send_command` (сек) |

Существующие `max_retry_attempts` в `MatrixCommandWorkflow` для production-path не используются — retry реализуется повторной отправкой команды при новом цикле фазы (опционально, v1: без повторной отправки — только poll до deadline; повтор send только если явно добавим `MATRIX_MAX_COMMAND_RETRIES`).

**Решение v1:** одна отправка команды на фазу + poll до per-machine deadline. Повторная отправка не делается — при timeout аппарат помечается `failed`. Retry команд — вне скоупа v1.

## Обработка ошибок

| Ситуация | Поведение |
|----------|-----------|
| Bind failed | Аппарат → `failed`, остальные продолжают |
| Load timeout (per-machine) | Аппарат → `failed`, loaded-аппараты идут в apply |
| Apply timeout | Аппарат → `failed` |
| API error на poll | Retry poll, таймеры аппаратов не сбрасываются |
| API error на send (не rate limit) | Аппарат → `failed` |
| Rate limit (27) | Retry через rate limiter клиента |
| Аппарат не найден в `GetVMStates` | Считать статус пустым `[]`, лог WARNING |

Частичный успех матрицы сохраняется: `success_count > 0 and failure_count > 0` → warning, как сейчас.

## Логирование

Обязательно логировать **фактические статусы** при каждом poll (DEBUG) и при deadline (WARNING):

```
INFO  Deploy: фаза load, pending=5
DEBUG Poll load #4 (60s): [512]=[21,1] ok | [505]=[1] waiting | [503]=not_found
INFO  [512] load подтверждён за 87 сек, статусы: [21, 1]
WARNING [505] load timeout 300 сек, последние статусы: [1]
INFO  Deploy: фаза apply, pending=4
```

## Изменения в существующем коде

| Файл | Изменение |
|------|-----------|
| `deploy_matrices.py` | Убрать `asyncio.gather`; единственная точка входа — координатор |
| `upload_and_apply_matrix.py` | Удалить per-machine цикл; координатор забирает bind/load/apply |
| `container.py` | Wire координатора, новые settings |
| `settings.py` | Новые env-поля |
| `.env.example` | Документация новых переменных |
| `matrix_command_workflow.py` | Без изменений (тесты) |

## Тестирование

### Unit

- `BatchMatrixDeployCoordinator`:
  - batch poll: 3 аппарата, статусы приходят в разное время → per-machine deadline независимы
  - один аппарат timeout → остальные переходят в apply
  - один `GetVMStates` на несколько аппаратов (mock call count = 1 per poll)
  - предикаты load/apply без изменений

### Integration (mock Kit client)

- 5 аппаратов, статус 21 появляется на 2-м и 4-м poll → success без полного timeout
- Rate limit на poll → retry, таймеры не сбрасываются

## Критерии успеха

1. Deploy 14:48-сценария (один аппарат, медленный apply) — apply успевает в пределах `MATRIX_APPLY_TIMEOUT` с polling.
2. Deploy 5 матриц — нет каскада rate limit (как утром 09:55).
3. Зависший аппарат не блокирует apply для остальных.
4. В логах видны фактические статусы при провале.

## Вне скоупа

- Изменение предикатов статусов (21 / not 21).
- Параллельная обработка матриц через `asyncio.gather`.
- Автоматическая «лечебная» перезагрузка аппарата при зависшем статусе.
- UI/уведомления о частичном провале.
