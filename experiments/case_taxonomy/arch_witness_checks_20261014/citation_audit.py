#!/usr/bin/env python3
"""Offline, non-correcting audit of the three preserved R5 model responses.

Reads only named R5 artifacts. Does not import the model runner, resolve a
credential, send a request, alter model text, or judge semantic correctness.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
IDENTITIES = ("export_x86", "export_pair", "export_ablated")
SCOPES = {"local_candidate", "cross_arch_candidate", "insufficient"}
AUTHORITIES = {"existing_requirement", "policy_proposal", "insufficient"}
MAX_LINES = 20


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def decode(text: str) -> Any:
    return json.loads(text, object_pairs_hook=unique_object)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def proposal_schema(proposal: Any) -> list[str]:
    """Same structural requirements as frozen runner; references audited later."""
    errors: list[str] = []
    if not isinstance(proposal, dict):
        return ["proposal_not_object"]
    if proposal.get("scope") not in SCOPES:
        errors.append("scope_invalid")
    findings = proposal.get("findings")
    if not isinstance(findings, list):
        errors.append("findings_not_list")
        findings = []
    elif len(findings) > 3:
        errors.append("findings_count_over_3")
    unknown = proposal.get("unknown")
    if not isinstance(unknown, list) or not all(isinstance(x, str) for x in unknown):
        errors.append("unknown_not_string_list")
    for index, finding in enumerate(findings):
        label = f"findings[{index}]"
        if not isinstance(finding, dict):
            errors.append(f"{label}:not_object")
            continue
        for field in ("title", "contract", "architecture_difference", "propagation",
                      "exposure_difference", "check_candidate"):
            if not isinstance(finding.get(field), str) or not finding[field].strip():
                errors.append(f"{label}:{field}_not_nonempty_string")
        if finding.get("authority_status") not in AUTHORITIES:
            errors.append(f"{label}:authority_status_invalid")
        unknown = finding.get("unknown")
        if not isinstance(unknown, list) or not all(isinstance(x, str) for x in unknown):
            errors.append(f"{label}:unknown_not_string_list")
        evidence = finding.get("evidence")
        if not isinstance(evidence, list) or not 1 <= len(evidence) <= 8:
            errors.append(f"{label}:evidence_count_not_1_to_8")
    return errors


def supplied_documents(request: dict[str, Any]) -> dict[str, dict[str, Any]]:
    documents = {}
    for doc in request["documents"]:
        if doc["id"] in documents:
            raise ValueError(f"Duplicate request document ID: {doc['id']}")
        lines, errors = {}, []
        for text in doc["text"].splitlines():
            match = re.fullmatch(r"([0-9]+): ?(.*)", text)
            if not match:
                errors.append("unnumbered_supplied_line")
                continue
            number = int(match[1])
            if number in lines:
                errors.append(f"duplicate_supplied_line:{number}")
            lines[number] = match[2]
        expected = list(range(doc["start_line"], doc["end_line"] + 1))
        if list(lines) != expected:
            errors.append("supplied_line_numbers_not_declared_contiguous_range")
        documents[doc["id"]] = {"document": doc, "lines": lines, "errors": errors}
    return documents


def audit_reference(reference: Any, location: str,
                    documents: dict[str, dict[str, Any]]) -> dict[str, Any]:
    row: dict[str, Any] = {"location": location, "original_reference": reference,
                           "syntax_schema_errors": [], "document_valid": False,
                           "within_supplied_range": None, "continuous_lines": None,
                           "too_wide": None, "errors": [], "extraction_status": "unavailable"}
    if not isinstance(reference, dict):
        row["syntax_schema_errors"].append("reference_not_object")
        row["errors"] = list(row["syntax_schema_errors"])
        row["protocol_valid"] = False
        return row
    identity, start, end = reference.get("document"), reference.get("start_line"), reference.get("end_line")
    if not isinstance(identity, str):
        row["syntax_schema_errors"].append("document_not_string")
    for field, value in (("start_line", start), ("end_line", end)):
        if type(value) is not int or value <= 0:
            row["syntax_schema_errors"].append(f"{field}_not_positive_integer")
    row["errors"].extend(row["syntax_schema_errors"])
    doc = documents.get(identity) if isinstance(identity, str) else None
    row["document_valid"] = doc is not None
    if doc is None:
        row["errors"].append("unknown_document")
    if not row["syntax_schema_errors"]:
        row["requested_line_count"] = end - start + 1
        row["too_wide"] = end - start + 1 > MAX_LINES
        if end < start:
            row["errors"].append("end_before_start")
        if row["too_wide"]:
            row["errors"].append("too_wide_frozen_20_line_limit")
        if doc is not None:
            supplied = doc["document"]
            row["source_path"] = supplied["path"]
            row["source_revision"] = supplied["revision"]
            row["supplied_range"] = [supplied["start_line"], supplied["end_line"]]
            inside = start <= end and supplied["start_line"] <= start and end <= supplied["end_line"]
            row["within_supplied_range"] = inside
            if not inside:
                row["errors"].append("out_of_supplied_document_range")
            continuous = start <= end and all(number in doc["lines"] for number in range(start, end + 1))
            row["continuous_lines"] = continuous
            if not continuous:
                row["errors"].append("requested_lines_not_continuously_supplied")
            if doc["errors"]:
                row["errors"].append("supplied_document_numbering_invalid")
            # No alternative ID or outside source is looked up. An overlap is
            # visibly partial, preserves the original invalid citation, and
            # never upgrades the reference to protocol-valid.
            available = [number for number in range(max(start, supplied["start_line"]),
                         min(end, supplied["end_line"]) + 1) if number in doc["lines"]]
            if available:
                row["extracted_provided_line_numbers"] = available
                row["provided_source_text"] = "\n".join(f"{n}: {doc['lines'][n]}" for n in available)
                row["extraction_status"] = "complete_requested_range" if inside and continuous else "partial_provided_overlap_only"
    row["protocol_valid"] = not row["errors"]
    return row


def main() -> None:
    protected = [HERE / name for name in ("run_model_checks.py", "protocol_pre.md",
                 "system_prompt.txt", "model_ledger.json", "manifest.json", "summary.json", "停点.md")]
    protected += [HERE / folder / f"{identity}.json" for identity in IDENTITIES for folder in ("requests", "responses")]
    before = {str(p.relative_to(HERE)).replace("\\", "/"): sha(p) for p in protected}
    reports = []
    for identity in IDENTITIES:
        request = decode((HERE / "requests" / f"{identity}.json").read_text(encoding="utf-8-sig"))
        response = decode((HERE / "responses" / f"{identity}.json").read_text(encoding="utf-8-sig"))
        documents = supplied_documents(request)
        row: dict[str, Any] = {"id": identity, "response_model": response.get("model"),
                              "json_syntax_valid": False, "schema_errors": [], "references": []}
        try:
            content = response["choices"][0]["message"]["content"].strip()
            fence = re.fullmatch(r"```(?:json)?\s*\n([\s\S]*?)\n```", content)
            proposal = decode(fence[1] if fence else content)
            row["json_syntax_valid"] = True
            row["schema_errors"] = proposal_schema(proposal)
            if isinstance(proposal, dict) and isinstance(proposal.get("findings"), list):
                for fi, finding in enumerate(proposal["findings"]):
                    if not isinstance(finding, dict) or not isinstance(finding.get("evidence"), list):
                        continue
                    for ei, reference in enumerate(finding["evidence"]):
                        row["references"].append(audit_reference(reference, f"findings[{fi}].evidence[{ei}]", documents))
        except (ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
            row["syntax_error"] = str(exc)
        refs = row["references"]
        row["protocol_valid"] = row["json_syntax_valid"] and not row["schema_errors"] and all(ref["protocol_valid"] for ref in refs)
        row["reference_counts"] = counts(refs)
        row["supplied_document_numbering_errors"] = {key: value["errors"] for key, value in documents.items() if value["errors"]}
        reports.append(row)
    after = {str(p.relative_to(HERE)).replace("\\", "/"): sha(p) for p in protected}
    if before != after:
        raise RuntimeError("Original artifact changed during offline audit")
    all_refs = [ref for report in reports for ref in report["references"]]
    result = {"date": "2026-10-14", "offline": True, "external_calls": 0,
              "scope": "Three preserved export responses; citation validity only.",
              "frozen_max_lines_per_reference": MAX_LINES,
              "original_artifacts_unchanged": True, "original_sha256": before,
              "protocol_valid_responses": sum(r["protocol_valid"] for r in reports),
              "counts": counts(all_refs), "responses": reports,
              "limitations": ["No semantic or contract-correctness judgement.",
                  "No correction, alternate-document lookup, source-range expansion, or relaxed protocol.",
                  "Complete extraction of an over-wide reference does not make it protocol-valid.",
                  "Partial extraction quotes only provided overlap and remains invalid.",
                  "Too-wide and out-of-document counts can overlap; these are error dimensions."]}
    output = HERE / "citation_audit.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"protocol_valid_responses": result["protocol_valid_responses"],
                      "counts": result["counts"], "original_artifacts_unchanged": True}, ensure_ascii=False))


def counts(references: list[dict[str, Any]]) -> dict[str, int]:
    return {"total": len(references), "protocol_valid": sum(r["protocol_valid"] for r in references),
            "too_wide": sum(r["too_wide"] is True for r in references),
            "unknown_document": sum(not r["document_valid"] for r in references),
            "out_of_supplied_range": sum(r["within_supplied_range"] is False for r in references),
            "out_of_doc_any": sum(not r["document_valid"] or r["within_supplied_range"] is False for r in references),
            "noncontinuous": sum(r["continuous_lines"] is False for r in references),
            "reference_schema_invalid": sum(bool(r["syntax_schema_errors"]) for r in references),
            "complete_requested_range_extractable": sum(r["extraction_status"] == "complete_requested_range" for r in references),
            "partial_provided_overlap": sum(r["extraction_status"] == "partial_provided_overlap_only" for r in references),
            "unavailable": sum(r["extraction_status"] == "unavailable" for r in references)}


if __name__ == "__main__":
    main()
