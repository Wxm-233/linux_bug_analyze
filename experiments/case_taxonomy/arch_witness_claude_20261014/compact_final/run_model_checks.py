#!/usr/bin/env python3
"""One bounded compact-protocol correction, retaining all three prior ledgers.

Only final JSON is validated; no reasoning is inspected and no JSON is repaired.
Zero findings/insufficient is valid. Failures never trigger automatic retries.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_PATH = HERE.parent / "expanded_output/run_model_checks.py"
spec = importlib.util.spec_from_file_location("compact_claude_audited_base", BASE_PATH)
assert spec is not None and spec.loader is not None
base = importlib.util.module_from_spec(spec)
previous_bytecode = sys.dont_write_bytecode
try:
    sys.dont_write_bytecode = True
    spec.loader.exec_module(base)
finally:
    sys.dont_write_bytecode = previous_bytecode
base.HERE, base.LEDGER, base.LOCK = HERE, HERE / "model_ledger.json", HERE / ".model_runner.lock"
base.__doc__ = __doc__
original_prepare, original_parse = base.prepare, base.parse_proposal


def load_carryover(manifest, limits):
    allowed = [
        ("../../arch_witness_checks_20261014/model_ledger.json", 52358, "usage_unknown_no_further_calls"),
        ("../model_ledger.json", 10956, "budget_reservation_blocked"),
        ("../expanded_output/model_ledger.json", 29333, None),
    ]
    rows = manifest.get("carryover")
    if not isinstance(rows, list) or len(rows) != 3 or any(not isinstance(row, dict) for row in rows):
        raise ValueError("Compact phase requires exactly the three frozen prior ledgers")
    if [row.get("ledger") for row in rows] != [row[0] for row in allowed]:
        raise ValueError("Unexpected prior ledger paths/order")
    if type(manifest.get("overall_budget_tokens")) is not int or manifest["overall_budget_tokens"] != 1000000:
        raise ValueError("The user-adjusted overall budget must remain 1000000 tokens")
    normalized, total = [], 0
    for row, (relative, expected_charge, stop_reason) in zip(rows, allowed):
        path = (HERE / relative).resolve()
        if not path.is_relative_to(base.PROJECT):
            raise ValueError("Prior ledger resolved outside the project")
        raw = path.read_bytes()
        sha = row.get("sha256")
        if not isinstance(sha, str) or not base.re.fullmatch(r"[0-9a-f]{64}", sha) or base.digest(raw) != sha:
            raise ValueError("Prior ledger SHA mismatch")
        prior = base.decode_json(raw.decode("utf-8-sig"))
        if not isinstance(prior, dict) or "stop_reason" not in prior or prior["stop_reason"] != stop_reason:
            raise ValueError("Prior stop state changed")
        entries = prior.get("entries")
        if not isinstance(entries, list) or not entries:
            raise ValueError("Prior ledger entries missing")
        accounted = 0
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("status") not in {"started", "finished"}:
                raise ValueError("Invalid prior entry status")
            charge = entry.get("charged_tokens")
            if type(charge) is not int or charge < 0 or type(entry.get("usage_known")) is not bool:
                raise ValueError("Invalid prior charge/usage state")
            if entry["status"] == "started" or not entry["usage_known"]:
                expected = entry.get("reserved_tokens")
            else:
                usage = entry.get("usage")
                expected = usage.get("total_tokens") if isinstance(usage, dict) else None
            if type(expected) is not int or charge != expected:
                raise ValueError("Prior charge differs from known usage/full unknown reservation")
            accounted += charge
        if type(row.get("accounted_tokens")) is not int or row["accounted_tokens"] != expected_charge or accounted != expected_charge:
            raise ValueError("Frozen prior-ledger total changed")
        if stop_reason is None:
            planned = prior.get("fingerprint_inputs", {}).get("requests", [])
            expected_ids = ["startup_target_pair", "startup_target_ablated"]
            if [entry["id"] for entry in entries] != expected_ids or [item["id"] for item in planned] != expected_ids:
                raise ValueError("Expanded phase did not exhaust exactly its two planned requests")
            if any(entry["status"] != "finished" for entry in entries):
                raise ValueError("Expanded phase still has unfinished requests")
        total += accounted
        normalized.append({"ledger": relative, "sha256": sha, "accounted_tokens": accounted, "prior_stop_reason": stop_reason})
    if total != 92647 or total + limits["max_total_tokens"] > 1000000:
        raise ValueError("Compact phase plus prior charges exceeds the adjusted overall budget")
    return {"ledgers": normalized, "accounted_tokens": total, "overall_budget_tokens": 1000000,
            "budget_basis": "user_authorized_1000000_one_bounded_compact_protocol_correction"}


def parse_proposal(content, documents):
    # This phase requires one raw JSON object, not a Markdown wrapper.
    base.decode_json(content.strip())
    proposal = original_parse(content, documents)
    if len(proposal["findings"]) > 1:
        raise ValueError("Compact protocol permits at most one finding")
    for item in [proposal, *proposal["findings"]]:
        if len(item["unknown"]) > 2 or any(len(text) > 100 for text in item["unknown"]):
            raise ValueError("Each unknown list permits at most two strings of 100 characters")
    for finding in proposal["findings"]:
        for field in ("title", "contract", "architecture_difference", "propagation", "exposure_difference", "check_candidate"):
            if len(finding[field]) > 180:
                raise ValueError(f"Compact finding field {field} exceeds 180 characters")
    return proposal


def prepare():
    prepared = original_prepare()
    inputs = prepared["fingerprint_inputs"]
    inputs["runner_sha256"] = base.digest(Path(__file__).read_bytes())
    inputs["runner_dependencies"] = [{"path": "../expanded_output/run_model_checks.py", "sha256": base.digest(BASE_PATH.read_bytes())}]
    inputs["compact_final_limits"] = {"findings": 1, "semantic_field_characters": 180, "unknown_items": 2, "unknown_characters": 100}
    prepared["fingerprint"] = base.digest(base.encoded(inputs))
    return prepared


base.load_carryover, base.parse_proposal, base.prepare = load_carryover, parse_proposal, prepare

if __name__ == "__main__":
    try:
        base.main()
    except (ValueError, OSError, KeyError, TypeError, base.json.JSONDecodeError) as exc:
        print(base.json.dumps({"status": "preparation_error", "type": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        raise SystemExit(1) from None
