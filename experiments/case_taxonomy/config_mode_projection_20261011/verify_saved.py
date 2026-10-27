"""Read-only saved-byte verification. Never invokes Git, compiler or projection."""
from pathlib import Path
from collections import Counter
import hashlib
import json

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[3]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check_map(base, mapping):
    for relative, expected in mapping.items():
        assert sha((base / relative).read_bytes()) == expected, relative
    return len(mapping)


def main():
    before = read_json(HERE / "freeze_pre.json")
    before_count = check_map(HERE, before["files"])
    pre = read_json(HERE / "projection_pre.json")
    pre_count = check_map(HERE, pre["files"]) + check_map(HERE, pre["reused_files"])
    oracle = read_json(HERE / "oracle_pre/expectations.json")
    oracle_count = check_map(HERE / "oracle_pre", read_json(HERE / "oracle_pre/freeze.json")["files"])
    old = HERE.parent / "config_contract_20261010"
    assert sha((old / "completion_manifest.json").read_bytes()) == before["previous_completion_sha256"]
    old_count = check_map(old, read_json(old / "completion_manifest.json")["files"])
    sources = read_json(HERE / "retrieval_manifest.json")
    assert sources["source_requests"] == sources["git_commands"] == 2
    for source in sources["sources"]:
        raw = (HERE / source["saved"]).read_bytes()
        assert sha(raw) == source["sha256"] and len(raw) == source["bytes"]
        assert hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == source["blob"]
    rawdir = HERE / "raw"
    receipts = read_json(rawdir / "receipts.json")
    assert len(receipts) == 2
    for receipt in receipts:
        for stream in ["stdout", "stderr"]:
            raw = (rawdir / (receipt["label"] + "." + stream + ".bin")).read_bytes()
            assert sha(raw) == receipt[stream + "_sha256"]
        request = (rawdir / "batch.request.txt").read_bytes() if receipt["label"] == "01_objects" else b""
        assert sha(request) == receipt["stdin_sha256"]
        assert receipt["exit"] == 0
    batch = (rawdir / "01_objects.stdout.bin").read_bytes()
    pos = 0
    for source in sources["sources"]:
        end = batch.index(b"\n", pos)
        blob, typ, size = batch[pos:end].decode().split()
        assert blob == source["blob"] and typ == "blob" and int(size) == source["bytes"]
        pos = end + 1
        assert batch[pos:pos + int(size)] == (HERE / source["saved"]).read_bytes()
        pos += int(size)
        assert batch[pos:pos + 1] == b"\n"
        pos += 1
    assert pos == len(batch)
    declarations = (rawdir / "02_kconfig_declarations.stdout.bin").read_text().splitlines()
    names = [line.split(":", 3)[3].strip().split()[1] for line in declarations]
    assert Counter(names) == {"CPU_BIG_ENDIAN": 15}
    evidence = read_json(HERE / "source_evidence.json")
    original_raw = (HERE / evidence["source"]).read_bytes()
    assert sha(original_raw) == evidence["source_sha256"]
    original_lines = original_raw.decode().splitlines(keepends=True)
    body = "".join(original_lines[662:685])
    constants = original_lines[36] + original_lines[44]
    assert body == evidence["slice_text"] and sha(body.encode()) == evidence["slice_sha256"]
    assert constants == evidence["constants_text"]
    check_map(HERE, evidence["generated_files"])
    for predicate, expected in [("original", body), ("cpu_attribute", body.replace("CONFIG_BIG_ENDIAN", "CONFIG_CPU_BIG_ENDIAN"))]:
        text = (HERE / f"projection/mode_{predicate}.c").read_text()
        actual = text.split("/* BEGIN unchanged historical lines 663-685 (counterpart replaces one config). */\n", 1)[1].split("/* END historical mode slice. */", 1)[0]
        assert actual == expected and constants in text
    quote_count = 0
    for q in oracle["source_quotes"]:
        raw = (HERE.parent / q["saved_relative_to_stage"]).read_bytes()
        assert sha(raw) == q["sha256"]
        assert "\n".join(raw.decode().splitlines()[q["start_line"] - 1:q["end_line"]]) == q["text"]
        quote_count += 1
    run = HERE / "runs/initial"
    execution = read_json(run / "execution_receipts.json")
    assert len(execution) == 10
    assert sum(r["label"].startswith("compile_") for r in execution) == 4
    assert sum(r["label"].startswith("execute_") for r in execution) == 4
    observed = []
    for receipt in execution:
        assert receipt["returncode"] == 0
        for stream in ["stdout", "stderr"]:
            raw = (run / (receipt["label"] + "." + stream)).read_bytes()
            assert sha(raw) == receipt[stream + "_sha256"]
        assert (run / (receipt["label"] + ".stderr")).read_bytes() == b""
        if receipt["label"].startswith("execute_"):
            for line in (run / (receipt["label"] + ".stdout")).read_text().splitlines():
                observed.append(json.loads(line))
    result = read_json(run / "results.json")
    assert result["projection_pre_sha256"] == sha((HERE / "projection_pre.json").read_bytes())
    assert len(observed) == len(result["observed_rows"]) == 16
    key_fields = ["predicate", "cpu_mode", "initial_data_big_endian_bit", "write_policy"]
    def key(row):
        return tuple(row[field] for field in key_fields)
    expected = {key(r): r["expected"] for r in oracle["rows"]}
    retained = {key(r): r for r in result["observed_rows"]}
    assert len(retained) == len(expected) == 16
    for row in observed:
        stored = retained[key(row)]
        assert all(stored[k] == v for k, v in row.items())
        assert all(stored[k] == v for k, v in expected[key(row)].items())
        cpu = int(row["cpu_mode"] == "BE")
        assert row["local_return_value"] in [0, -95]
        assert stored["successful_cpu_mode_contract"] == (row["local_return_value"] == 0 and row["final_data_big_endian_bit"] == cpu)
        assert row["mode_region_entered"] and row["invalid_register_access"] == 0
        assert row["diagnostics"] == int(row["local_return_value"] == -95)
        assert (int(row["final_control_register"], 16) & ~16) == 0xa5000100
    assert result["oracle_agreements"] == 16 and all(r["oracle_agreement"] for r in result["comparisons"])
    assert result["reads"] == 24 and result["writes"] == 8 and result["unrelated_bits_preserved_rows"] == 16
    assert result["compile_repair_retries"] == result["new_confirmed_cases"] == result["independent_positive_cases"] == 0
    cleanup = read_json(WORKSPACE / "日志/目录整理-2026-10-10.json")
    protected_count = check_map(WORKSPACE, cleanup["protected_experiment_files"])
    code_count = check_map(WORKSPACE, cleanup["source_code"])
    report_count = check_map(WORKSPACE, cleanup["current_reports"])
    completion = HERE / "completion_manifest.json"
    seal_count = check_map(HERE, read_json(completion)["files"]) if completion.exists() else 0
    print(json.dumps({"status": "PASS", "pre_retrieval_files": before_count,
                      "projection_pre_files_including_reuse": pre_count, "oracle_files": oracle_count,
                      "new_source_objects": 2, "source_quotes": quote_count,
                      "previous_completion_files": old_count, "protected_historical_files": protected_count,
                      "protected_program_test_files": code_count, "current_reports_unchanged": report_count,
                      "observed_rows": 16, "oracle_agreements": 16,
                      "completion_sealed_files": seal_count}, ensure_ascii=False))


if __name__ == "__main__":
    main()
