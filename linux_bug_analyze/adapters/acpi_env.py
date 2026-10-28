"""ACPI environment-classification run (console.log + receipt.json) -> CPU-set facts.

Migrated from experiments/case_taxonomy/acpi_env_classification_20261027/analyze.py (observe and
the facts built in main). Expects the registered PID1 'LBA key=value' lines and QMP receipt.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

VERSION = "acpi_env_console/1"


def _cpulist(text: str | None) -> list[int]:
    out: list[int] = []
    for part in (text or "").split(","):
        if not part or part.startswith("ERR"):
            continue
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return out


def adapt(spec: Mapping[str, Any]) -> dict[str, Any]:
    run = Path(spec["run_dir"])
    receipt = json.loads((run / "receipt.json").read_text())
    text = (run / "console.log").read_bytes().decode("utf-8", "replace")
    lba = dict(re.findall(r"^LBA (\w+)=(.*?)\r?$", text, re.M))
    hyp = re.search(r"Hypervisor detected: (\S+)", text)
    headers = sorted(set(re.findall(r"ACPI: (FACP|APIC) 0x[0-9A-F]+ [0-9A-F]+ \((v\d+) BOCHS", text)))
    boot = {k: _cpulist(lba.get("boot_" + k)) for k in ("possible", "present", "online")}
    final = {k: _cpulist(lba.get("final_" + k)) for k in ("possible", "present", "online")}
    values = {"supported_context": bool(receipt["ready_seen"] and receipt["done_seen"] and receipt["returncode"] == 0),
              "qemu_guest_with_legacy_slots": ("APIC", "v03") in [tuple(h) for h in headers],
              "required_possible_count": int(spec["required_possible_count"]),
              "boot_possible_count": len(boot["possible"]),
              "online_outside_boot_possible": sorted(set(final["online"]) - set(boot["possible"]))}
    return {"values": values, "types": {},
            "observation": {"hypervisor": hyp.group(1) if hyp else None, "boot": boot, "final": final,
                            "firmware_headers": headers, "console_sha256": receipt["console_sha256"],
                            "image_sha256": receipt["image_sha256"]}}
