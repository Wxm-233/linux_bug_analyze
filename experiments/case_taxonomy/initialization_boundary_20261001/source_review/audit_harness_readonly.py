"""Read-only audit of saved final output against an earlier source expectation.

Does not import or execute the runner, compile C, execute binaries, or alter the
saved source expectation. Git reads are restricted to the four known source
paths at the two already reviewed revisions.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN = HERE.parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--linux-dir", required=True, type=Path)
    args = parser.parse_args()
    inputs = ["run_entry.py", "entry_parent.c", "entry_fix.c", "source_evidence.json", "results.json"]
    before = {name: digest(RUN / name) for name in inputs}
    report = json.loads((RUN / "results.json").read_text(encoding="utf-8"))
    evidence = json.loads((RUN / "source_evidence.json").read_text(encoding="utf-8"))
    pre_path = HERE / "expected_matrix_pre_harness.json"
    pre = json.loads(pre_path.read_text(encoding="utf-8"))
    pre_sha = digest(pre_path)
    expected = {
        tuple(int(row[field]) for field in
              ("primary", "lmp_le_capable", "data_len_feature", "init1_sync_error")): row
        for row in pre["rows"]
    }
    assert len(expected) == 16
    assert set(expected) == set(itertools.product((0, 1), repeat=4))
    assert pre["saved_at_utc"] < report["created_utc"]
    assert report["runner_sha256"] == before["run_entry.py"]
    assert report["source_evidence_sha256"] == before["source_evidence.json"]
    assert report["matrix"]["total_cells"] == 64
    assert report["run_integrity"]["runner_sha_before"] == report["run_integrity"]["runner_sha_after"] == before["run_entry.py"]

    refs = []
    reads = {}
    allowed_paths = {"net/bluetooth/hci_core.c", "include/net/bluetooth/hci.h",
                     "include/net/bluetooth/hci_core.h", "net/bluetooth/hci_event.c"}
    allowed_revisions = {pre["source_parent"], pre["source_fix"]}
    for variant, bundle in evidence["variants"].items():
        c_name = f"entry_{variant}.c"
        c = (RUN / c_name).read_text(encoding="utf-8")
        assert bundle["generated_c_sha256"] == report["generated_c_sha256"][variant] == before[c_name]
        assert report["run_integrity"]["generated_sha_before"][variant] == report["run_integrity"]["generated_sha_after"][variant] == before[c_name]
        for excerpt in bundle["excerpts"]:
            revision, path = excerpt["revision"], excerpt["path"]
            assert revision in allowed_revisions and path in allowed_paths
            key = (revision, path)
            if key not in reads:
                argv = ["git", "show", f"{revision}:{path}"]
                result = subprocess.run(argv, cwd=args.linux_dir, capture_output=True, check=True)
                blob_result = subprocess.run(["git", "rev-parse", f"{revision}:{path}"], cwd=args.linux_dir, capture_output=True, check=True)
                reads[key] = (result.stdout, blob_result.stdout.decode().strip())
            source_bytes, blob = reads[key]
            source = source_bytes.decode()
            assert blob == excerpt["blob"]
            assert hashlib.sha256(source_bytes).hexdigest() == excerpt["source_sha256"]
            lines = source.splitlines()
            text = "\n".join(lines[excerpt["start_line"] - 1:excerpt["end_line"]])
            assert text == excerpt["text"]
            actual_text = excerpt["text"].strip() if excerpt["label"].startswith("historical_default_") else excerpt["text"]
            assert c.count(actual_text) == 1, excerpt["label"]
            refs.append({"variant": variant, "label": excerpt["label"], "path": path,
                         "revision": revision, "blob": blob, "start_line": excerpt["start_line"],
                         "end_line": excerpt["end_line"], "excerpt_sha256": hashlib.sha256(excerpt["text"].encode()).hexdigest(),
                         "exact_git_excerpt_and_c_preservation": True})

    # Read the captured raw JSONL stdout, rather than trusting derived verdicts.
    raw_runs = []
    for cmd in report["commands"]:
        stdout = cmd.get("stdout", "")
        if stdout.startswith('{"kind":"meta"'):
            rows = [json.loads(line) for line in stdout.splitlines()]
            raw_runs.append((cmd, rows))
        assert cmd["returncode"] == 0
    assert len(raw_runs) == 4
    results = []
    per_group = []
    for target, groups in report["targets"].items():
        order = {"x86_64": "little", "s390x": "big"}[target]
        for variant, bundle in groups.items():
            assert bundle["metadata"]["actual_host_order"] == order
            assert bundle["metadata"]["payload_bytes"] == 4
            matches = [items for _, items in raw_runs if items[0]["variant"] == variant and items[0]["actual_host_order"] == order]
            assert len(matches) == 1
            raw = matches[0]
            assert len(raw) == 17 and raw[0] == bundle["metadata"]
            assert len(bundle["rows"]) == 16
            seen = set()
            local = []
            for row, observed in zip(bundle["rows"], raw[1:]):
                assert all(row[key] == value for key, value in observed.items())
                key = tuple(row[field] for field in ("primary", "lmp_le_capability", "extension", "early_error"))
                assert key not in seen and key in expected
                seen.add(key)
                exp = expected[key]
                applicable = exp["expected_target_add_attempts"] == 1
                assert row["stages"] == exp["expected_sync_call_stages"]
                assert row["result"] == (-5 if exp["expected_return"] == "-EIO" else 0)
                assert row["target_add_attempt_count"] == row["simulated_target_copy_count"] == exp["expected_target_add_attempts"]
                assert row["add_attempt_opcodes"].count(0x2024) == exp["expected_target_add_attempts"]
                primary, le, dle, error = key
                expected_other_opcodes = [0x2001] if primary and le and not error else []
                if primary and le and dle and not error:
                    expected_other_opcodes += [0x202f, 0x2023]
                if applicable:
                    expected_other_opcodes += [0x2024]
                assert row["add_attempt_opcodes"] == expected_other_opcodes
                assert row["host_values"] == [27, 328]
                mismatch = None
                if applicable:
                    values = row["host_values"]
                    actual = bytes.fromhex(row["payload_hex"])
                    schema = b"".join(value.to_bytes(2, "little") for value in values)
                    producer_order = order if variant == "parent" else "little"
                    produced = b"".join(value.to_bytes(2, producer_order) for value in values)
                    decoded = [int.from_bytes(actual[i:i + 2], "little") for i in (0, 2)]
                    assert actual == produced and len(actual) == 4
                    assert row["reader_values"] == decoded
                    assert row["expected_schema_payload_hex"] == schema.hex()
                    assert row["payload_matches_source_contract"] == (actual == schema)
                    assert row["local_reader_matches_host_values"] == (decoded == values)
                    assert row["applicability"] == "applicable_at_simulated_target_add_copy"
                    verdict = "conditional_numeric_match" if actual == schema else "conditional_representation_mismatch"
                    assert row["projection_verdict"] == verdict
                    mismatch = actual != schema
                else:
                    assert row["applicability"] == "not_applicable"
                    assert row["payload_hex"] is None and row["reader_values"] == [51, 801]
                    assert row["expected_schema_payload_hex"] is None
                    assert row["payload_matches_source_contract"] is None
                    assert row["local_reader_matches_host_values"] is None
                    assert row["projection_verdict"].startswith("not_applicable;")
                inconsistent = not le and bool(dle)
                assert row["fixture_state"].startswith("inconsistent_") == inconsistent
                cell = {"target": target, "variant": variant,
                        "primary": bool(primary), "lmp_le_capability": bool(le), "data_len_feature": bool(dle),
                        "init1_error": bool(error), "source_expectation_agrees": True,
                        "sync_attempt_stages": row["stages"], "target_add_attempt_count": row["target_add_attempt_count"],
                        "byte_check_applicable": applicable, "byte_mismatch": mismatch,
                        "payload_hex": row["payload_hex"], "local_reader_values": row["reader_values"],
                        "inconsistent_LE_off_DLE_on": inconsistent,
                        "real_hardware_reachability": "unproved"}
                results.append(cell)
                local.append(cell)
            assert seen == set(expected)
            summary = {"target": target, "variant": variant, "cells": len(local),
                       "applicable": sum(c["byte_check_applicable"] for c in local),
                       "not_applicable": sum(not c["byte_check_applicable"] for c in local),
                       "byte_mismatches_only_among_applicable": sum(c["byte_mismatch"] is True for c in local),
                       "inconsistent_fixture_cells": sum(c["inconsistent_LE_off_DLE_on"] for c in local),
                       "inconsistent_applicable": sum(c["inconsistent_LE_off_DLE_on"] and c["byte_check_applicable"] for c in local),
                       "noncontradictory_applicable": sum(not c["inconsistent_LE_off_DLE_on"] and c["byte_check_applicable"] for c in local)}
            saved = bundle["summary"]
            assert saved["configurations"] == summary["cells"]
            assert saved["configurations_with_target_add_attempt"] == summary["applicable"]
            assert saved["not_applicable"] == summary["not_applicable"]
            assert saved["byte_mismatch_at_mock_copy"] == summary["byte_mismatches_only_among_applicable"]
            assert saved["inconsistent_fixtures_with_target_add_attempt"] == summary["inconsistent_applicable"]
            per_group.append(summary)

    assert len(results) == 64
    after = {name: digest(RUN / name) for name in inputs}
    assert before == after and digest(pre_path) == pre_sha
    audit = {
        "schema": "independent-hci-initialization-harness-audit-v1",
        "reviewed_utc": datetime.now(timezone.utc).isoformat(),
        "status": "bounded_source_projection_agrees_with_pre_harness_expectation",
        "final_inputs_sha256": before,
        "pre_harness_expected_matrix_sha256": pre_sha,
        "pre_harness_expected_saved_utc": pre["saved_at_utc"],
        "reviewed_results_created_utc": report["created_utc"],
        "procedure": "Read saved raw stdout and final results; independent old expectation and Python bytes arithmetic; known Git excerpt revalidation only. No recompilation, runner execution or binary execution.",
        "git_source_files_read": [{"revision": revision, "path": path, "blob": blob,
                                   "sha256": hashlib.sha256(data).hexdigest()}
                                  for (revision, path), (data, blob) in reads.items()],
        "exact_preserved_source_excerpts": refs,
        "checks": {"all_64_source_conditions": True, "all_64_stages_returns": True,
                   "all_64_target_add_attempt_counts": True, "all_64_exact_opcode_sequences": True,
                   "all_8_applicable_bytes_and_local_reader_values": True,
                   "all_56_not_applicable_rows_have_no_byte_verdict": True,
                   "raw_stdout_matches_derived_records": True,
                   "original_git_excerpts_exactly_preserved": True, "input_hashes_stable_during_audit": True},
        "groups": per_group,
        "cells": results,
        "blockers_found": [],
        "qualifications": [
            "Counts represent original hci_req_add call attempts and successful mock memcpy only. The real hci_req_add_ev req->err and ENOMEM path, skb_queue_tail, controller transport and request completion are not executed.",
            "Matrix starts inside __hci_init. Outer hci_core.c:1501-1504 prior ret==0 && !HCI_UNCONFIGURED && !HCI_USER_CHANNEL remains an assumption, not a validated full boot/open chain.",
            "Only init1 sync -EIO injection is covered. Stage2/3/4 and allocation/timeout errors and asynchronous responses remain untested.",
            "LMP_LE is a hardware capability bit, not HCI_LE_ENABLED. Configuration flags and setup helpers are fixed false/no-op; command masks, other feature bits and max_page are zero; init1/init2 are stubs.",
            "Full init3 source is retained but its response side effects are not executed. Injected max values 27/328 and capabilities remain fixed; this is not discovery or actual controller state reachability.",
            "LE-off/DLE-on is an inconsistent injected fixture. Four applicable cells across versions/targets include that state; their mismatches are conditional projection evidence, not additional confirmed defects. The other four applicable cells also have unproved real-device reachability.",
            "The Python check is after the saved program has exited. It is not an inserted in-kernel check and does not prevent or block real command enqueue.",
            "The contract is the same-revision __le16 payload and actual local le16_to_cpu reader. External protocol normative authority, full kernel correctness and held-out detector generalization are not established.",
            "This is one already reviewed case in 64 version/target/condition cells. It does not add cases or estimate detection accuracy."
        ]
    }
    output = HERE / "harness_audit_final.json"
    output.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"saved": str(output), "groups": per_group, "checks": audit["checks"]}))


if __name__ == "__main__":
    main()
