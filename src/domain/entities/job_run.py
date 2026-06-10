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
