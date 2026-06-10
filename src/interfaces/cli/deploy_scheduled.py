from __future__ import annotations

from src.bootstrap.container import Container


async def deploy_scheduled(container: Container, scheduled_matrix_names: str) -> int:
    container.configure_scheduled_selection(scheduled_matrix_names)
    job = await container.run_deployment(trigger="scheduled")
    return 0 if job.status in ("completed", "partial") else 1
