"""Independent, read-only audit of the new gate and saved HCI projection.

Does not compile or re-run the historical source projection.  Uses synthetic
gate fixtures only to probe status semantics and saved files for data checks.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import authority_gate as gate
import authority_gate_test as fixture_module


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gate_probes() -> dict:
    plan, card, files = fixture_module.fixture()
    baseline = gate.evaluate(plan, card, files)
    assert baseline["status"] == "source_contract_ready"
    assert baseline["reference_integrity"]["status"] == "matched"
    for key in ("machine_contract_proven", "runtime_reachability_proven", "full_kernel_proven", "external_protocol_proven"):
        assert baseline[key] is False

    no_review = copy.deepcopy(card)
    no_review.pop("review")
    assert gate.evaluate(plan, no_review, files)["status"] == "conditional"

    wrong_revision = copy.deepcopy(card)
    wrong_revision["binding"]["revision"] = "different"
    assert gate.evaluate(plan, wrong_revision, files)["status"] == "insufficient"

    wrong_field = copy.deepcopy(card)
    wrong_field["fields"][0]["producer"]["field"] = "different"
    assert gate.evaluate(plan, wrong_field, files)["status"] == "insufficient"

    invalid_quote = copy.deepcopy(card)
    invalid_quote["fields"][0]["facts"][1]["evidence"][0]["quote"] = "a line not present"
    assert gate.evaluate(plan, invalid_quote, files)["status"] == "insufficient"

    conflict = copy.deepcopy(card)
    conflict["binding"]["revision"] = "different"
    conflict["fields"][0]["facts"][0]["status"] = "conflict"
    assert gate.evaluate(plan, conflict, files)["status"] == "conflict"

    unknown_history = copy.deepcopy(card)
    unknown_history["fields"][0]["facts"][1].update(
        origin="normative_review", document_version="current",
        historical_applicability={"status": "unknown", "claim": "not verified"},
    )
    assert gate.evaluate(plan, unknown_history, files)["status"] == "conditional"

    # This is a deliberate boundary probe, not a defect oracle: the other
    # field's exact source quote cannot establish this field's semantics.
    cross_field_quote = copy.deepcopy(card)
    cross_field_quote["fields"][0]["facts"][1]["evidence"] = copy.deepcopy(
        card["fields"][1]["facts"][1]["evidence"]
    )
    cross = gate.evaluate(plan, cross_field_quote, files)
    assert cross["status"] == "source_contract_ready"
    assert cross["reference_integrity"]["status"] == "matched"
    assert cross["machine_contract_proven"] is False

    return {
        "baseline": baseline["status"],
        "no_review": "conditional",
        "wrong_revision": "insufficient",
        "wrong_field_binding": "insufficient",
        "invalid_quote": "insufficient",
        "conflict_over_wrong_binding": "conflict",
        "unknown_external_history": "conditional",
        "cross_field_exact_quote": {
            "status": cross["status"],
            "reference_integrity": cross["reference_integrity"]["status"],
            "machine_contract_proven": cross["machine_contract_proven"],
            "interpretation": "Exact reference integrity does not validate quote-to-field semantics; reviewer claim remains an input.",
        },
    }


def projection_audit() -> dict:
    result_file = ROOT / "provider_projection" / "results.json"
    record = json.loads(result_file.read_text(encoding="utf-8"))
    assert record["runner_sha256"] == sha(ROOT / "run_provider_projection.py")
    assert record["source_sha256"] == sha(ROOT / "provider_projection" / "chain.c")
    for relative, digest in record["input_hashes"].items():
        assert sha(ROOT.parent / relative) == digest, relative

    evidence = json.loads((ROOT / "source_authority" / "evidence.json").read_text(encoding="utf-8"))
    by_path = {source["path"]: source for source in evidence["sources"]}
    for source in evidence["sources"]:
        raw = (ROOT / "source_authority" / source["raw_file"]).read_bytes()
        assert raw.decode("utf-8") == source["full_text"]
        assert hashlib.sha256(raw).hexdigest() == source["full_file_sha256"]
        assert hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == source["git_blob_sha1"]

    chain = (ROOT / "provider_projection" / "chain.c").read_text(encoding="utf-8")
    for label in ("source", "consumer"):
        src = json.loads((ROOT / "provider_projection" / f"{label}.json").read_text(encoding="utf-8"))
        assert src["revision"] == evidence["parent_commit"]
        for block in (src["function"], src["structure"]):
            source = by_path[block["file"]]
            assert block["sha256"] == source["full_file_sha256"]
            lines = source["full_text"].splitlines()
            quote = block["quote"].splitlines()
            assert lines[block["line"] - 1 : block["line"] - 1 + len(quote)] == quote
            assert block["quote"] in chain

    commands = record["commands"]
    assert len(commands) == 4
    for command in commands:
        assert command["returncode"] == 0
    summaries = {}
    expected_error_kinds = {"provider_error", "reader_error", "reader_missing_sent"}
    for target, endian, command_index in (("x86_64", "little", 1), ("s390x", "big", 3)):
        source_output = commands[command_index]["stdout"]
        assert source_output.startswith('{"kind":"layout"')
        if target == "s390x":
            assert commands[command_index]["argv"][0] == "qemu-s390x"
        rows = [json.loads(line) for line in source_output.splitlines()]
        assert rows == record["targets"][target]["rows"]
        assert rows[0] == {"kind": "layout", "host_endian": endian, "rp_size": 9, "cp_size": 4, "cp_offsets": [0, 2]}
        chains = [row for row in rows[1:] if row["kind"] == "chain"]
        errors = [row for row in rows[1:] if row["kind"] != "chain"]
        assert len(chains) == 6 and {row["kind"] for row in errors} == expected_error_kinds
        assert len(errors) == 3
        mismatch = {"parent": 0, "fix": 0}
        for row in chains:
            values = record["values"][row["index"]]
            assert row["host_values"] == values
            actual = bytes.fromhex(row["payload"])
            assert len(actual) == 4
            assert row["reader_values"] == [int.from_bytes(actual[i : i + 2], "little") for i in (0, 2)]
            expected_le = b"".join(value.to_bytes(2, "little") for value in values[:2])
            if row["variant"] == "fix":
                assert actual == expected_le
            else:
                assert actual == b"".join(value.to_bytes(2, endian) for value in values[:2])
            mismatch[row["variant"]] += int(actual != expected_le)
        for error in errors:
            assert error["host_values"] == [27, 328, 27, 328]
            assert error["reader_values"] == [51, 801]
            assert error["payload"] == ""
        assert mismatch == {key: value["format_mismatch_vectors"] for key, value in record["targets"][target]["summary"].items()}
        summaries[target] = mismatch
    return {"saved_output_and_input_hashes": "matched", "source_quotes": "matched against saved parent blobs", "summaries": summaries,
            "limits": "Only saved user-space projected callbacks and assignments audited; no binary remains for replay, no kernel/controller execution."}


def main() -> None:
    report = {
        "audit_scope": "read-only independent saved-artifact review",
        "gate_sha256": sha(ROOT / "authority_gate.py"),
        "gate_tests_sha256": sha(ROOT / "authority_gate_test.py"),
        "provider_runner_sha256": sha(ROOT / "run_provider_projection.py"),
        "gate_probes": gate_probes(),
        "projection": projection_audit(),
    }
    (HERE / "audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("GATE_AND_SAVED_PROJECTION_AUDIT_OK")


if __name__ == "__main__":
    main()
