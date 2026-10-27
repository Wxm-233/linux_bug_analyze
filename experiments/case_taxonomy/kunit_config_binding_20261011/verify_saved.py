"""Verify saved first-run evidence, quotations and historical byte protection."""
from pathlib import Path
import ast
import hashlib
import json

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[3]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    freeze_counts = {}
    for filename in ["freeze_pre.json", "execution_pre.json"]:
        frozen = load(HERE / filename)
        files = {**frozen["files"], **frozen.get("reused_files", {})}
        for path, expected in files.items():
            assert sha((HERE / path).read_bytes()) == expected, path
        freeze_counts[filename] = len(files)
    retrieval = load(HERE / "retrieval_manifest.json")
    receipt = load(HERE / "raw/receipt.json")
    assert receipt["returncode"] == 0 and receipt["exception"] is None
    for stream in ["stdin", "stdout", "stderr"]:
        data = (HERE / ("raw/01_batch." + stream + ".bin")).read_bytes()
        assert sha(data) == receipt[stream + "_sha256"]
    batch = (HERE / "raw/01_batch.stdout.bin").read_bytes()
    assert len(batch) == receipt["stdout_bytes"] <= 524288
    assert retrieval["Git_commands"] == 1 and len(retrieval["sources"]) == 4
    expected_request = "".join(s["revision"] + ":" + s["path"] + "\n" for s in retrieval["sources"]).encode()
    assert expected_request == (HERE / "raw/01_batch.stdin.bin").read_bytes()
    pos = 0
    bypath = {}
    for source in retrieval["sources"]:
        assert source["status"] == "available"
        end = batch.index(b"\n", pos)
        blob, typ, size = batch[pos:end].decode().split()
        pos = end + 1
        data = batch[pos:pos + int(size)]
        pos += int(size)
        assert batch[pos:pos + 1] == b"\n"
        pos += 1
        assert typ == "blob" and blob == source["blob"]
        assert hashlib.sha1(b"blob " + size.encode() + b"\0" + data).hexdigest() == blob
        assert data == (HERE / source["saved"]).read_bytes()
        assert len(data) == source["bytes"] and sha(data) == source["sha256"]
        bypath[source["path"]] = source["saved"]
    assert pos == len(batch)
    quote_counts = {}
    for filename, key in [("source_quotes.json", "quotes"), ("audit_authority/review.json", "quotes"),
                          ("audit_method/oracle_pre.json", "source_quotes")]:
        quotes = load(HERE / filename)[key]
        for quote in quotes:
            source = quote.get("source") or bypath[quote["source_path"]]
            path = HERE / source
            expected_hash = quote.get("sha256") or quote["source_sha256"]
            assert sha(path.read_bytes()) == expected_hash
            start = quote.get("line_start", quote.get("start_line"))
            end = quote.get("line_end", quote.get("end_line"))
            text = quote.get("quote", quote.get("text"))
            assert "\n".join(path.read_text(encoding="utf-8").splitlines()[start - 1:end]) == text
        quote_counts[filename] = len(quotes)
    first = load(HERE / "first_run.receipt.json")
    assert first["returncode"] == 0 and first["exception"] is None and first["offline_runner_executions"] == 1
    for stream in ["stdout", "stderr"]:
        data = (HERE / ("first_run." + stream + ".bin")).read_bytes()
        assert sha(data) == first[stream + "_sha256"]
    observed = load(HERE / "observations.json")
    assert json.loads((HERE / "first_run.stdout.bin").read_bytes()) == observed
    assert (HERE / "first_run.stderr.bin").read_bytes() == b""
    oracle = load(HERE / "audit_method/oracle_pre.json")
    inputs = load(HERE / "inputs_pre.json")
    assert observed["matching_calls"] == len(inputs["records"]) == len(observed["records"]) == 6
    expected = {r["id"]: r["expected"] for r in oracle["rows"]}
    for row, input_row in zip(observed["records"], inputs["records"]):
        assert row["id"] == input_row["id"]
        assert all(row[k] == v for k, v in expected[row["id"]].items())
        tree = ast.parse((HERE / input_row["provider"]).read_text(encoding="utf-8"))
        assignment = next(n for n in tree.body if isinstance(n, ast.Assign))
        fragment = next(k.value.value for k in assignment.value.keywords if k.arg == "kconfig")
        assert fragment == input_row["request_text"]
    assert observed["real_generated_configs"] == observed["kernel_builds_or_boots"] == 0
    comparison = load(HERE / "comparison.json")
    assert comparison["status"] == "PASS" and comparison["oracle_agreements"] == 6
    assert comparison["observations_sha256"] == sha((HERE / "observations.json").read_bytes())
    old_counts = {}
    for name in ["config_mode_transfer_scope_20261011", "config_mode_candidates_20261011",
                 "config_mode_projection_20261011", "config_contract_20261010"]:
        base = HERE.parent / name
        seal = load(base / "completion_manifest.json")
        for path, expected_hash in seal["files"].items():
            assert sha((base / path).read_bytes()) == expected_hash, name + "/" + path
        old_counts[name] = len(seal["files"])
    protection = load(WORKSPACE / "日志/目录整理-2026-10-10.json")
    groups = {}
    for group in ["protected_experiment_files", "source_code", "current_reports"]:
        for path, expected_hash in protection[group].items():
            assert sha((WORKSPACE / path).read_bytes()) == expected_hash, path
        groups[group] = len(protection[group])
    result = {"status": "PASS", "freeze_objects": freeze_counts, "retrieved_blobs": 4,
              "quote_records": quote_counts, "offline_runner_executions": 1, "matching_records": 6,
              "first_stdout_equals_observations": True, "old_seals": old_counts,
              "historical_protection": groups, "verification_historical_functions_executed": 0}
    (HERE / "root_verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
