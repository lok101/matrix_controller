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
