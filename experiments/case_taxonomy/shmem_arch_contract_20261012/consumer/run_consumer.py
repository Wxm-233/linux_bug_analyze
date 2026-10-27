"""Build/run the official historical XArray shim using authenticated inputs.

Example (only after authenticating these values in the linked geometry file):
  python3 run_consumer.py --geometry-source ../geometry.json --chunk-shift 6 \
    --profile x86_64_4k=9 --profile arm64_4k=9 --profile arm64_64k=13

The supplied profile values are recorded, not inferred by this script. The
geometry source is preserved with a SHA-256 link for independent reconciliation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent
HARNESS = BASE / "source/tools/testing/radix-tree"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--geometry-source", type=Path, required=True)
    parser.add_argument("--chunk-shift", type=int, required=True)
    parser.add_argument("--profile", action="append", required=True)
    args = parser.parse_args()
    geometry = args.geometry_source.resolve()
    geometry_bytes = geometry.read_bytes()
    profiles = []
    for item in args.profile:
        label, value = item.split("=", 1)
        profiles.append((label, int(value)))
    geometry_records = {item["profile"]: item for item in json.loads(geometry_bytes)}
    bindings = []
    for label, order in profiles:
        record = geometry_records[label]
        if record["geometry"]["HPAGE_PMD_ORDER"] != order:
            raise SystemExit(f"{label}: order does not match compiled geometry")
        if record["geometry"]["XA_CHUNK_SHIFT"] != args.chunk_shift:
            raise SystemExit(f"{label}: chunk does not match compiled geometry")
        bindings.append({"profile": label, "revision": record["revision"],
                         "input_order": order, "source_field": "geometry.HPAGE_PMD_ORDER",
                         "geometry_execution": record["execution"]})
    # Deliberately confined to this frozen two-order consumer experiment.
    if args.chunk_shift != 6 or any(order not in (9, 13) for _, order in profiles):
        raise SystemExit("out of frozen scope: expected authenticated chunk6 and order9/13")
    manifest = json.loads((BASE / "source_manifest.json").read_text())
    if not manifest["parent_fixed_identity"]["lib/xarray.c"]["identical"]:
        raise SystemExit("parent/fixed consumer differs; require separate builds")
    probe_source = BASE / "consumer_probe.c"
    probe_copy = HARNESS / "consumer_probe.c"
    if probe_copy.read_bytes() != probe_source.read_bytes():
        shutil.copyfile(probe_source, probe_copy)
    commands = [
        ["make", "generated/map-shift.h", "generated/bit-length.h", "SHIFT=6"],
        ["make", "-f", "Makefile", "-f", str(BASE / "consumer_probe.mk"),
         "consumer-probe", "SHIFT=6"],
    ]
    build_records = []
    for index, command in enumerate(commands):
        completed = subprocess.run(command, cwd=HARNESS, text=True, capture_output=True)
        (BASE / f"run_build_{index}.stdout.log").write_text(completed.stdout)
        (BASE / f"run_build_{index}.stderr.log").write_text(completed.stderr)
        build_records.append({"command": command, "cwd": str(HARNESS),
                              "returncode": completed.returncode})
        if completed.returncode:
            raise SystemExit(f"build failed; inspect run_build_{index}.stderr.log")
    results = []
    for label, order in profiles:
        command = [str(HARNESS / "consumer-probe"), str(order)]
        completed = subprocess.run(command, cwd=HARNESS, text=True, capture_output=True)
        (BASE / f"{label}.stdout.log").write_text(completed.stdout)
        (BASE / f"{label}.stderr.log").write_text(completed.stderr)
        observed = json.loads(completed.stdout)
        warn_lines = [line for line in completed.stderr.splitlines()
                      if "assertion failed at" in line and "lib/xarray.c:" in line]
        expected_error = -12 if order == 13 else 0
        expected_warns = 1 if order == 13 else 0
        checks = {
            "original_consumer_error": observed["xas_error"] == expected_error,
            "original_consumer_warn": len(warn_lines) == expected_warns,
            "new_order_zero": observed["new_order"] == 0 and observed["xa_shift"] == 0,
            "chunk_matches_geometry": observed["xa_chunk_shift"] == args.chunk_shift,
            "allocation_path": ((observed["nodes_after_alloc"] > observed["nodes_before"])
                                if order == 9 else
                                (observed["nodes_after_alloc"] == observed["nodes_before"])),
            "cleanup": observed["nodes_after_cleanup"] == observed["nodes_before"],
            "process_exit": completed.returncode == 0,
            "stderr_only_expected_warn": len(completed.stderr.splitlines()) == expected_warns,
        }
        results.append({"profile": label, "input_order": order, "command": command,
                        "returncode": completed.returncode, "observed": observed,
                        "original_warn_lines": warn_lines, "checks": checks,
                        "passed": all(checks.values())})
    report = {
        "fix": manifest["fix"], "parent": manifest["parent"],
        "consumer_blob": manifest["parent_fixed_identity"]["lib/xarray.c"],
        "geometry_source": str(geometry),
        "geometry_sha256": hashlib.sha256(geometry_bytes).hexdigest(),
        "input_binding": bindings,
        "evidence_level": "unchanged historical lib/xarray.c in official userspace test shim with liburcu",
        "oracle": "original consumer WARN xa_shift + 2*XA_CHUNK_SHIFT < order and xas_error; not MAX_XAS_ORDER gate",
        "compiler": subprocess.check_output(["gcc", "--version"], text=True).splitlines()[0],
        "build": build_records, "results": results,
        "passed": all(item["passed"] for item in results),
        "limits": ["no historical kernel boot", "no 512MB folio allocation or shmem selection call",
                   "no actual xas_split commit", "single-caller experiment, not concurrency validation",
                   "official tools shim hardcodes PAGE_SHIFT=12; only certified input order carries ARM64 page geometry"],
    }
    (BASE / "consumer_result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"profiles": len(results), "passed": report["passed"]}))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
