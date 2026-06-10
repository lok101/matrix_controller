from __future__ import annotations

import re

from src.infrastructure.kit_vending.api.enums import VendingMachineStatus


def extract_statuses(statuses_str: str) -> list[VendingMachineStatus]:
    result: list[VendingMachineStatus] = []

    if statuses_str:
        for status in statuses_str.split(","):
            try:
                result.append(VendingMachineStatus(int(status)))
            except ValueError:
                continue

    return result


def extract_vending_machine_id(vending_machine_name: str) -> int | None:
    match = re.search(r"\[(\d+)\]", vending_machine_name)
    if match:
        return int(match.group(1))
    return None
