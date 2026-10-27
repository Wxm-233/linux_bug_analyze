"""Verify saved artifacts only; no historical functions or runner are executed."""
from pathlib import Path
import ast
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[3]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def plain_entries(text):
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        enabled = re.fullmatch(r"CONFIG_(\w+)=(y|n)", line)
        disabled = re.fullmatch(r"# CONFIG_(\w+) is not set", line)
        assert enabled or disabled, line
        name, value = enabled.groups() if enabled else (disabled.group(1), "n")
        assert name not in values
        values[name] = value
    return values


def main():
    pre = load(HERE / "execution_pre.json")
    for path, expected in pre["files"].items():
        assert sha(HERE / path) == expected, path
    receipt = load(HERE / "first_run.receipt.json")
    assert receipt["returncode"] == 0 and receipt["exception"] is None
    assert receipt["offline_runner_executions"] == 1
    for stream in ["stdout", "stderr"]:
        assert sha(HERE / ("first_run." + stream + ".bin")) == receipt[stream + "_sha256"]
    assert len((HERE / "first_run.stdout.bin").read_bytes()) == receipt["stdout_bytes"] == 6607
    assert (HERE / "first_run.stderr.bin").read_bytes() == b""
    observed = load(HERE / "observations.json")
    assert json.loads((HERE / "first_run.stdout.bin").read_bytes()) == observed
    adapter = load(HERE / "audit_oracle/oracle_runner_adapter_pre.json")
    expected = {r["id"]: r["expected"] for r in adapter["rows"]}
    inputs = load(HERE / "inputs_pre.json")
    assert len(inputs["rows"]) == len(observed["rows"]) == len(expected) == 6
    for item, row in zip(inputs["rows"], observed["rows"]):
        assert item["id"] == row["id"]
        assert all(row[k] == v for k, v in expected[row["id"]].items())
        assert all(row[k] == v for k, v in adapter["required_unknown_states"].items())
        path = HERE / item["provider"]
        assert sha(path) == item["provider_sha256"]
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assignment = next(n for n in tree.body if isinstance(n, ast.Assign))
        text = next(kw.value.value for kw in assignment.value.keywords if kw.arg == "kconfig")
        assert text == item["architecture_request_text"]
        arch = plain_entries(text)
        user = plain_entries(item["user_request_text"])
        output = plain_entries(item["synthetic_generated_text"])
        assert len(user) == 1 and list(user) == ["CPU_BIG_ENDIAN"]
        assert {k: v for k, v in output.items() if k != "CPU_BIG_ENDIAN"} == {
            k: v for k, v in arch.items() if k != "CPU_BIG_ENDIAN"}
        assert dict(row["original_arch_pairs"]) == arch and dict(row["user_pairs"]) == user
        assert dict(row["synthetic_generated_pairs"]) == output
        final = {**arch, **user}
        assert dict(row["final_request_pairs"]) == final
        assert row["request_satisfied"] == all(output.get(k) == v for k, v in final.items())
    oracle = load(HERE / "audit_oracle/oracle_pre.json")
    for source in oracle["sources"]:
        assert sha(WORKSPACE / source["path"]) == source["sha256"]
    quote_records = []
    for path, owner, names in [
        (HERE / "../kunit_config_binding_20261011/raw/03_kunit_config.py", "Kconfig",
         ["is_subset_of", "conflicting_options", "merge_in_entries"]),
        (HERE / "../kunit_config_binding_20261011/raw/02_kunit_kernel.py", "LinuxSourceTreeOperationsQemu",
         ["make_arch_config"])]:
        text = path.read_text(encoding="utf-8")
        cls = next(n for n in ast.parse(text).body if isinstance(n, ast.ClassDef) and n.name == owner)
        for name in names:
            function = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name)
            quote_records.append({"source": str(path.resolve().relative_to(WORKSPACE)).replace("\\", "/"),
                                  "sha256": sha(path), "owner": owner, "function": name,
                                  "start_line": function.lineno, "end_line": function.end_lineno,
                                  "quote": "\n".join(text.splitlines()[function.lineno - 1:function.end_lineno])})
    (HERE / "source_quotes.json").write_text(json.dumps({"quotes": quote_records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    comparison = load(HERE / "comparison.json")
    assert comparison["status"] == "PASS" and comparison["oracle_agreements"] == 6
    assert comparison["observations_sha256"] == sha(HERE / "observations.json")
    prior = {}
    for name in ["kunit_config_binding_20261011", "config_mode_transfer_scope_20261011",
                 "config_mode_candidates_20261011", "config_mode_projection_20261011", "config_contract_20261010"]:
        base = HERE.parent / name
        manifest = load(base / "completion_manifest.json")
        for path, expected_sha in manifest["files"].items():
            assert sha(base / path) == expected_sha, name + "/" + path
        prior[name] = len(manifest["files"])
    protection = load(WORKSPACE / "日志/目录整理-2026-10-10.json")
    protected = {}
    for group in ["protected_experiment_files", "source_code", "current_reports"]:
        for path, expected_sha in protection[group].items():
            assert sha(WORKSPACE / path) == expected_sha, path
        protected[group] = len(protection[group])
    result = {"status": "PASS", "frozen_objects": len(pre["files"]), "saved_rows": 6,
              "original_stdout_equals_observations": True, "source_function_quotes": len(quote_records),
              "prior_sealed_files": prior, "historical_protection": protected,
              "historical_functions_executed_by_verifier": 0, "new_Git_commands": 0}
    (HERE / "root_verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
