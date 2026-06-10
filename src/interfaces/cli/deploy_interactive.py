from __future__ import annotations

from src.bootstrap.container import Container


async def deploy_interactive(container: Container) -> int:
    container.configure_interactive_selection()
    job = await container.run_deployment(trigger="interactive")
    return 0 if job.status in ("completed", "partial") else 1
