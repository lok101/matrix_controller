import asyncio
import time
from collections import deque
from typing import Deque


class RateLimiter:
    """
    Упрощенный ограничитель запросов для одного API с одним набором лимитов.
    """

    def __init__(self, max_requests: int, time_window: float = 1.0):
        """
        Args:
            max_requests: Максимальное количество запросов в time_window секунд
            time_window: Временное окно в секундах
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: Deque[float] = deque()
        self._lock = asyncio.Lock()

    async def wait(self):
        """
        Асинхронно ожидает, когда можно будет выполнить следующий запрос.
        """
        async with self._lock:
            current_time = time.monotonic()

            # Удаляем старые запросы
            while self.requests and self.requests[0] <= current_time - self.time_window:
                self.requests.popleft()

            if len(self.requests) < self.max_requests:
                # Можно выполнить запрос сразу
                self.requests.append(current_time)
                return

            # Нужно подождать
            wait_until = self.requests[0] + self.time_window
            wait_time = max(0.0, wait_until - current_time)

            # Обновляем очередь
            self.requests.append(wait_until)
            self.requests.popleft()

            if wait_time > 0:
                await asyncio.sleep(wait_time)


def rate_limit(max_requests: int, time_window: float = 1.0):
    """
    Декоратор класса для автоматического ограничения запросов к API.

    Args:
        max_requests: Максимальное количество запросов в time_window секунд
        time_window: Временное окно в секундах
    """

    def decorator(cls):
        # Создаем экземпляр ограничителя для класса
        limiter = RateLimiter(max_requests, time_window)

        # Обходим все методы класса
        for attr_name in dir(cls):
            if attr_name.startswith('_'):
                continue

            attr = getattr(cls, attr_name)
            # Если это асинхронный метод, оборачиваем его
            if callable(attr) and asyncio.iscoroutinefunction(attr):
                setattr(cls, attr_name, _wrap_method(attr, limiter))

        # Добавляем ограничитель как атрибут класса
        cls._limiter = limiter
        return cls

    return decorator


def _wrap_method(method, limiter):
    """
    Обертка для асинхронного метода, добавляющая ожидание ограничителя.
    """

    async def wrapper(self, *args, **kwargs):
        await limiter.wait()
        return await method(self, *args, **kwargs)

    return wrapper


def api_method(max_requests: int = None, time_window: float = 1.0):
    """
    Декоратор для отдельных методов API.
    Если параметры не указаны, используются параметры из декоратора класса.
    """

    def decorator(func):
        async def wrapper(self, *args, **kwargs):
            limiter = getattr(self, '_limiter', None)
            if limiter is None:
                if max_requests is None:
                    raise ValueError(
                        "Для метода нужно указать max_requests или использовать "
                        "декоратор @rate_limit на классе"
                    )
                limiter = RateLimiter(max_requests, time_window)

            await limiter.wait()
            return await func(self, *args, **kwargs)

        return wrapper

    return decorator
