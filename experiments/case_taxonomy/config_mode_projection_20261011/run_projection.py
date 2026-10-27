"""One frozen 4-build/4-run native projection. Oracle comparison follows execution."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import platform
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def verify_pre():
    freeze = json.loads((HERE / "projection_pre.json").read_text())
    for relative, expected in freeze["files"].items():
        assert sha((HERE / relative).read_bytes()) == expected, relative
    for relative, expected in freeze["reused_files"].items():
        assert sha((HERE / relative).read_bytes()) == expected, relative
    assert freeze["maximum_builds"] == 4 and freeze["maximum_runs"] == 4
    assert platform.machine() == "x86_64" and sys.platform == "linux"
    return sha((HERE / "projection_pre.json").read_bytes())


def derive(row):
    """Evaluate observations against the predeclared CPU property, not the oracle row."""
    be = int(row["cpu_mode"] == "BE")
    row["local_return_symbol"] = "0-wrapper-success-sentinel" if row["local_return_value"] == 0 else "-EOPNOTSUPP"
    row["unrelated_bits_unchanged"] = (int(row["initial_control_register"], 16) & ~16) == (int(row["final_control_register"], 16) & ~16)
    row["selector_matches_injected_cpu_mode"] = row["selector"] == be
    row["final_bit_matches_injected_cpu_mode"] = row["final_data_big_endian_bit"] == be
    row["successful_cpu_mode_contract"] = row["local_return_value"] == 0 and row["final_bit_matches_injected_cpu_mode"]
    row["outcome"] = ("local_success_with_mode_match" if row["successful_cpu_mode_contract"] else
                      "silent_mode_mismatch" if row["local_return_value"] == 0 else "local_controlled_rejection")
    return row


def main():
    pre_hash = verify_pre()
    run = HERE / "runs" / "initial"
    run.mkdir(parents=True, exist_ok=False)
    receipts, rows = [], []

    def invoke(label, command):
        start = time.monotonic()
        failure = None
        try:
            response = subprocess.run(command, cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      timeout=45, check=False)
            stdout, stderr, rc = response.stdout, response.stderr, response.returncode
        except subprocess.TimeoutExpired as error:
            stdout, stderr, rc = error.stdout or b"", error.stderr or b"", "timeout"
            failure = repr(error)
        except OSError as error:
            stdout, stderr, rc = b"", b"", "os_error"
            failure = repr(error)
        out, err = run / f"{label}.stdout", run / f"{label}.stderr"
        out.write_bytes(stdout)
        err.write_bytes(stderr)
        receipts.append({"label": label, "command": command, "returncode": rc,
                         "seconds": time.monotonic() - start,
                         "stdout_sha256": sha(stdout), "stderr_sha256": sha(stderr),
                         "invocation_exception": failure})
        save_json(run / "execution_receipts.json", receipts)
        if rc:
            raise RuntimeError(f"{label}: exit {rc}; original receipt preserved; {failure or ''}")
        return stdout

    invoke("compiler_version", ["gcc", "--version"])
    target = invoke("compiler_target", ["gcc", "-dumpmachine"]).decode().strip()
    assert target.startswith("x86_64"), target
    for predicate in ["original", "cpu_attribute"]:
        for cpu in ["BE", "LE"]:
            label = predicate + "_" + cpu
            binary = run / label
            invoke("compile_" + label, ["gcc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                   "-fsanitize=undefined", "-fno-sanitize-recover=all",
                   "-I", str(HERE / "projection/config" / cpu),
                   "-DTEST_CPU_BE=" + str(int(cpu == "BE")),
                   str(HERE / f"projection/mode_{predicate}.c"), "-o", str(binary)])
            stdout = invoke("execute_" + label, [str(binary)])
            observed = [json.loads(line) for line in stdout.decode().splitlines()]
            assert len(observed) == 4
            for row in observed:
                assert row["predicate"] == predicate and row["cpu_mode"] == cpu
                rows.append(derive(row))
    # Observation collection is finished; only now load the independent pre-run oracle.
    oracle = json.loads((HERE / "oracle_pre/expectations.json").read_text())
    key_fields = ["predicate", "cpu_mode", "initial_data_big_endian_bit", "write_policy"]
    def key(row):
        return tuple(row[k] for k in key_fields)
    actual = {key(row): row for row in rows}
    assert len(rows) == len(actual) == oracle["row_count"] == 16
    comparisons = []
    for item in oracle["rows"]:
        row = actual[key(item)]
        mismatch = {}
        for field, expected in item["expected"].items():
            observed = row[field]
            same = observed == expected
            if not same:
                mismatch[field] = {"observed": observed, "expected": expected}
        if row["diagnostics"] != int(row["local_return_value"] == -95):
            mismatch["diagnostics"] = row["diagnostics"]
        if row["invalid_register_access"] != 0 or row["host_target"] != "x86_64":
            mismatch["harness_scope"] = row
        comparisons.append({"id": item["id"], "oracle_agreement": not mismatch,
                            "differences": mismatch, "oracle_outcome": item["expected"]["outcome"]})
    counts = {predicate: dict(Counter(row["outcome"] for row in rows if row["predicate"] == predicate))
              for predicate in ["original", "cpu_attribute"]}
    result = {"projection_pre_sha256": pre_hash, "host_machine": platform.machine(),
              "compiler_target": target, "compiled_variants": 4, "binary_executions": 4,
              "compile_repair_retries": 0, "observed_rows": rows, "comparisons": comparisons,
              "oracle_agreements": sum(item["oracle_agreement"] for item in comparisons),
              "counts": counts, "reads": sum(row["reg_read_calls"] for row in rows),
              "writes": sum(row["reg_write_calls"] for row in rows),
              "unrelated_bits_preserved_rows": sum(row["unrelated_bits_unchanged"] for row in rows),
              "new_confirmed_cases": 0, "independent_positive_cases": 0,
              "scope": "native_user_space_macro_injection_register_projection_not_kernel_or_ARM_execution"}
    save_json(run / "results.json", result)
    print(json.dumps({k: result[k] for k in ["oracle_agreements", "counts", "reads", "writes",
                                           "unrelated_bits_preserved_rows", "compile_repair_retries"]}))
    assert result["oracle_agreements"] == 16, "Saved results differ from independent oracle"


if __name__ == "__main__":
    main()
