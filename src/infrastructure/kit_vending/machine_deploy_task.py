from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from src.domain.entities.vending_machine import VendingMachine
from src.infrastructure.kit_vending.api.enums import VendingMachineStatus

MachineDeployPhase = Literal["pending_load", "loaded", "pending_apply", "applied", "failed"]


def is_load_confirmed(statuses: list[VendingMachineStatus]) -> bool:
    return VendingMachineStatus.MATRIX_LOADED in statuses


def is_apply_confirmed(statuses: list[VendingMachineStatus]) -> bool:
    return bool(statuses) and VendingMachineStatus.MATRIX_LOADED not in statuses


@dataclass
class MachineDeployTask:
    machine: VendingMachine
    matrix_name: str
    phase: MachineDeployPhase = "pending_load"
    phase_started_at: datetime = field(default_factory=datetime.now)
    last_seen_statuses: list[VendingMachineStatus] = field(default_factory=list)
    failure_step: str | None = None
    failure_message: str | None = None

