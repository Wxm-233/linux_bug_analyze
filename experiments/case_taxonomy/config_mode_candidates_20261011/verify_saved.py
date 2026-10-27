"""Saved artifacts only; no parser import, Git, models, compiler or rerun."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[3]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check_map(base, mapping):
    for path, expected in mapping.items():
        assert sha((base / path).read_bytes()) == expected, path
    return len(mapping)


def check_subset(actual, expected):
    if isinstance(expected, dict):
        assert isinstance(actual, dict)
        for key, value in expected.items():
            if key != "reason":
                check_subset(actual[key], value)
    elif isinstance(expected, list):
        assert isinstance(actual, list) and len(actual) == len(expected)
        for a, b in zip(actual, expected):
            check_subset(a, b)
    else:
        assert actual == expected, (actual, expected)


def verify_quotes(value, source=None):
    count = 0
    if isinstance(value, dict):
        proposed = value.get("source")
        if isinstance(proposed, dict) and "saved" in proposed:
            source = proposed
        if all(key in value for key in ["start_line", "end_line", "text"]):
            assert source is not None
            raw = (HERE / source["saved"]).read_bytes()
            assert sha(raw) == source["sha256"]
            lines = raw.decode("utf-8").splitlines()
            assert "\n".join(lines[value["start_line"] - 1:value["end_line"]]) == value["text"]
            count += 1
        for key, child in value.items():
            if key != "source":
                count += verify_quotes(child, source)
    elif isinstance(value, list):
        for child in value:
            count += verify_quotes(child, source)
    return count


def main():
    frozen_inputs = load(HERE / "inputs_pre.json")
    count_inputs = check_map(HERE, frozen_inputs["files"])
    count_reused = check_map(HERE, frozen_inputs["reused_files"])
    pre = load(HERE / "implementation_pre.json")
    count_pre = check_map(HERE, pre["files"])
    check_map(HERE, pre["reused_files"])
    assert pre["maximum_inputs"] == 3 and pre["maximum_CLI_executions"] == 1
    oracle = load(HERE / "oracle_pre/expectations.json")
    check_map(HERE / "oracle_pre", load(HERE / "oracle_pre/freeze.json")["files"])
    assert oracle["input_pre_sha256"] == sha((HERE / "inputs_pre.json").read_bytes())
    inputs = load(HERE / "inputs.json")
    assert len(inputs["inputs"]) == 3
    original = (HERE / inputs["inputs"][0]["saved"]).read_bytes()
    counterpart = (HERE / inputs["inputs"][1]["saved"]).read_bytes()
    assert original.count(b"CONFIG_BIG_ENDIAN") == 1
    assert original.replace(b"CONFIG_BIG_ENDIAN", b"CONFIG_CPU_BIG_ENDIAN") == counterpart
    catalog = load(HERE / "control_catalog.json")
    catalog_quotes = verify_quotes(catalog)
    assert catalog_quotes == 5
    observations = load(HERE / "runs/initial/observations.json")
    result = load(HERE / "runs/initial/results.json")
    rows = {row["id"]: row for row in observations["rows"]}
    assert len(rows) == len(oracle["rows"]) == 3
    for row in oracle["rows"]:
        check_subset(rows[row["id"]], row["expected"])
    for row in observations["rows"]:
        for candidate in row["candidates"]:
            assert candidate["verdict"] == "needs_source_review"
            assert not candidate["controlled_operation"]["association_automatically_inferred"]
            assert candidate["boundaries"]["effective_configuration_binding"] == "unknown"
            assert candidate["boundaries"]["automatic_replacement"] is None
            assert candidate["suggested_check"]["first_actual_consumer"] is None
            assert not candidate["suggested_check"]["placement_certified"]
    observation_quotes = verify_quotes(observations)
    oracle_quotes = verify_quotes(oracle)
    assert observations["c_facts_calls"] == 3 and observations["kconfig_facts_calls"] == 2
    for key in ["Git_commands", "C_compilations", "new_confirmed_cases", "independent_positive_cases"]:
        assert observations[key] == 0
    receipt = load(HERE / "first_run.receipt.json")
    assert receipt["CLI_executions"] == 1 and receipt["returncode"] == 0
    assert receipt["implementation_pre_sha256"] == sha((HERE / "implementation_pre.json").read_bytes())
    for stream in ["stdout", "stderr"]:
        assert sha((HERE / ("first_run." + stream)).read_bytes()) == receipt[stream + "_sha256"]
    assert (HERE / "first_run.stderr").read_bytes() == b""
    stdout = load(HERE / "first_run.stdout")
    assert stdout["candidate_counts"] == result["candidate_counts"] == [1, 1, 0]
    assert stdout["oracle_agreements"] == result["oracle_agreements"] == 3
    assert all(item["oracle_agreement"] and not item["differences"] for item in result["comparisons"])
    assert not list(HERE.rglob("__pycache__"))
    previous = HERE.parent / "config_mode_projection_20261011"
    assert sha((previous / "completion_manifest.json").read_bytes()) == frozen_inputs["previous_completion_sha256"]
    count_previous = check_map(previous, load(previous / "completion_manifest.json")["files"])
    older = HERE.parent / "config_contract_20261010"
    count_older = check_map(older, load(older / "completion_manifest.json")["files"])
    cleanup = load(WORKSPACE / "日志/目录整理-2026-10-10.json")
    count_history = check_map(WORKSPACE, cleanup["protected_experiment_files"])
    count_code = check_map(WORKSPACE, cleanup["source_code"])
    completion = HERE / "completion_manifest.json"
    count_completion = check_map(HERE, load(completion)["files"]) if completion.exists() else 0
    print(json.dumps({"status": "PASS", "input_files": count_inputs, "reused_files": count_reused,
                      "pre_execution_files": count_pre, "catalog_quotes": catalog_quotes,
                      "observation_quote_objects": observation_quotes, "oracle_quote_objects": oracle_quotes,
                      "inputs": 3, "CLI_executions": 1, "oracle_agreements": 3,
                      "previous_sealed_files": count_previous, "older_sealed_files": count_older,
                      "historical_protected_files": count_history, "program_test_files": count_code,
                      "completion_files": count_completion}))


if __name__ == "__main__":
    main()
