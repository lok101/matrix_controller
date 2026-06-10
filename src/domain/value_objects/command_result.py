from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class CommandResult:
    success: bool
    step: Literal["send_command", "verify_status"]
    message: str
    attempts: int
