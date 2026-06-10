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
