"""Check saved first observations against the independently written source oracle."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    freeze = load(HERE / "execution_pre.json")
    for path, expected in freeze["files"].items():
        assert sha((HERE / path).read_bytes()) == expected, path
    observed = load(HERE / "observations.json")
    oracle = load(HERE / "audit_method/oracle_pre.json")
    rows = oracle["rows"]
    expected = {r["id"]: r["expected"] for r in rows}
    assert len(expected) == len(observed["records"]) == 6
    actual = {r["id"]: {key: r[key] for key in expected[r["id"]]} for r in observed["records"]}
    assert actual == expected
    assert observed["real_generated_configs"] == observed["kernel_builds_or_boots"] == 0
    result = {"status": "PASS", "matching_records": 6, "oracle_agreements": 6,
              "request_satisfied_records": sum(v["request_satisfied"] for v in actual.values()),
              "request_rejected_records": sum(not v["request_satisfied"] for v in actual.values()),
              "oracle_sha256": sha((HERE / "audit_method/oracle_pre.json").read_bytes()),
              "observations_sha256": sha((HERE / "observations.json").read_bytes()),
              "scope": "six synthetic request-matching records; not independent cases or actual generated configs"}
    (HERE / "comparison.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
