"""Count deliberately weak check strategies from saved rows, without C execution."""

from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def main() -> None:
    run = json.loads((ROOT / "results.json").read_text(encoding="utf-8"))
    controls = {}
    for target, versions in run["targets"].items():
        controls[target] = {}
        host_endian = "big" if target == "s390x" else "little"
        for version, result in versions.items():
            rows = result["rows"]
            no_target = [row for row in rows if row["target_add_attempt_count"] == 0]
            active = [row for row in rows if row["target_add_attempt_count"] == 1]
            early_error = sum(row["early_error"] == 1 for row in no_target)
            amp_success = sum(row["early_error"] == 0 and row["primary"] == 0 for row in no_target)
            primary_dle_off = sum(row["early_error"] == 0 and row["primary"] == 1 and row["extension"] == 0 for row in no_target)
            assert (early_error, amp_success, primary_dle_off) == (8, 4, 2)
            other_opcode_attempts = sum(len(row["add_attempt_opcodes"]) - row["add_attempt_opcodes"].count(0x2024) for row in rows)
            assert other_opcode_attempts == 4
            mismatches = sum(not row["payload_matches_source_contract"] for row in active)
            native_roundtrip_false_negatives = 0
            for row in active:
                raw = bytes.fromhex(row["payload_hex"])
                host_values = [int.from_bytes(raw[i:i + 2], host_endian) for i in (0, 2)]
                if host_values == row["host_values"] and not row["payload_matches_source_contract"]:
                    native_roundtrip_false_negatives += 1
            controls[target][version] = {
                "zero_target_as_pass_would_make_unsupported_byte_claims": len(no_target),
                "no_target_breakdown": {"stage1_injected_error": early_error, "amp_success": amp_success,
                                        "primary_success_dle_off": primary_dle_off},
                "ignore_opcode_would_count_unrelated_add_attempts": other_opcode_attempts,
                "naive_native_endian_roundtrip_would_miss_local_LE_mismatches": native_roundtrip_false_negatives,
                "raw_assignment_as_current_byte_error_in_all_16_rows_would_make_unsupported_or_contradicted_claims":
                    16 - mismatches if version == "parent" else None,
                "actual_target_add_attempts": len(active),
                "actual_local_LE_mismatches": mismatches,
            }
    record = {
        "scope": "offline counterfactual strategy controls from saved init-entry projection; no compiler/controller/kernel run",
        "qualification": "Static portability candidate is distinct from a current-run byte-error verdict; counts concern only this saved fixture grid.",
        "controls": controls,
    }
    with (HERE / "strategy_controls.json").open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print("OFFLINE_STRATEGY_CONTROLS_OK")


if __name__ == "__main__":
    main()
