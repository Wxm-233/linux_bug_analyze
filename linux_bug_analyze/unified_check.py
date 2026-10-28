"""Thin unified entry: case manifest -> registered adapter -> v2 contracts -> layered report.

Relations, policy documents and configuration symbols come from the reviewed manifest; adapters only
project stored inputs into facts; ``contract_protocol_v2`` alone decides. Inputs whose adapter is not
registered are reported as ``unsupported`` and are never judged. This is not automatic requirement
inference.

    python -m linux_bug_analyze.unified_check --manifest case.json [--manifest ...] --out DIR
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from .adapters import REGISTRY
from .contract_envelope import build_envelope, document, symbol_type, symbols_used, whole
from .contract_protocol import CLAIM_ROLES
from .contract_protocol_v2 import evaluate_contract

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_SCHEMA = "unified_case_v1"


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load_input(entry: Mapping[str, Any], root: Path) -> tuple[Any, dict[str, Any]]:
    params = dict(entry.get("params", {}))
    if "json" in entry:
        path = root / entry["json"]
        value: Any = json.loads(path.read_text(encoding="utf-8"))
        for key in entry.get("select", []):
            value = value[key]
        return value, {"source": entry["json"], "source_sha256": _sha(path), "select": entry.get("select", [])}
    if "dir" in entry:
        path = root / entry["dir"]
        files = sorted(p for p in path.iterdir() if p.is_file())
        return dict(params, run_dir=str(path)), {"source": entry["dir"], "files_sha256": {p.name: _sha(p) for p in files}}
    return dict(entry["inline"]), {"source": "inline"}


def _envelope(case: Mapping[str, Any], input_id: str, revision: str, relation: Mapping[str, Any],
              values: Mapping[str, Any], types: Mapping[str, str], evidence: Path, root: Path) -> dict[str, Any]:
    context = f"{case['case']}.{input_id}"
    qualification = relation.get("qualification")
    names = symbols_used(relation["scope"], relation["relation"], *([qualification] if qualification else []))
    missing = sorted(n for n in names if n not in values)
    if missing:
        raise KeyError("adapter did not provide: " + ", ".join(missing))
    config = set(case.get("config_symbols", []))
    symbols = {n: {"type": types.get(n) or symbol_type(values[n]), "role": "configuration" if n in config else "observation"}
               for n in sorted(names)}
    docs = {"evidence": document(evidence, root, revision, source_revision=revision),
            "policy": document(root / case["policy"], root, revision, source_revision=revision)}
    statement = case.get("statement", "Relation registered in the reviewed case manifest; evidence tier as declared.")
    spec = {"schema": "architecture_contract_v2", "contract_id": f"unified.{context}.{relation['name']}",
            "revision": revision, "basis": case["basis"], "context_id": context, "object_id": context + ".object",
            "sample_event": context + "." + relation.get("sample", "sample"),
            "deadline_event": context + ".unobserved_consumer", "authority_kind": case["authority_kind"],
            "symbols": symbols, "scope": relation["scope"], "relation": relation["relation"], "documents": docs,
            "role_claims": {r: {"statement": statement, "references": whole(docs, "policy" if r in ("authority", "consumer_requirement") else "evidence")}
                            for r in CLAIM_ROLES},
            "observation_claim": {"statement": "Stored input projected by the registered adapter.", "references": whole(docs, "evidence")},
            "facts": {n: {"value": values[n], "statement": "Adapter projection of the stored input.", "references": whole(docs, "evidence")}
                      for n in symbols}}
    if qualification is not None:
        spec["observation_qualification"] = qualification
    return build_envelope(spec)


def run_case(case: Mapping[str, Any], out: Path, root: Path = ROOT) -> dict[str, Any]:
    if case.get("schema") != MANIFEST_SCHEMA:
        raise ValueError("unsupported manifest schema")
    out, root = Path(out).resolve(), Path(root).resolve()
    evidence_dir = out / "evidence" / case["case"]
    evidence_dir.mkdir(parents=True, exist_ok=False)
    adapter = REGISTRY.get(case["adapter"])
    rows = []
    for entry in case["inputs"]:
        input_id = entry["id"]
        revision = entry.get("revision", case["revision"])
        row: dict[str, Any] = {"input": input_id, "revision": revision, "decisions": {}}
        if adapter is None:
            row["status"] = "unsupported"
            row["reason"] = "adapter not registered: " + case["adapter"]
            rows.append(row)
            continue
        version, fn = adapter
        try:
            raw, provenance = _load_input(entry, root)
            projected = fn(raw)
        except (KeyError, ValueError, TypeError, IndexError, OSError) as exc:
            row["status"] = "adapter_failed"
            row["reason"] = repr(exc)[:300]
            rows.append(row)
            continue
        evidence = evidence_dir / f"{input_id}.json"
        evidence.write_text(json.dumps({"case": case["case"], "input": input_id, "adapter": case["adapter"],
                                        "adapter_version": version, "provenance": provenance,
                                        "observation": projected["observation"], "facts": projected["values"]},
                                       ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        row["status"] = "judged"
        row["adapter_version"] = version
        for rel in case["relations"]:
            try:
                item = _envelope(case, input_id, revision, rel, projected["values"], projected.get("types", {}), evidence, root)
                result = evaluate_contract(item["contract"], item["ledger"], item["record"])
            except KeyError as exc:
                row["decisions"][rel["name"]] = {"relation_at_observation": "insufficient", "reasons": [str(exc)]}
                continue
            row["decisions"][rel["name"]] = {k: result[k] for k in ("applicability", "relation_at_observation",
                                                                     "relation_at_deadline", "whole_path", "reasons")}
        expected = (case.get("expected") or {}).get(input_id)
        if expected is not None:
            got = {k: v["relation_at_observation"] for k, v in row["decisions"].items()}
            row["expected"] = expected
            row["matches_expected"] = got == expected
        rows.append(row)
    counts = Counter(d["relation_at_observation"] for r in rows for d in r["decisions"].values())
    status = Counter(r["status"] for r in rows)
    compared = [r for r in rows if "matches_expected" in r]
    return {"case": case["case"], "family": case.get("family"), "mechanism": case.get("mechanism"),
            "basis": case["basis"], "adapter": case["adapter"], "inputs": len(rows), "status": dict(status),
            "decision_counts": dict(counts), "expected_compared": len(compared),
            "expected_matched": sum(r["matches_expected"] for r in compared), "rows": rows}


def markdown(report: Mapping[str, Any]) -> str:
    lines = ["# Unified check report", "", "| case | family / mechanism | tier | adapter | inputs | status | decisions | expected match |",
             "| --- | --- | --- | --- | ---: | --- | --- | --- |"]
    for c in report["cases"]:
        lines.append(f"| {c['case']} | {c['family']} / {c['mechanism']} | {c['basis']} | {c['adapter']} | {c['inputs']} | "
                     f"{c['status']} | {c['decision_counts']} | {c['expected_matched']}/{c['expected_compared']} |")
    lines += ["", "Deadline and whole-path results are reported per relation in the JSON; a sample never establishes the deadline.",
              "`unsupported` inputs had no registered adapter and were not judged."]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--manifest", type=Path, action="append", required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--root", type=Path, default=ROOT)
    a = p.parse_args(argv)
    a.out = a.out.resolve()
    a.out.mkdir(parents=True, exist_ok=False)
    cases = [run_case(json.loads(m.read_text(encoding="utf-8")), a.out, a.root) for m in a.manifest]
    report = {"manifests": [str(m) for m in a.manifest], "cases": cases}
    (a.out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (a.out / "report.md").write_text(markdown(report), encoding="utf-8")
    print(json.dumps([{k: c[k] for k in ("case", "inputs", "status", "decision_counts", "expected_compared", "expected_matched")}
                      for c in cases], ensure_ascii=False))


if __name__ == "__main__":
    main()
