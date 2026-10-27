"""Reproduce two reviewed scalar expressions on little- and big-endian CPUs.

Reads only the listed historical Linux files; compiles the reduced C projection
in a temporary directory. No new candidate discovery or external model call.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


HCI_OLD = "c30b93eade2ad1d77695669f25ddeb3833588d3b^"
HCI_FIX = "c30b93eade2ad1d77695669f25ddeb3833588d3b"
MPT_OLD = "494f401bcd07d6b39f49f114e4eaa788842f16fe^"
MPT_FIX = "494f401bcd07d6b39f49f114e4eaa788842f16fe"

# Each anchor is at the specified revision; it must not silently float to HEAD.
SOURCE_SPECS = [
    ("hci_old_driver", HCI_OLD, "drivers/bluetooth/hci_ll.c",
     {"opcode": [60], "host_speed": [670, 702, 703, 704, 705, 706, 707],
      "old_command": [712, 713, 714, 716], "compatible": list(range(760, 772))}),
    ("hci_fix_driver", HCI_FIX, "drivers/bluetooth/hci_ll.c",
     {"fixed_command": list(range(709, 719))}),
    ("hci_old_request", HCI_OLD, "net/bluetooth/hci_request.c",
     {"sync_to_request": [122, 123, 134, 187, 188, 190, 323, 324, 337],
      "payload_copy": list(range(296, 313))}),
    ("hci_old_skb_copy", HCI_OLD, "include/linux/skbuff.h",
     {"raw_copy": list(range(2046, 2054))}),
    ("hci_old_config", HCI_OLD, "drivers/bluetooth/Kconfig",
     {"supported_config": list(range(145, 153))}),
    ("mpt_old_driver", MPT_OLD, "drivers/scsi/mpt3sas/mpt3sas_base.c",
     {"old_condition": list(range(1735, 1753)),
      "consumer": list(range(1788, 1802))}),
    ("mpt_fix_driver", MPT_FIX, "drivers/scsi/mpt3sas/mpt3sas_base.c",
     {"fixed_condition": list(range(1735, 1753))}),
    ("mpt_old_constant", MPT_OLD, "drivers/scsi/mpt3sas/mpt3sas_base.h",
     {"page_constant": [144]}),
    ("mpt_old_length_provider", MPT_OLD, "include/scsi/scsi_cmnd.h",
     {"length_provider": [188, 189, 190]}),
    ("mpt_old_config", MPT_OLD, "drivers/scsi/mpt3sas/Kconfig",
     {"supported_config": list(range(43, 50))}),
]


def checked_output(argv: list[str], *, cwd: Path | None = None) -> str:
    process = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                             check=True)
    return process.stdout


def git_sources(linux_dir: Path) -> list[dict]:
    records = []
    for label, revision, path, anchors in SOURCE_SPECS:
        source = checked_output(["git", "show", f"{revision}:{path}"], cwd=linux_dir)
        lines = source.splitlines()
        snippets = {}
        for name, numbers in anchors.items():
            if max(numbers) > len(lines):
                raise ValueError(f"line anchor absent: {label}:{name}")
            snippets[name] = [{"line": n, "text": lines[n - 1]} for n in numbers]
        records.append({
            "label": label, "revision": revision, "path": path,
            "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            "anchors": snippets,
        })
    return records


def parse_probe(stdout: str) -> dict:
    rows = list(csv.reader(stdout.splitlines()))
    if len(rows) != 14 or rows[0][0] != "META":
        raise ValueError("unexpected probe row count or header")
    result = {"host_endian": rows[0][1], "u32_bytes": int(rows[0][2]),
              "hci": [], "mpt": [], "raw_stdout": stdout}
    for row in rows[1:]:
        if row[0] == "HCI":
            result["hci"].append({
                "speed": int(row[1]), "old_payload_hex": row[2],
                "fixed_payload_hex": row[3], "contract_payload_hex": row[4],
                "host_speed_for_serial_api": int(row[5]),
            })
        elif row[0] == "MPT":
            result["mpt"].append({
                "host_length_bytes": int(row[1]), "sge_count": int(row[2]),
                "old_compared_numeric_value": int(row[3]),
                "old_build_prp": bool(int(row[4])),
                "fixed_build_prp": bool(int(row[5])),
            })
        else:
            raise ValueError(f"unexpected probe record: {row[0]}")
    if len(result["hci"]) != 3 or len(result["mpt"]) != 10:
        raise ValueError("missing probe case")
    return result


def run_probe(source_path: Path) -> dict:
    result = {}
    with tempfile.TemporaryDirectory(prefix="outbound-scalar-") as temp_name:
        temp = Path(temp_name)
        for label, compiler, launcher, expected_endian in [
            ("x86_64", "gcc", [], "little"),
            ("s390x", "s390x-linux-gnu-gcc", ["qemu-s390x"], "big"),
        ]:
            executable = temp / f"probe-{label}"
            argv = [compiler, "-static", "-std=c11", "-O2", "-Wall", "-Wextra",
                    "-Werror", str(source_path), "-o", str(executable)]
            checked_output(argv)
            parsed = parse_probe(checked_output(launcher + [str(executable)]))
            if parsed["host_endian"] != expected_endian or parsed["u32_bytes"] != 4:
                raise ValueError(f"unexpected {label} target ABI")
            parsed["compiler"] = compiler
            parsed["compiler_version"] = checked_output([compiler, "--version"]).splitlines()[0]
            parsed["launcher"] = launcher or ["native"]
            result[label] = parsed
    return result


def validate_runs(runs: dict) -> list[str]:
    checks = []
    le, be = runs["x86_64"], runs["s390x"]
    for platform, run in runs.items():
        for case in run["hci"]:
            assert case["fixed_payload_hex"] == case["contract_payload_hex"]
            assert case["host_speed_for_serial_api"] == case["speed"]
        for case in run["mpt"]:
            length, count = case["host_length_bytes"], case["sge_count"]
            assert case["fixed_build_prp"] == (not (length <= 16384 and count <= 2))
        checks.append(f"{platform}: fixed HCI bytes and host-length threshold conform")
    assert all(c["old_payload_hex"] == c["fixed_payload_hex"] for c in le["hci"])
    assert all(c["old_build_prp"] == c["fixed_build_prp"] for c in le["mpt"])
    checks.append("little-endian old and fixed are equal for all selected inputs")
    assert all(c["old_payload_hex"] != c["fixed_payload_hex"]
               for c in be["hci"] if c["speed"] != 0)
    assert next(c for c in be["hci"] if c["speed"] == 0)["old_payload_hex"] == "00000000"
    checks.append("big-endian nonzero HCI values differ; zero is a normal counterexample")
    mpt_be = {(c["host_length_bytes"], c["sge_count"]): c for c in be["mpt"]}
    for length in (4096, 16384, 65536):
        assert mpt_be[(length, 2)]["old_build_prp"] != mpt_be[(length, 2)]["fixed_build_prp"]
    assert all(c["old_build_prp"] == c["fixed_build_prp"]
               for c in be["mpt"] if c["sge_count"] == 3)
    checks.append("big-endian threshold reversals and sge_count=3 normal branch")
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linux-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source_path = Path(__file__).with_name("authority_probe.c")
    runs = run_probe(source_path)
    checks = validate_runs(runs)
    report = {
        "schema": "outbound-scalar-authority-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Reduced C expressions only; no real kernel, controller or PCIe device",
        "independent_causal_chains": 2,
        "contracts": {
            "hci_ll": {
                "A": "BT_HCIUART_LL with SERDEV; WiLink 8 compatible; successful setup and nonzero speed enters opcode 0xff36 branch",
                "A_source_refs": ["hci_old_config:supported_config", "hci_old_driver:compatible", "hci_old_driver:host_speed"],
                "P": "host u32 speed must be encoded as four least-significant-byte-first command-parameter bytes; serial API retains host numeric speed",
                "P_source_refs": ["hci_old_driver:opcode", "hci_old_driver:host_speed", "hci_fix_driver:fixed_command"],
                "P_external_authority": "TI SWRU442B (revised October 2017), pp. 6 and 13; WiLink 8 scope",
                "C": "old &speed or fixed &speed_le passes __hci_cmd_sync and reaches skb_put_data, which memcpy-copies the four payload bytes",
                "C_source_refs": ["hci_old_driver:old_command", "hci_old_request:sync_to_request", "hci_old_request:payload_copy", "hci_old_skb_copy:raw_copy"],
                "normal_controls": ["positive speeds on little-endian CPU have identical old/fixed payloads", "speed=0 has identical bytes but does not enter actual if(speed) send branch"],
                "limit": "TI guide covers WiLink 8, not every older compatible; no firmware or hardware execution",
            },
            "mpt3sas": {
                "A": "SCSI_MPT3SAS depends on PCI and SCSI; PCIe SGL selection path after scsi_dma_map succeeds",
                "A_source_refs": ["mpt_old_config:supported_config", "mpt_old_driver:consumer"],
                "P": "scsi_bufflen returns host numeric sdb.length; NVME_PRP_PAGE_SIZE=4096; threshold=16384 host bytes",
                "P_source_refs": ["mpt_old_length_provider:length_provider", "mpt_old_constant:page_constant"],
                "C": "base_is_prp_possible compares data_length<=16384 and sge_count<=2; caller selects IEEE or PRP",
                "C_source_refs": ["mpt_old_driver:old_condition", "mpt_fix_driver:fixed_condition", "mpt_old_driver:consumer"],
                "normal_controls": ["all selected lengths on little-endian CPU give old=fixed", "sge_count=3 masks length condition on both CPUs", "16385 bytes with two SGEs selects PRP in both versions"],
                "limit": "s390x runs a reduced scalar function only; real adapter reachability and IO effects untested",
            },
        },
        "external_authority": {
            "title": "WiLink 8.0 Bluetooth Vendor-Specific HCI Commands",
            "document": "SWRU442B",
            "revision": "October 2017",
            "url": "https://www.ti.com/lit/ug/swru442b/swru442b.pdf",
            "pages": [6, 13],
            "scope": "WiLink 8 family including WL183xMOD; does not establish every older hci_ll compatible",
        },
        "probe_source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "historical_sources": git_sources(args.linux_dir),
        "runs": runs, "assertions": checks,
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")


if __name__ == "__main__":
    main()
