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
