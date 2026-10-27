"""Separate source-reference integrity from reviewed contract assumptions.

This gate consumes a frozen generator plan and a review card. It verifies source
references and bindings, but never decides whether a claim follows semantically
from its quote. source_contract_ready is a local, attributed review condition,
not machine_contract_proven or independent sample truth.
"""
from __future__ import annotations

import copy
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import contract_assertion_generator as generator

VERSION = "contract-authority-gate-v1.0"
FACT_KINDS = {"source_numeric_domain", "consumer_format", "applicability"}
FACT_STATUS = {"supported", "conditional", "insufficient", "conflict"}
ORIGINS = {"source_review", "normative_review", "assumption"}
UNKNOWN = {"", "unknown", "unproven", "unspecified", "n/a", "none"}
UNPINNED_DOCUMENT_VERSION = UNKNOWN | {"current", "latest", "head", "trunk", "main", "master"}


def _base() -> dict:
    return {"version": VERSION, "status": "insufficient", "source_contract_ready": False,
            "machine_contract_proven": False, "runtime_reachability_proven": False,
            "full_kernel_proven": False, "external_protocol_proven": False,
            "reference_integrity": {"status": "not_checked", "checks": [], "issues": []},
            "semantic_review": {"status": "unavailable", "qualification": "claims are reviewed input, never inferred automatically from matching source quotes"},
            "field_checks": [], "issues": [],
            "scope": "version-bound local reviewed source contract; not an independent label, hardware or complete interface proof"}


def _reported_conflict(card) -> bool:
    pending, seen = [card], set()
    while pending:
        item = pending.pop()
        if not isinstance(item, (dict, list)) or id(item) in seen:
            continue
        seen.add(id(item))
        if isinstance(item, dict):
            if item.get("status") == "conflict":
                return True
            pending.extend(item.values())
        else:
            pending.extend(item)
    return False


def _state(states) -> str:
    if "conflict" in states:
        return "conflict"
    if "insufficient" in states or not states:
        return "insufficient"
    if "conditional" in states:
        return "conditional"
    return "source_contract_ready"


def _known_text(value) -> bool:
    return isinstance(value, str) and value.strip().lower() not in UNKNOWN and len(value) <= 4096


def _selected_program(plan: dict, binding: dict) -> dict:
    if not isinstance(plan, dict) or plan.get("status") != "generated" or not isinstance(plan.get("programs"), list):
        raise ValueError("generated plan/program is missing")
    keys = {"revision": "source_revision", "source_file": "source_file", "function": "function",
            "variable": "variable", "payload_struct": "payload_struct"}
    if any(not _known_text(binding.get(key)) for key in keys):
        raise ValueError("card revision/source/function/object/payload binding incomplete")
    matches = [program for program in plan["programs"] if isinstance(program, dict)
               and all(program.get(value) == binding[key] for key, value in keys.items())
               and ("program_id" not in binding or program.get("id") == binding["program_id"])]
    if len(matches) != 1:
        raise ValueError("card binding does not select exactly one generated program")
    program = matches[0]
    inputs = program.get("validated_inputs", {})
    rebuilt = generator.build_plan(inputs.get("report"), inputs.get("files"))
    if not any(candidate == program for candidate in rebuilt["programs"]):
        raise ValueError("program does not reproduce from its retained source evidence")
    return program


def _source_entry(path: str, sources: dict, program: dict) -> tuple[str, dict]:
    if not isinstance(path, str) or path.startswith(("/", "\\")) or "\\" in path or ":" in path or ".." in path.split("/"):
        raise ValueError("reference file must be a relative repository source path")
    if path not in sources:
        raise ValueError("reference source file not supplied")
    item = sources[path]
    original = program["validated_inputs"]["files"].get(path)
    if isinstance(item, str):
        if original is None:
            raise ValueError("extra source needs explicit same-revision metadata")
        text, revision = item, program["source_revision"]
        metadata_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        provenance = "matches validated plan source bytes"
    elif isinstance(item, dict) and isinstance(item.get("text"), str):
        text, revision = item["text"], item.get("revision")
        metadata_hash, provenance = item.get("sha256"), "caller same-revision metadata, not a Git commit membership proof"
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if metadata_hash != digest:
            raise ValueError("supplied source sha256 does not match bytes")
        if "git_blob" in item:
            raw = text.encode("utf-8")
            blob = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
            if item["git_blob"] != blob:
                raise ValueError("supplied Git blob does not match bytes")
    else:
        raise ValueError("reference source must be text or a source metadata entry")
    if revision != program["source_revision"]:
        raise ValueError("reference source revision differs from selected program")
    if original is not None and text != original:
        raise ValueError("reference source bytes differ from validated same-version plan source")
    return text, {"file": path, "revision": revision, "sha256": metadata_hash, "provenance": provenance}


