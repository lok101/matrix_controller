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
