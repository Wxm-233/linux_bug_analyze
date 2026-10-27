#!/usr/bin/env python3
"""One bounded state-condition extraction round over frozen known-case inputs.

Dry-run never reads a credential or imports an API client. Only final JSON is
parsed. Format/citation validity is not semantic correctness or detection proof.
"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
BASE_PATH = HERE.parent / "arch_witness_claude_20261014/expanded_output/run_model_checks.py"
spec = importlib.util.spec_from_file_location("state_extract_bounded_runner_base", BASE_PATH)
assert spec is not None and spec.loader is not None
base = importlib.util.module_from_spec(spec)
previous_bytecode = sys.dont_write_bytecode
try:
    sys.dont_write_bytecode = True
    spec.loader.exec_module(base)
finally:
    sys.dont_write_bytecode = previous_bytecode
base.HERE, base.PROJECT = HERE, PROJECT
base.SETTINGS = PROJECT / "analysis_out/claude-main-expanded/settings.toml"
base.LEDGER, base.LOCK = HERE / "model_ledger.json", HERE / ".model_runner.lock"
base.__doc__ = __doc__
original_prepare = base.prepare
REQUEST_IDS = ["startup_target_pair", "startup_target_ablated"]
PRIOR = [
    ("../arch_witness_checks_20261014/model_ledger.json", 52358, "usage_unknown_no_further_calls"),
    ("../arch_witness_claude_20261014/model_ledger.json", 10956, "budget_reservation_blocked"),
    ("../arch_witness_claude_20261014/expanded_output/model_ledger.json", 29333, None),
    ("../arch_witness_claude_20261014/compact_final/model_ledger.json", 18305, None),
]


def load_carryover(manifest, limits):
    rows = manifest.get("carryover")
    if not isinstance(rows, list) or len(rows) != 4 or any(not isinstance(row, dict) for row in rows):
        raise ValueError("Exactly four frozen prior ledgers are required")
    if [row.get("ledger") for row in rows] != [row[0] for row in PRIOR]:
        raise ValueError("Unexpected carryover ledger paths or order")
    if type(manifest.get("overall_budget_tokens")) is not int or manifest["overall_budget_tokens"] != 1000000:
        raise ValueError("The user-authorized cumulative budget must remain 1000000")
    normalized, total = [], 0
    for row, (relative, expected_charge, stop_reason) in zip(rows, PRIOR):
        path = (HERE / relative).resolve()
        if not path.is_relative_to(PROJECT):
            raise ValueError("Prior ledger resolved outside project")
        raw = path.read_bytes()
        sha = row.get("sha256")
        if not isinstance(sha, str) or not base.re.fullmatch(r"[a-f0-9]{64}", sha) or base.digest(raw) != sha:
            raise ValueError("Prior ledger SHA mismatch")
        prior = base.decode_json(raw.decode("utf-8-sig"))
        if not isinstance(prior, dict) or "stop_reason" not in prior or prior["stop_reason"] != stop_reason:
            raise ValueError("Prior stop state changed")
        entries = prior.get("entries")
        if not isinstance(entries, list) or not entries:
            raise ValueError("Prior ledger entries missing")
        accounted = 0
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("status") not in ("started", "finished"):
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
                raise ValueError("Prior charge differs from reported usage/full unknown reservation")
            accounted += charge
        if type(row.get("accounted_tokens")) is not int or row["accounted_tokens"] != expected_charge or accounted != expected_charge:
            raise ValueError("Frozen prior-ledger total changed")
        if stop_reason is None:
            planned = prior.get("fingerprint_inputs", {}).get("requests", [])
            if [entry["id"] for entry in entries] != REQUEST_IDS or [req["id"] for req in planned] != REQUEST_IDS \
                    or any(entry["status"] != "finished" for entry in entries):
                raise ValueError("Prior unstopped round did not exhaust exactly its two requests")
        total += accounted
        normalized.append({"ledger": relative, "sha256": sha, "accounted_tokens": accounted,
                           "prior_stop_reason": stop_reason})
    if total != 110952 or limits["max_total_tokens"] > 889048 or total + limits["max_total_tokens"] > 1000000:
        raise ValueError("This round plus prior charges exceeds the adjusted budget")
    return {"ledgers": normalized, "accounted_tokens": total, "overall_budget_tokens": 1000000,
            "budget_basis": "user_authorized_1000000_bounded_state_predicate_extraction"}


def text(value, limit, name, nonempty=False):
    if not isinstance(value, str) or (nonempty and not value.strip()) or len(value) > limit:
        raise ValueError(f"{name} must be text of at most {limit} characters" + (" and nonempty" if nonempty else ""))


def text_list(value, maximum, limit, name):
    if not isinstance(value, list) or len(value) > maximum:
        raise ValueError(f"{name} has invalid list/count")
    for item in value:
        text(item, limit, name)


def references(value, documents, maximum):
    if not isinstance(value, list) or not 1 <= len(value) <= maximum:
        raise ValueError("Evidence count outside this field's bounds")
    extracted = []
    for ref in value:
        if not isinstance(ref, dict) or ref.get("document") not in documents:
            raise ValueError("Unknown evidence document")
        lo = base.positive_integer(ref.get("start_line"), "evidence start_line")
        hi = base.positive_integer(ref.get("end_line"), "evidence end_line")
        doc = documents[ref["document"]]
        if hi < lo or lo < doc["document"]["start_line"] or hi > doc["document"]["end_line"] \
                or any(number not in doc["lines"] for number in range(lo, hi + 1)):
            raise ValueError("Evidence outside supplied continuous original range")
        extracted.append({"document": ref["document"], "path": doc["document"]["path"],
                          "start_line": lo, "end_line": hi,
                          "source_text": "\n".join(f"{n}: {doc['lines'][n]}" for n in range(lo, hi + 1))})
    return extracted


def validate_ast(node):
    """Bounded expression syntax only; no symbol meaning, C execution or eval."""
    count = 0
    def visit(value, depth):
        nonlocal count
        count += 1
        if depth > 5 or count > 32 or not isinstance(value, dict):
            raise ValueError("Predicate exceeds depth/node/type limits")
        if set(value) == {"symbol"}:
            text(value["symbol"], 160, "symbol", nonempty=True)
            return
        if set(value) == {"literal"}:
            literal = value["literal"]
            if type(literal) in (bool, int):
                return
            if type(literal) is float and math.isfinite(literal):
                return
            if isinstance(literal, str) and len(literal) <= 100:
                return
            raise ValueError("Literal must be bool, finite number or <=100-character string")
        if set(value) != {"op", "args"} or not isinstance(value["args"], list):
            raise ValueError("Invalid AST node shape")
        op, args = value["op"], value["args"]
        if not isinstance(op, str):
            raise ValueError("Operator must be text")
        arity = {"contains": (2, 2), "eq": (2, 2), "ne": (2, 2), "lt": (2, 2),
                 "le": (2, 2), "gt": (2, 2), "ge": (2, 2), "precedes": (2, 2),
                 "nonempty": (1, 1), "not": (1, 1), "and": (2, 4), "or": (2, 4)}
        if op not in arity or not arity[op][0] <= len(args) <= arity[op][1]:
            raise ValueError("Unsupported operator or wrong arity")
        for arg in args:
            visit(arg, depth + 1)
    visit(node, 1)


def parse_proposal(content, documents):
    proposal = base.decode_json(content.strip())
    if not isinstance(proposal, dict) or proposal.get("scope") not in base.SCOPES:
        raise ValueError("Invalid proposal scope")
    checks = proposal.get("checks")
    if not isinstance(checks, list) or len(checks) > 1:
        raise ValueError("At most one check is permitted")
    text_list(proposal.get("unknown"), 3, 160, "proposal unknown")
    for check in checks:
        if not isinstance(check, dict):
            raise ValueError("Check must be an object")
        for field, limit in (("id", 32), ("title", 120), ("basis", 220)):
            text(check.get(field), limit, field)
        if check.get("polarity") not in ("must_hold", "alert_if_true") or check.get("authority_status") not in base.AUTHORITY:
            raise ValueError("Invalid polarity/authority enum")
        if "predicate" not in check:
            raise ValueError("Predicate must be explicitly an AST or null")
        if check["predicate"] is not None:
            validate_ast(check["predicate"])
        text_list(check.get("unknown"), 3, 160, "check unknown")
        providers, config = check.get("providers"), check.get("configuration")
        if not isinstance(providers, list) or len(providers) > 2 or not isinstance(config, list) or len(config) > 2:
            raise ValueError("Provider/configuration list exceeds two items or is absent")
        for provider in providers:
            if not isinstance(provider, dict):
                raise ValueError("Provider must be an object")
            for field, limit in (("architecture", 40), ("value", 160), ("eligibility", 160)):
                text(provider.get(field), limit, "provider " + field)
            provider["program_extracted_evidence"] = references(provider.get("evidence"), documents, 4)
        for condition in config:
            if not isinstance(condition, dict):
                raise ValueError("Configuration must be an object")
            text(condition.get("architecture"), 40, "configuration architecture")
            text_list(condition.get("requires"), 8, 100, "configuration requires")
            condition["program_extracted_evidence"] = references(condition.get("evidence"), documents, 2)
        consumer = check.get("consumer")
        if not isinstance(consumer, dict) or consumer.get("event") not in ("entry", "before_call", "first_read"):
            raise ValueError("Invalid consumer/event")
        text(consumer.get("function"), 120, "consumer function")
        text(consumer.get("anchor"), 160, "consumer anchor")
        consumer["program_extracted_evidence"] = references(consumer.get("evidence"), documents, 4)
        check["program_extracted_evidence"] = references(check.get("evidence"), documents, 8)
    # Do not permit nonfinite JSON constants even in unused extra metadata.
    base.encoded(proposal)
    return proposal


def prepare():
    prepared = original_prepare()
    if [req["id"] for req in prepared["requests"]] != REQUEST_IDS:
        raise ValueError("Exactly the paired and architecture-ablated frozen requests are required")
    prior_requests = HERE.parent / "arch_witness_claude_20261014/compact_final/requests"
    for req in prepared["requests"]:
        if req["sha256"] != base.digest((prior_requests / (req["id"] + ".json")).read_bytes()):
            raise ValueError("Source request JSON bytes changed from the preceding compact round")
    inputs = prepared["fingerprint_inputs"]
    inputs["runner_sha256"] = base.digest(Path(__file__).read_bytes())
    inputs["runner_dependencies"] = [{"path": "../arch_witness_claude_20261014/expanded_output/run_model_checks.py",
                                      "sha256": base.digest(BASE_PATH.read_bytes())}]
    test_path = HERE / "test_extract_protocol.py"
    if test_path.is_file():
        inputs["runner_dependencies"].append({"path": test_path.name, "sha256": base.digest(test_path.read_bytes())})
    inputs["protocol_semantics"] = "Structured state candidates; parser validity does not establish semantic correctness"
    prepared["fingerprint"] = base.digest(base.encoded(inputs))
    return prepared


base.load_carryover, base.parse_proposal, base.prepare = load_carryover, parse_proposal, prepare

if __name__ == "__main__":
    try:
        base.main()
    except (ValueError, OSError, KeyError, TypeError, base.json.JSONDecodeError) as exc:
        print(base.json.dumps({"status": "preparation_error", "type": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        raise SystemExit(1) from None
