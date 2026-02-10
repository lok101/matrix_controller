import logging
import os
import sys
from datetime import datetime

from tzlocal import get_localzone

from src.domain.project_timezone import PROJECT_TIMEZONE


class FlushingStreamHandler(logging.StreamHandler):
    """StreamHandler, который автоматически делает flush после каждого сообщения."""

    def emit(self, record) -> None:
        super().emit(record)
        self.flush()


def configure_logging(log_dir: str = "logs") -> logging.Logger:
    os.makedirs(log_dir, exist_ok=True)

    local_tz = get_localzone()
    now = datetime.now(PROJECT_TIMEZONE)
    log_filename = f"{now.astimezone(local_tz).strftime('%Y-%m-%d')}.log"
    log_path = os.path.join(log_dir, log_filename)

    root_logger: logging.Logger = logging.getLogger()

    if root_logger.handlers:
        return root_logger

    root_logger.setLevel(logging.DEBUG)

    console_handler = FlushingStreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    return root_logger
