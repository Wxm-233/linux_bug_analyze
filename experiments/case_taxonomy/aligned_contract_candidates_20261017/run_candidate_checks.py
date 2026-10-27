"""Bind unchanged model evidence and check only supported lexical call order."""
from __future__ import annotations

import argparse
from bisect import bisect_right
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from linux_bug_analyze.preprocessed_evidence import EvidenceError, _lex

SCHEMA = "n25_contract_candidates_v1"
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z_0-9]*\Z")
NONCALL_NAMES = {"if", "while", "for", "switch", "sizeof", "typeof", "__typeof__", "_Alignof",
                 "__alignof__", "__attribute__", "__attribute", "_Static_assert", "asm", "__asm__"}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def packet_identity(raw_documents, manifest):
    require(sha(raw_documents) == manifest["documents_sha256"], "packet_manifest_digest_mismatch")


def parse_final(raw):
    text = raw.decode("utf-8-sig")
    fenced = re.fullmatch(r"```(?:json)?\s*\n([\s\S]*?)\n```", text.strip())
    def unique_object(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result
    return json.loads(fenced[1] if fenced else text, object_pairs_hook=unique_object), ("unique_complete_outer_json_fence" if fenced else "bare_json")


def require(condition, reason):
    if not condition:
        raise EvidenceError(reason)


def pointer(value, selector):
    require(isinstance(selector, str) and selector.startswith("/") and selector.count("/") <= 8, "invalid_json_pointer")
    for part in selector[1:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        require(isinstance(value, dict) and part in value, "missing_json_pointer")
        value = value[part]
    return value


def bind_documents(packet, artifacts):
    """Validate exact region/projection identities; this is not source truth."""
    require(isinstance(packet, dict) and packet.get("schema") == SCHEMA, "packet_schema_mismatch")
    documents = packet.get("documents")
    require(isinstance(documents, list) and 0 < len(documents) <= 32, "invalid_documents")
    ids = [d.get("id") for d in documents if isinstance(d, dict)]
    require(len(ids) == len(documents) and all(isinstance(x, str) for x in ids) and len(set(ids)) == len(ids), "duplicate_or_invalid_document_id")
    manifest = {x["path"]: x["sha256"] for x in packet.get("input_manifest", [])}
    bound = {}
    for doc in documents:
        row = {"id": doc["id"], "status": "insufficient", "reasons": [], "document": doc}
        bound[doc["id"]] = row
        try:
            text = doc["text"]
            require(isinstance(text, str) and sha(text.encode("utf-8")) == doc["text_sha256"], "document_text_digest_mismatch")
            require(doc["profile"] in {"old_s390", "old_x86"}, "unsupported_profile")
            source = doc["source_binding"]
            raw = artifacts[source["artifact"]]
            require(isinstance(raw, bytes) and sha(raw) == source["artifact_sha256"] == manifest.get(source["artifact"]), "source_artifact_digest_mismatch")
            if doc["kind"] == "configured_function":
                original = json.loads(raw.decode("utf-8-sig"))
                require(source["json_pointer"] == "/functions/" + doc["function"] + "/text", "wrong_function_pointer")
                require(pointer(original, source["json_pointer"]) == text, "region_text_mismatch")
                region = original["functions"][doc["function"]]
                require(region.get("name") == doc["function"] and region.get("sha256") == doc["text_sha256"], "region_function_identity_mismatch")
                require(region.get("expected_source") == doc["path"], "source_path_mismatch")
                require(all(original.get(k) == doc.get(k) for k in
                            ["profile", "revision", "configuration_sha256", "image_sha256", "preprocessed_sha256"]), "profile_or_build_identity_mismatch")
            elif doc["kind"] == "selected_config_facts":
                lines = raw.decode("utf-8-sig").splitlines()
                chosen = source.get("source_lines")
                require(source.get("projection") == "selected_lines" and isinstance(chosen, list) and chosen
                        and all(type(n) is int and 1 <= n <= len(lines) for n in chosen)
                        and chosen == sorted(set(chosen)), "invalid_config_projection")
                require(doc["function"] is None and doc["path"] == source["artifact"]
                        and "/profiles/" + doc["profile"] + "/kernel.config" in source["artifact"], "config_profile_mismatch")
                require(text == "\n".join(lines[n - 1] for n in chosen)
                        and doc["configuration_sha256"] == sha(raw), "config_projection_mismatch")
            else:
                raise EvidenceError("unsupported_document_kind")
            row.update(status="source_bound", text_sha256=doc["text_sha256"], source_binding=source)
        except (EvidenceError, KeyError, TypeError, ValueError, IndexError) as exc:
            row["reasons"].append(str(exc))
    # Every configured function also needs its same-profile actual config doc.
    for row in bound.values():
        doc = row["document"]
        if row["status"] == "source_bound" and doc["kind"] == "configured_function":
            configs = [b for b in bound.values() if b["status"] == "source_bound"
                       and b["document"]["kind"] == "selected_config_facts"
                       and b["document"]["profile"] == doc["profile"]
                       and b["document"]["configuration_sha256"] == doc["configuration_sha256"]]
            if len(configs) != 1:
                row.update(status="insufficient", reasons=["same_profile_configuration_not_uniquely_bound"])
    return bound


def evidence_spans(evidence, bound, *, profile=None):
    require(isinstance(evidence, list) and 0 < len(evidence) <= 32, "evidence_missing_or_oversized")
    result = []
    for item in evidence:
        require(isinstance(item, dict) and set(item) == {"document", "start_line", "end_line"}, "evidence_schema_mismatch")
        require(isinstance(item["document"], str) and item["document"] in bound, "evidence_document_unknown")
        row = bound[item["document"]]
        require(row["status"] == "source_bound", "evidence_document_unbound")
        doc = row["document"]
        require(profile is None or profile == doc["profile"], "evidence_profile_mismatch")
        start, end = item["start_line"], item["end_line"]
        lines = doc["text"].splitlines()
        require(type(start) is int and type(end) is int and 1 <= start <= end <= len(lines)
                and end - start + 1 <= 24, "evidence_line_range_invalid")
        result.append({**item, "profile": doc["profile"], "text_sha256": doc["text_sha256"],
                       "quoted_text": "\n".join(lines[start - 1:end]), "source_binding": doc["source_binding"]})
    return result


def _function_body(tokens, pairs, function):
    bodies = []
    for index, token in enumerate(tokens[:-1]):
        if token.top_level and token.value == function and tokens[index + 1].value == "(":
            after = pairs[index + 1] + 1
            while after + 1 < len(tokens) and tokens[after].value in {"__attribute__", "__attribute"} and tokens[after + 1].value == "(":
                after = pairs[after + 1] + 1
            if after < len(tokens) and tokens[after].value == "{":
                bodies.append((after, pairs[after]))
    require(len(bodies) == 1, "function_body_not_unique")
    return bodies[0]


def _anchor(text, tokens, pairs, body, anchor):
    require(isinstance(anchor, dict) and {"callee", "line"} <= set(anchor)
            and not set(anchor) - {"callee", "line", "column"}, "anchor_schema_mismatch")
    callee, line = anchor["callee"], anchor["line"]
    require(isinstance(callee, str) and bool(IDENTIFIER.fullmatch(callee)) and callee not in NONCALL_NAMES
            and type(line) is int and line > 0, "invalid_callee_or_line")
    column = anchor.get("column")
    require(column is None or (type(column) is int and column > 0), "invalid_anchor_column")
    starts = [0] + [m.end() for m in re.finditer("\n", text)]
    found = []
    for index in range(body[0] + 1, body[1]):
        token = tokens[index]
        if token.value != callee or index + 1 >= len(tokens) or tokens[index + 1].value != "(":
            continue
        at_line = bisect_right(starts, token.start)
        at_column = token.start - starts[at_line - 1] + 1
        if at_line != line or (column is not None and column != at_column):
            continue
        closing = pairs[index + 1]
        after = closing + 1
        while after + 1 < len(tokens) and tokens[after].value in {"__attribute__", "__attribute"} and tokens[after + 1].value == "(":
            after = pairs[after + 1] + 1
        # Only an independent call-shaped statement is supported. This does
        # not resolve function pointers/macros or certify C execution semantics.
        previous = tokens[index - 1].value
        if after >= len(tokens) or tokens[after].value != ";":
            continue
        if previous not in {";", "{", "}"}:
            continue
        parameter_tokens = []
        argument_index = index + 2
        while argument_index < closing:
            argument = tokens[argument_index]
            if argument.value in {"(", "{", "["}:
                # Inner arguments/GNU statement expressions remain opaque. A
                # type inside them does not make the outer callee a prototype.
                argument_index = pairs[argument_index] + 1
            else:
                parameter_tokens.append(argument.value)
                argument_index += 1
        if any(v in {"void", "int", "char", "long", "short", "float", "double", "struct", "enum", "union"} for v in parameter_tokens):
            continue
        found.append({"callee": callee, "line": at_line, "column": at_column,
                      "character_offset": token.start, "utf8_byte_offset": len(text[:token.start].encode("utf-8"))})
    require(len(found) <= 1, "ambiguous_callee_anchor")
    return found[0] if found else None


def check_lexical_order(claim, bound):
    result = {"id": claim.get("id") if isinstance(claim, dict) else None, "status": "insufficient",
              "reasons": [], "control_flow_proved": False, "preparation_effect_proved": False}
    try:
        require(isinstance(claim, dict) and set(claim) == {"id", "kind", "profile", "document", "function", "first", "second", "expected", "evidence"}, "local_check_schema_mismatch")
        require(claim["kind"] == "lexical_call_order" and claim["expected"] in {"before", "after"}, "unsupported_local_relation")
        require(claim["document"] in bound, "local_document_unknown")
        row = bound[claim["document"]]
        require(row["status"] == "source_bound", "local_document_unbound")
        doc = row["document"]
        require(doc["kind"] == "configured_function" and doc["profile"] == claim["profile"]
                and doc["function"] == claim["function"], "local_document_profile_or_function_mismatch")
        spans = evidence_spans(claim["evidence"], bound, profile=claim["profile"])
        result["evidence"] = spans
        require("\\\n" not in doc["text"] and "\\\r\n" not in doc["text"], "line_splice_unsupported")
        tokens, pairs, _ = _lex(doc["text"])
        body = _function_body(tokens, pairs, doc["function"])
        anchors = [_anchor(doc["text"], tokens, pairs, body, claim[key]) for key in ("first", "second")]
        for key in ("first", "second"):
            require(any(s["document"] == claim["document"] and s["start_line"] <= claim[key]["line"] <= s["end_line"] for s in spans), "anchor_not_covered_by_evidence")
        if any(a is None for a in anchors):
            result.update(status="insufficient", reasons=["call_anchor_not_in_supported_expression_context"],
                          limitation="Missing or unsupported lexical anchor; not a semantic error verdict")
            return result
        first, second = anchors
        actual = "before" if first["character_offset"] < second["character_offset"] else "after" if first["character_offset"] > second["character_offset"] else "same_position"
        result.update(status="verified_lexical_order" if actual == claim["expected"] else "not_established",
                      observed_lexical_relation=actual, anchors=anchors,
                      document=doc["id"], profile=doc["profile"], function=doc["function"], text_sha256=doc["text_sha256"])
        if actual != claim["expected"]:
            result["reasons"] = ["expected_lexical_relation_not_established"]
    except (EvidenceError, KeyError, TypeError, ValueError, IndexError) as exc:
        result["reasons"].append(str(exc))
    return result


def check_output(output, bound):
    require(isinstance(output, dict) and set(output) == {"schema", "requirements", "architecture_paths", "local_checks", "recommended_checks", "limits"}
            and output["schema"] == SCHEMA, "model_output_schema_mismatch")
    require(all(isinstance(output[k], list) for k in ["requirements", "architecture_paths", "local_checks", "recommended_checks", "limits"]), "model_output_lists_missing")
    require(len(output["requirements"]) <= 3 and len(output["local_checks"]) <= 6
            and len(output["architecture_paths"]) <= 6, "model_output_bounds_exceeded")
    rows = []
    for group in ["requirements", "architecture_paths", "recommended_checks"]:
        for index, candidate in enumerate(output[group]):
            row = {"group": group, "index": index, "id": candidate.get("id") if isinstance(candidate, dict) else None,
                   "status": "insufficient", "semantic_review_required": True,
                   "check_scope": "evidence_identity_and_line_spans_only"}
            try:
                require(isinstance(candidate, dict), "candidate_not_object")
                if group == "architecture_paths":
                    require(candidate.get("profile") in {"old_s390", "old_x86"}, "architecture_path_profile_invalid")
                row["evidence"] = evidence_spans(candidate.get("evidence"), bound,
                    profile=candidate.get("profile") if group == "architecture_paths" else None)
                row["status"] = "source_bound_candidate"
            except (EvidenceError, KeyError, TypeError, ValueError, IndexError) as exc:
                row["reasons"] = [str(exc)]
            rows.append(row)
    return {"schema": SCHEMA, "candidate_bindings": rows,
            "local_checks": [check_lexical_order(claim, bound) for claim in output["local_checks"]],
            "formal_features_updated": False, "semantic_or_effect_proof": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--final", type=Path, required=True)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--output", type=Path, default=HERE / "candidate_checks.json")
    args = parser.parse_args()
    require(not args.output.exists(), "output_exists_preserve_prior_record")
    raw_documents = (HERE / "documents.json").read_bytes()
    manifest = json.loads((HERE / "packet_manifest.json").read_text(encoding="utf-8"))
    packet_identity(raw_documents, manifest)
    packet = json.loads(raw_documents.decode("utf-8-sig"))
    artifacts = {}
    for item in packet["input_manifest"]:
        path = (ROOT / item["path"]).resolve()
        require(path.is_relative_to(ROOT), "artifact_outside_project")
        artifacts[item["path"]] = path.read_bytes()
    bound = bind_documents(packet, artifacts)
    receipt_path = args.receipt or args.final.parent / "receipt.json"
    plan_path = args.plan or args.final.parent / "call_plan.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    require(receipt.get("status") == "complete_final_received" and receipt.get("exit_code") == 0
            and receipt.get("result_subtype") == "success" and receipt.get("result_is_error") is not True,
            "delivery_not_complete")
    require(receipt.get("actual_models") == receipt.get("response_models") == ["AWS-Claude-Opus-5.5"], "delivery_model_mismatch")
    require(isinstance(receipt.get("stop_reasons"), list) and receipt["stop_reasons"]
            and set(receipt["stop_reasons"]) <= {"end_turn", "stop_sequence"}
            and receipt.get("refusal_observed") is False, "delivery_stop_or_refusal_gate_failed")
    require(plan.get("prompt_sha256") == manifest["prompt_sha256"], "delivery_prompt_mismatch")
    raw_final = args.final.read_bytes()
    require(bool(raw_final.strip()), "empty_final")
    result = {"documents_sha256": sha(raw_documents), "raw_final_sha256": sha(raw_final),
              "document_bindings": [{k: v for k, v in row.items() if k != "document"} for row in bound.values()]}
    try:
        parsed, result["parse_mode"] = parse_final(raw_final)
        result.update(check_output(parsed, bound))
        result["status"] = "bounded_checks_complete"
    except (EvidenceError, ValueError, TypeError) as exc:
        result.update(status="insufficient", error=str(exc), original_final_unchanged=True)
    require(args.final.read_bytes() == raw_final, "final_changed_during_check")
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "documents_bound": sum(r["status"] == "source_bound" for r in bound.values()),
                      "local_statuses": [x["status"] for x in result.get("local_checks", [])]}))


if __name__ == "__main__":
    main()
