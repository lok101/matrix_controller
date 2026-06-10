import logging
from dataclasses import dataclass
from datetime import datetime

from beartype import beartype

from src.application.use_cases.deploy.deploy_matrices import DeployMatricesUseCase
from src.application.use_cases.sync.sync_all_caches import SyncAllCachesUseCase
from src.domain.entities.job_run import JobRun, JobRunStatus, JobRunTrigger
from src.domain.exceptions import SynchronizationError
from src.domain.ports.matrix_selection import MatrixSelectionPort
from src.domain.project_timezone import PROJECT_TIMEZONE
from src.domain.repositories.job_run_repository import JobRunRepository
from src.domain.repositories.matrix_repository import MatrixRepository
from src.domain.value_objects.ids.job_run_id import JobRunId

logger = logging.getLogger(__name__)


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class RunDeploymentJobUseCase:
    job_run_repository: JobRunRepository
    sync_all_caches: SyncAllCachesUseCase
    matrix_selection: MatrixSelectionPort
    matrix_repository: MatrixRepository
    deploy_matrices: DeployMatricesUseCase

    async def execute(self, trigger: JobRunTrigger) -> JobRun:
        started_at = datetime.now(tz=PROJECT_TIMEZONE)
        job_id = JobRunId.generate()
        job_run = JobRun(
            id=job_id,
            trigger=trigger,
            status="running",
            started_at=started_at,
            finished_at=None,
            matrices_total=0,
            matrices_success=0,
            matrices_failed=0,
            error_summary=None,
        )
        self.job_run_repository.create(job_run)

        try:
            await self.sync_all_caches.execute()
        except SynchronizationError as exc:
            failed = self._finalize(
                job_run,
                status="failed",
                matrices_total=0,
                matrices_success=0,
                matrices_failed=0,
                error_summary=str(exc),
            )
            return failed

        selected_names = self.matrix_selection.select(self.matrix_repository.get_all())
        if not selected_names:
            return self._finalize(
                job_run,
                status="completed",
                matrices_total=0,
                matrices_success=0,
                matrices_failed=0,
                error_summary=None,
            )

        try:
            success, failed, skipped = await self.deploy_matrices.execute(
                selected_names, datetime.now(tz=PROJECT_TIMEZONE)
            )
        except Exception as exc:
            return self._finalize(
                job_run,
                status="failed",
                matrices_total=len(selected_names),
                matrices_success=0,
                matrices_failed=len(selected_names),
                error_summary=str(exc),
            )

        total = len(selected_names)
        if failed == 0 and skipped == 0:
            status = "completed"
        elif success == 0:
            status = "failed"
        else:
            status = "partial"

        summary_parts: list[str] = []
        if failed:
            summary_parts.append(f"Ошибок: {failed} из {total}")
        if skipped:
            summary_parts.append(f"Пропущено: {skipped} из {total}")
        error_summary = "; ".join(summary_parts) if summary_parts else None

        return self._finalize(
            job_run,
            status=status,
            matrices_total=total,
            matrices_success=success,
            matrices_failed=failed,
            error_summary=error_summary,
        )

    def _finalize(
        self,
        job_run: JobRun,
        *,
        status: JobRunStatus,
        matrices_total: int,
        matrices_success: int,
        matrices_failed: int,
        error_summary: str | None,
    ) -> JobRun:
        finished = JobRun(
            id=job_run.id,
            trigger=job_run.trigger,
            status=status,
            started_at=job_run.started_at,
            finished_at=datetime.now(tz=PROJECT_TIMEZONE),
            matrices_total=matrices_total,
            matrices_success=matrices_success,
            matrices_failed=matrices_failed,
            error_summary=error_summary,
        )
        self.job_run_repository.update(finished)
        logger.info(
            "Job %s завершён: status=%s, success=%s, failed=%s, trigger=%s",
            finished.id.value,
            finished.status,
            finished.matrices_success,
            finished.matrices_failed,
            finished.trigger,
        )
        return finished
