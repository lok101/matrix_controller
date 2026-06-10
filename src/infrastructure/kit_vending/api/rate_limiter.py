from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Deque


class GlobalBackoff:
    """Глобальная блокировка при превышении лимита API (код TOO_MANY_REQUEST)."""

    def __init__(self, timeout: float = 60.0) -> None:
        self._timeout = timeout
        self._event: asyncio.Event | None = None
        self._lock: asyncio.Lock | None = None
        self._backoff_task: asyncio.Task | None = None

    def _ensure_initialized(self) -> None:
        if self._event is None:
            self._event = asyncio.Event()
            self._event.set()
        if self._lock is None:
            self._lock = asyncio.Lock()

    async def wait_if_blocked(self) -> None:
        self._ensure_initialized()
        await self._event.wait()

    async def trigger_backoff(self) -> None:
        self._ensure_initialized()

        async with self._lock:
            if self._event.is_set():
                self._event.clear()
                self._backoff_task = asyncio.create_task(self._backoff_timer())

        await self._event.wait()

    async def _backoff_timer(self) -> None:
        try:
            await asyncio.sleep(self._timeout)
        finally:
            self._event.set()
            self._backoff_task = None

    def is_blocked(self) -> bool:
        if self._event is None:
            return False
        return not self._event.is_set()


class RateLimiter:
    """Ограничитель запросов для одного API с одним набором лимитов."""

    def __init__(self, max_requests: int, time_window: float = 1.0) -> None:
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: Deque[float] = deque()
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self._lock:
            current_time = time.monotonic()

            while self.requests and self.requests[0] <= current_time - self.time_window:
                self.requests.popleft()

            if len(self.requests) < self.max_requests:
                self.requests.append(current_time)
                return

            wait_until = self.requests[0] + self.time_window
            wait_time = max(0.0, wait_until - current_time)

            self.requests.append(wait_until)
            self.requests.popleft()

            if wait_time > 0:
                await asyncio.sleep(wait_time)