def _reference(evidence, sources: dict, program: dict) -> dict:
    result = {"status": "insufficient", "issue": None}
    try:
        if not isinstance(evidence, dict):
            raise ValueError("evidence reference is not an object")
        path, line, quote = evidence.get("file"), evidence.get("line"), evidence.get("quote")
        if not isinstance(line, int) or isinstance(line, bool) or line < 1 or not isinstance(quote, str) or not quote.strip() or len(quote) > 4096:
            raise ValueError("reference requires a positive line and a bounded exact quote")
        source, metadata = _source_entry(path, sources, program)
        if evidence.get("sha256") != metadata["sha256"]:
            raise ValueError("reference hash differs from supplied source")
        lines = source.splitlines(keepends=True)
        if line > len(lines):
            raise ValueError("reference line outside source")
        offset = sum(len(value) for value in lines[:line - 1])
        first = lines[line - 1]
        positions = [match.start() for match in re.finditer(re.escape(quote.split("\n", 1)[0]), first)]
        if not positions or not any(source[offset + pos:offset + pos + len(quote)] == quote for pos in positions):
            raise ValueError("exact quote does not begin on the referenced line")
        result.update(status="matched", metadata=metadata, line=line, quote=quote,
                      qualification="exact source reference only; semantic entailment not machine checked")
    except (ValueError, TypeError) as error:
        result["issue"] = str(error)
    return result


def _fact(fact, field: dict, program: dict, sources: dict, review_ok: bool) -> dict:
    check = {"status": "insufficient", "reviewed_input": False, "issues": [], "references": []}
    if not isinstance(fact, dict):
        check["issues"].append("fact is not an object")
        return check
    kind, status, origin = fact.get("kind"), fact.get("status"), fact.get("origin")
    check.update(kind=kind, reported_status=status, origin=origin, claim=fact.get("claim"), value=fact.get("value"))
    metadata_ok = (isinstance(kind, str) and kind in FACT_KINDS and isinstance(status, str) and status in FACT_STATUS
                   and isinstance(origin, str) and origin in ORIGINS)
    if not metadata_ok:
        check["issues"].append("unknown fact kind/status/origin")
    if not _known_text(fact.get("claim")):
        check["issues"].append("fact claim is missing or unknown")
    references = fact.get("evidence")
    if not isinstance(references, list) or not references:
        check["issues"].append("fact has no source references")
    else:
        check["references"] = [_reference(item, sources, program) for item in references]
        check["issues"].extend(item["issue"] for item in check["references"] if item["status"] != "matched")
    check["reference_complete"] = bool(isinstance(references, list) and references
        and all(item["status"] == "matched" for item in check["references"]))
    value_ok = True
    if kind == "source_numeric_domain":
        value_ok = fact.get("value") == "host_numeric"
    elif kind == "consumer_format":
        value_ok = fact.get("value") == {"endian": field["endian"], "bits": field["bits"]}
    elif kind == "applicability":
        value_ok = fact.get("value") == {"revision": program["source_revision"], "scope": "source_contract"}
    if not value_ok:
        check["issues"].append("fact value does not establish the selected source/schema/applicability precondition")
    history_ok = True
    if origin == "normative_review":
        history = fact.get("historical_applicability")
        check.update(document_version=fact.get("document_version"), historical_applicability=copy.deepcopy(history))
        document_version = fact.get("document_version")
        history_ok = (_known_text(document_version) and document_version.strip().lower() not in UNPINNED_DOCUMENT_VERSION and isinstance(history, dict)
                      and history.get("status") == "reviewed" and _known_text(history.get("claim")))
        if not history_ok:
            check["issues"].append("normative document version or historical applicability is unreviewed/unknown")
        check["normative_document_integrity"] = "not checked; only supplied same-revision source quotes are matched"
    if status == "conflict":
        check["status"] = "conflict"
    elif not metadata_ok or status == "insufficient" or check["issues"] and (value_ok is False or any(item["status"] != "matched" for item in check["references"]) or not references or not _known_text(fact.get("claim"))):
        check["status"] = "insufficient"
    elif status == "conditional" or origin == "assumption" or not review_ok or not history_ok:
        check["status"] = "conditional"
    elif not check["issues"] and status == "supported":
        check["status"] = "source_contract_ready"
        check["reviewed_input"] = True
    if not review_ok:
        check["issues"].append("no attributed completed semantic source-contract review")
    check["semantic_support"] = "supplied review claim, not automatic quote-to-claim inference"
    return check


