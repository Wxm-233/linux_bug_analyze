"""Independent audit of saved init-entry stdout; never compiles or re-runs C."""

from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCE_EXPECTED = ROOT / "source_review" / "expected_matrix_pre_harness.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    result = load(ROOT / "results.json")
    source_expected = load(SOURCE_EXPECTED)
    assert source_expected["saved_at_utc"] < result["created_utc"]
    assert source_expected["target_present_rows"] == 2
    assert result["runner_sha256"] == sha(ROOT / "run_entry.py")
    assert result["source_evidence_sha256"] == sha(ROOT / "source_evidence.json")
    for version, expected_hash in result["generated_c_sha256"].items():
        assert expected_hash == sha(ROOT / f"entry_{version}.c")
        assert result["run_integrity"]["generated_sha_before"][version] == expected_hash
        assert result["run_integrity"]["generated_sha_after"][version] == expected_hash
    assert result["run_integrity"]["runner_sha_before"] == result["runner_sha256"]
    assert result["run_integrity"]["runner_sha_after"] == result["runner_sha256"]

    expected_rows = {
        (int(row["primary"]), int(row["lmp_le_capable"]), int(row["data_len_feature"]), int(row["init1_sync_error"])): row
        for row in source_expected["rows"]
    }
    assert len(expected_rows) == 16
    assert set(expected_rows) == set(itertools.product((0, 1), repeat=4))

    # Compare saved stdout, not just the runner's interpreted rows.
    execution_commands = [command for command in result["commands"] if command.get("stdout", "").startswith('{"kind":"meta"')]
    assert len(execution_commands) == 4
    summaries = {}
    for target, host_order in (("x86_64", "little"), ("s390x", "big")):
        summaries[target] = {}
        for version in ("parent", "fix"):
            matching = [command for command in execution_commands if command["argv"][-1].endswith(f"{target}-{version}")]
            assert len(matching) == 1 and matching[0]["returncode"] == 0
            stdout_rows = [json.loads(line) for line in matching[0]["stdout"].splitlines()]
            stored = result["targets"][target][version]
            assert stdout_rows[0] == stored["metadata"]
            assert stdout_rows[1:] == [
                {key: row[key] for key in stdout_rows[i + 1]}
                for i, row in enumerate(stored["rows"])
            ]
            assert stdout_rows[0]["actual_host_order"] == host_order
            assert stdout_rows[0]["payload_bytes"] == 4
            rows = stdout_rows[1:]
            assert len(rows) == 16
            observed = set()
            active = 0
            consistent_active = 0
            inconsistent_active = 0
            mismatches = 0
            for row_index, row in enumerate(rows):
                saved_row = stored["rows"][row_index]
                key = tuple(row[item] for item in ("primary", "lmp_le_capability", "extension", "early_error"))
                assert key in expected_rows and key not in observed
                observed.add(key)
                expected = expected_rows[key]
                assert row["stages"] == expected["expected_sync_call_stages"]
                assert row["result"] == (0 if expected["expected_return"] == "0" else -5)
                target_attempts = expected["expected_target_add_attempts"]
                assert row["target_add_attempt_count"] == target_attempts
                assert row["simulated_target_copy_count"] == target_attempts
                assert row["add_attempt_opcodes"].count(0x2024) == target_attempts
                # Init3 READ_MAX is gated separately by LE capability and DLE.
                assert row["add_attempt_opcodes"].count(0x202F) == int(bool(key[0] and key[1] and key[2] and not key[3]))
                assert row["host_values"] == [27, 328]
                if target_attempts:
                    active += 1
                    inconsistent_active += int(key[1] == 0)
                    consistent_active += int(key[1] == 1)
                    raw = bytes.fromhex(row["payload_hex"])
                    expected_le = (27).to_bytes(2, "little") + (328).to_bytes(2, "little")
                    expected_producer = (27).to_bytes(2, host_order if version == "parent" else "little") + (328).to_bytes(2, host_order if version == "parent" else "little")
                    assert raw == expected_producer
                    assert row["reader_values"] == [int.from_bytes(raw[0:2], "little"), int.from_bytes(raw[2:4], "little")]
                    assert saved_row["payload_matches_source_contract"] == (raw == expected_le)
                    assert saved_row["expected_schema_payload_hex"] == expected_le.hex()
                    mismatches += int(raw != expected_le)
                else:
                    assert row["payload_hex"] is None
                    assert saved_row["payload_matches_source_contract"] is None
                    assert saved_row["expected_schema_payload_hex"] is None
                    assert row["reader_values"] == [51, 801]
                    assert saved_row["projection_verdict"].startswith("not_applicable")
            assert observed == set(expected_rows)
            recorded = stored["summary"]
            assert recorded["configurations"] == 16
            assert recorded["configurations_with_target_add_attempt"] == active == 2
            assert recorded["not_applicable"] == 16 - active == 14
            assert recorded["byte_mismatch_at_mock_copy"] == mismatches
            assert recorded["inconsistent_fixtures_with_target_add_attempt"] == inconsistent_active == 1
            assert consistent_active == 1
            summaries[target][version] = {
                "target_add_attempts": active,
                "consistent_capability_activations": consistent_active,
                "inconsistent_capability_activations": inconsistent_active,
                "local_byte_mismatches": mismatches,
                "no_target_byte_verdict": 16 - active,
            }

    audit = {
        "scope": "read-only independent audit of saved user-mode init-entry stdout and source-predeclared matrix",
        "design_sha256": sha(HERE / "README.md"),
        "result_sha256": sha(ROOT / "results.json"),
        "source_expected_sha256": sha(SOURCE_EXPECTED),
        "runner_sha256": result["runner_sha256"],
        "source_evidence_sha256": result["source_evidence_sha256"],
        "summaries": summaries,
        "outcome": "saved stdout, source-expected activation matrix, target opcode counts, independent raw-byte oracle and local reader all agree",
        "qualification": [
            "Target count is hci_req_add attempt plus mocked copy, not original skb queue execution.",
            "LE-off/DLE-on is an inconsistent injected capability row, not confirmed real-world applicability.",
            "No-target rows receive no byte-pass verdict; they do not establish a fixed defect.",
            "No kernel, controller, full HCI initialization or external historical Bluetooth specification execution.",
        ],
    }
    with (HERE / "audit_final.json").open("x", encoding="utf-8") as stream:
        json.dump(audit, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print("INIT_ENTRY_SAVED_AUDIT_OK")


if __name__ == "__main__":
    main()
