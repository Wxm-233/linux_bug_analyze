"""Independent finite synthetic boundary audit. Never accesses Git or APIs."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys


HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
BASE = STAGE.parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9_\-]+", args.label):
        raise ValueError("audit label must be a plain file component")
    destination = HERE / ("execution_" + args.label)
    if destination.exists():
        raise FileExistsError("preserve the existing audit execution; use a new label")

    specification_path = HERE / "probes_pre.json"
    specification = json.loads(specification_path.read_text(encoding="utf-8"))
    probes = specification["probes"]
    if len(probes) != 20 or len(probes) > specification["max_inputs"]:
        raise ValueError("the independent audit is fixed to the 20 prespecified inputs")
    if len({p["id"] for p in probes}) != len(probes):
        raise ValueError("duplicate probe identifier")
    implementation = STAGE / "numeric_compare.py"
    dependencies = [
        implementation,
        BASE / "interface_facts_20261008" / "interface_fact_extractor.py",
        BASE / "endian_consumer_single_revision.py",
        specification_path,
        Path(__file__).resolve(),
    ]
    before = {str(p): digest(p) for p in dependencies}
    destination.mkdir()
    inputs = destination / "inputs"
    inputs.mkdir()
    records = []
    for probe in probes:
        source_text = (
            probe.get("prefix", "")
            + probe.get("declaration", specification["default_declaration"])
            + "\n"
            + specification["default_header"]
            + "\n{\n"
            + probe["body"]
            + "\n}\n"
        )
        source_path = inputs / (probe["id"] + ".c")
        raw = source_text.encode("utf-8")
        source_path.write_bytes(raw)
        records.append({
            "probe": probe,
            "path": str(source_path),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob_sha1_algorithm": hashlib.sha1(
                b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
            ).hexdigest(),
        })
    input_snapshot = {
        "saved_before_module_import": True,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version,
        "argv": sys.argv,
        "dependencies_before": before,
        "inputs": records,
        "input_kind": "independent_synthetic_boundary_probes",
        "real_case_count": 0,
        "source_query_count": 0,
        "model_calls": 0,
    }
    (destination / "input_snapshot_pre.json").write_text(
        json.dumps(input_snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    module_spec = importlib.util.spec_from_file_location("numeric_boundary_root", implementation)
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = module
    module_spec.loader.exec_module(module)
    results = []
    for record in records:
        probe = record["probe"]
        raw = Path(record["path"]).read_bytes()
        src = module.Source(
            "synthetic/" + probe["id"] + ".c",
            "synthetic_numeric_boundary",
            record["path"],
            record["git_blob_sha1_algorithm"],
            raw,
        )
        try:
            output = module.inspect_function(src, specification["function"])
            target_rows = [
                row for row in output.get("field_atoms", [])
                if re.search(r"\bp\s*->\s*value\b", row.get("expression", ""))
            ]
            statuses = [row.get("status", "missing_status") for row in target_rows]
            bounded_refusal = not target_rows and output.get("execution_status") == "insufficient"
            passed = (
                bool(statuses) and all(s == probe["expected"] for s in statuses)
            ) or (probe["expected"] == "insufficient" and bounded_refusal)
            results.append({
                "id": probe["id"],
                "expected": probe["expected"],
                "target_statuses": statuses,
                "bounded_function_refusal": bounded_refusal,
                "passed": passed,
                "output": output,
            })
        except Exception as exc:
            results.append({
                "id": probe["id"],
                "expected": probe["expected"],
                "passed": False,
                "unexpected_exception": repr(exc),
            })
    after = {str(p): digest(p) for p in dependencies}
    immutable = before == after
    report = {
        "probe_count": len(results),
        "passed_count": sum(r["passed"] for r in results),
        "failed_ids": [r["id"] for r in results if not r["passed"]],
        "dependencies_unchanged_during_execution": immutable,
        "dependencies_before": before,
        "dependencies_after": after,
        "results": results,
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "real_case_count": 0,
        "new_confirmed_cases": 0,
        "generalization_claim": False,
        "normal_scope": "only_prespecified_local_synthetic_shapes",
        "root_code_modified_by_auditor": False,
        "git_or_model_access": False,
    }
    (destination / "results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    summary = {k: report[k] for k in (
        "probe_count", "passed_count", "failed_ids", "dependencies_unchanged_during_execution"
    )}
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if immutable and all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
