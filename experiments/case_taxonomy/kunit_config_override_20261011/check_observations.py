"""Compare saved observations with a frozen independent source oracle."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    freeze = load(HERE / "execution_pre.json")
    for name, expected in freeze["files"].items():
        assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == expected, name
    observed = load(HERE / "observations.json")
    adapter = load(HERE / "audit_oracle/oracle_runner_adapter_pre.json")
    oracle = load(HERE / "audit_oracle/oracle_pre.json")
    assert len(observed["rows"]) == len(adapter["rows"]) == len(oracle["rows"]) == 6
    adapted = {row["id"]: row["expected"] for row in adapter["rows"]}
    original = {row["id"]: row["expected"] for row in oracle["rows"]}
    fields = 0
    for row in observed["rows"]:
        assert all(row[k] == v for k, v in adapted[row["id"]].items()), row["id"]
        assert all(row[k] == v for k, v in adapter["required_unknown_states"].items()), row["id"]
        expected = original[row["id"]]
        assert dict(row["final_request_pairs"]) == expected["request_entries"]
        assert row["final_request_CPU_BIG_ENDIAN"] == expected["request_cpu_big_endian"]
        assert row["request_satisfied"] == expected["request_is_subset_of_output"]
        fields += len(adapted[row["id"]]) + len(adapter["required_unknown_states"])
    result = {"status": "PASS", "oracle_agreements": 6, "adapted_fields_checked": fields,
              "request_satisfied": sum(row["request_satisfied"] for row in observed["rows"]),
              "request_rejected": sum(not row["request_satisfied"] for row in observed["rows"]),
              "override_review_candidates": sum(row["review_override_legality_candidate"] for row in observed["rows"]),
              "oracle_sha256": hashlib.sha256((HERE / "audit_oracle/oracle_pre.json").read_bytes()).hexdigest(),
              "observations_sha256": hashlib.sha256((HERE / "observations.json").read_bytes()).hexdigest(),
              "scope": "six synthetic records, no original workflow conflict gate or actual mode certification"}
    (HERE / "comparison.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