def evaluate(plan, card, source_files) -> dict:
    """Gate an attributed source contract without deriving a new defect label."""
    result, reported_conflict = _base(), _reported_conflict(card)
    try:
        if not isinstance(card, dict) or not isinstance(source_files, dict):
            raise ValueError("contract card and source files are required")
        binding = card.get("binding")
        if not isinstance(binding, dict):
            raise ValueError("contract card binding missing")
        program = _selected_program(plan, binding)
    except (ValueError, TypeError, KeyError) as error:
        result["issues"].append(str(error))
        result["status"] = "conflict" if reported_conflict else "insufficient"
        result["semantic_review"]["reported_conflict"] = reported_conflict
        return result
    result.update(program_id=program["id"], binding=copy.deepcopy(binding))
    review = card.get("review")
    review_ok = (isinstance(review, dict) and review.get("status") == "reviewed"
                 and review.get("scope") == "source_contract" and isinstance(review.get("reviewer_kind"), str)
                 and review.get("reviewer_kind") in {"human", "assistant"}
                 and _known_text(review.get("reviewed_by")))
    result["semantic_review"] = {"status": "attributed_review_input" if review_ok else "unreviewed",
        "review": copy.deepcopy(review), "reported_conflict": reported_conflict,
        "qualification": "matching quotes verify references, not claim semantics; assistant review is not a human gold standard"}
    cards = card.get("fields")
    if not isinstance(cards, list):
        cards = []
    by_name = {}
    for item in cards:
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            by_name.setdefault(item.get("name"), []).append(item)
        else:
            result["issues"].append("field card name/object is malformed")
    expected_fields = {field["name"]: field for field in program["fields"]}
    if set(by_name) != set(expected_fields):
        result["issues"].append("contract card payload fields missing or unexpected")
    for name, field in expected_fields.items():
        field_result = {"name": name, "status": "insufficient", "issues": [], "facts": []}
        result["field_checks"].append(field_result)
        entries = by_name.get(name, [])
        if len(entries) != 1:
            field_result["issues"].append("exactly one card per payload field required")
            continue
        entry = entries[0]
        expected_source = {"struct": field["source_struct"], "field": field["source_field"], "type": field["source_type"]}
        expected_consumer = {"endian": field["endian"], "bits": field["bits"]}
        if entry.get("producer") != expected_source or entry.get("consumer") != expected_consumer:
            field_result["issues"].append("field source/type or consumer domain/width binding differs from selected program")
            continue
        facts = entry.get("facts")
        if not isinstance(facts, list) or not facts:
            field_result["issues"].append("field facts missing")
            continue
        checks = [_fact(fact, field, program, source_files, review_ok) for fact in facts]
        field_result["facts"] = checks
        kinds = {item.get("kind") for item in checks if isinstance(item.get("kind"), str)}
        if not FACT_KINDS.issubset(kinds):
            field_result["issues"].append("numeric domain, consumer format and source applicability facts all required")
        field_result["status"] = _state([item["status"] for item in checks] + (["insufficient"] if field_result["issues"] else []))
    all_references = [reference for field in result["field_checks"] for fact in field["facts"] for reference in fact["references"]]
    reference_issues = [reference["issue"] for reference in all_references if reference["status"] != "matched"]
    fact_checks = [fact for field in result["field_checks"] for fact in field["facts"]]
    if any(not fact.get("reference_complete", False) for fact in fact_checks):
        reference_issues.append("one or more supplied facts lack complete source references")
    coverage = bool(result["field_checks"] and not result["issues"] and all(not field["issues"]
        and FACT_KINDS.issubset({fact.get("kind") for fact in field["facts"] if isinstance(fact.get("kind"), str)})
        for field in result["field_checks"]))
    result["reference_integrity"] = {"status": "matched" if all_references and not reference_issues and coverage else "insufficient",
        "checks": all_references, "issues": reference_issues,
        "coverage_complete": coverage,
        "qualification": "exact bytes/revision metadata only; external document and semantic authority unproven"}
    result["status"] = _state([field["status"] for field in result["field_checks"]]
                             + (["insufficient"] if result["issues"] else []) + (["conflict"] if reported_conflict else []))
    result["source_contract_ready"] = result["status"] == "source_contract_ready"
    return result
