"""Bounded source-context recovery; pointer acquisition is not content observation.

This development adapter reads final JSON/request documents and existing archives.
It neither repairs model citations nor changes the model consumer/AST.  A separate
post-hoc diagnostic may evaluate the unchanged AST at a proposed content boundary;
that is explicitly not validation at the model's pointer-acquisition location.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASE_ROOT = HERE.parent
PREVIOUS = CASE_ROOT / "state_predicate_extract_20261015"


def load_adapter():
    spec = importlib.util.spec_from_file_location("frozen_neutral_ast_adapter", PREVIOUS / "evaluate_predicates.py")
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


AST = load_adapter()


def remove_comments_strings(text):
    # Preserve newlines/positions; braces or call names in prose do not bind code.
    pattern = r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''
    return re.sub(pattern, lambda m: "".join("\n" if c == "\n" else " " for c in m[0]), text, flags=re.S)


def function_scopes(index):
    """Recognize complete one-line-signature functions in supplied fragments only."""
    scopes = {}
    signature = re.compile(r"^\s*(?:(?:static|inline|__always_inline)\s+)*(?:void|int|bool|unsigned\s+int)\s+(\w+)\s*\(([^()]*)\)\s*$")
    for identifier, (doc, lines) in index.items():
        if doc["kind"] != "source" or not doc["path"].endswith(".c"):
            continue
        numbers = list(lines)
        clean = remove_comments_strings("\n".join(lines.values())).splitlines()
        for offset, line in enumerate(clean):
            match = signature.match(line)
            if not match:
                continue
            opened, balance, finish = False, 0, None
            for pos in range(offset + 1, len(clean)):
                balance += clean[pos].count("{") - clean[pos].count("}")
                opened = opened or "{" in clean[pos]
                if opened and balance == 0:
                    finish = pos
                    break
            if finish is None:
                continue
            parameters = []
            for raw in match[2].split(","):
                raw = raw.strip()
                if raw in ("", "void"):
                    continue
                param = re.fullmatch(r"(.+?\b)(\w+)", raw)
                if not param:
                    parameters = None
                    break
                parameters.append({"name": param[2], "declaration": raw})
            if parameters is None:
                continue
            scope = {"document": identifier, "path": doc["path"], "function": match[1],
                     "start_line": numbers[offset], "end_line": numbers[finish],
                     "parameters": parameters,
                     "source_lines": [{"line": numbers[p], "text": lines[numbers[p]], "code": clean[p]}
                                      for p in range(offset, finish + 1)]}
            key = (scope["path"], scope["function"], scope["start_line"])
            if key in scopes and scopes[key] != scope:
                raise ValueError("ambiguous duplicate source scope")
            scopes[key] = scope
    return list(scopes.values())


def aliases(scope):
    rows = []
    pattern = re.compile(r"^\s*(?:const\s+)?struct\s+cpumask\s*\*\s*(\w+)\s*=\s*cpu_smt_mask\(\s*(\w+)\s*\)\s*;\s*$")
    for line in scope["source_lines"]:
        match = pattern.match(line["code"])
        if match:
            rows.append({"name": match[1], "getter": "cpu_smt_mask", "argument": match[2],
                         "line": line["line"], "source_text": line["text"],
                         "scope": {key: scope[key] for key in ("document", "path", "function", "start_line", "end_line")}})
    return rows


def source_record(scope):
    return {key: copy.deepcopy(scope[key]) for key in ("document", "path", "function", "start_line", "end_line", "parameters", "source_lines")}


def local_path(scope, start, stop, alias, cpu):
    """Fail closed on explicit mutation, branching or unexpanded arbitrary calls.

    The two accepted helper names are annotated assumptions of this bounded
    source connection; their complete bodies and concurrent stability are not
    proved.  No general purity or C alias analysis is claimed.
    """
    assumed = []
    for line in scope["source_lines"]:
        if not start < line["line"] < stop:
            continue
        code = line["code"]
        if re.search(r"\b(?:if|else|for|while|switch|goto|return)\b", code):
            raise ValueError("branch/control transfer on the candidate local path")
        variable = r"(?:" + re.escape(alias) + "|" + re.escape(cpu) + r")"
        # A bounded lexical rejection, not a complete C lvalue/alias solver.
        # Unknown statements are rejected below as an independent backstop.
        target = (r"(?:\(\s*\*\s*\b" + variable + r"\b\s*\)|\*\s*\b" + variable +
                  r"\b|\b" + variable + r"\b)(?:\s*(?:\[[^\]]*\]|(?:->|\.)\s*\w+))*")
        assignment = r"(?:<<=|>>=|[+\-*/%&|^]=|=(?!=)|\+\+|--)"
        if re.search(target + r"\s*" + assignment, code) or re.search(r"(?:\+\+|--)\s*" + target, code):
            raise ValueError("alias/CPU explicit write on the candidate local path")
        calls = re.findall(r"\b([A-Za-z_]\w*)\s*\(", code)
        for called in calls:
            if called not in ("cpu_rq", "local_irq_save", "sizeof"):
                raise ValueError("unexpanded intermediate call or mask mutation: " + called)
            assumed.append({"line": line["line"], "helper": called,
                            "limit": "Recognized local helper; no complete purity or concurrent object-stability proof."})
        stripped = code.strip()
        if not stripped:
            continue
        # Permit only the few declaration/helper shapes present on this local
        # historical path.  Even unrelated but unrecognized statements refuse
        # binding, rather than guessing their effect on object identity.
        declaration = re.fullmatch(r"(?:struct\s+rq|unsigned\s+long|int|bool)\s+(.+);", stripped)
        if declaration:
            declarators = declaration[1].split(",")
            initializer = r"(?:0|NULL|cpu_rq\(\s*" + re.escape(cpu) + r"\s*\))"
            shape = r"\s*\*?\s*[A-Za-z_]\w*\s*(?:=\s*" + initializer + r")?\s*"
            if all(re.fullmatch(shape, item) for item in declarators):
                continue
        if re.fullmatch(r"local_irq_save\(\s*\*\s*flags\s*\)\s*;", stripped):
            continue
        raise ValueError("unrecognized intermediate statement; local identity/effect not proved")
    return assumed


def content_connection(scope, acquire, all_scopes):
    # One explicit call edge only, with literal parameter->argument evidence.
    choices = []
    for line in scope["source_lines"]:
        if line["line"] <= acquire["line"]:
            continue
        call = re.fullmatch(r"\s*(\w+)\s*\(([^()]*)\)\s*;\s*", line["code"])
        if not call:
            continue
        candidates = [s for s in all_scopes if s["path"] == scope["path"] and s["function"] == call[1]]
        if len(candidates) != 1:
            continue
        callee = candidates[0]
        args = [a.strip() for a in call[2].split(",")]
        if len(args) != len(callee["parameters"]):
            continue
        parameter_map = dict(zip((p["name"] for p in callee["parameters"]), args))
        for other in aliases(callee):
            if parameter_map.get(other["argument"]) != acquire["argument"]:
                continue
            read = next((r for r in callee["source_lines"] if r["line"] > other["line"]
                         and re.search(r"\bfor_each_cpu\(\s*\w+\s*,\s*" + re.escape(other["name"]) + r"\s*\)", r["code"])), None)
            if read is not None:
                choices.append((line, callee, other, read, parameter_map))
    if not choices:
        raise ValueError("no complete same-object callee/content-read connection in supplied fragments")
    first_line = min(choice[0]["line"] for choice in choices)
    first = [choice for choice in choices if choice[0]["line"] == first_line]
    if len(first) != 1:
        raise ValueError("ambiguous first candidate content call")
    call, callee, other, read, mapping = first[0]
    assumptions = local_path(scope, acquire["line"], call["line"], acquire["name"], acquire["argument"])
    assumptions += local_path(callee, other["line"], read["line"], other["name"], other["argument"])
    return {"status": "bounded_source_connection", "caller": scope["function"],
            "call_line": call["line"], "call_source": call["text"], "parameter_to_argument": mapping,
            "callee": callee["function"], "callee_alias": other,
            "same_getter_identity": {"getter": acquire["getter"], "caller_argument": acquire["argument"],
                                     "callee_argument": other["argument"], "basis": "explicit call argument/parameter map, not equal variable names"},
            "content_read": {"document": callee["document"], "path": callee["path"], "function": callee["function"],
                             "line": read["line"], "expression": read["text"].strip(),
                             "event": "before_mask_iteration", "proposed_observation": "lock_snapshot",
                             "observed_event": "pre_irq_disable_content_sample",
                             "not_exact_iteration_observation": True,
                             "observation_limit": "Archived mask is sampled before local_irq_save, not at the later iteration; intervening/concurrent stability is unproved."},
            "local_helper_assumptions": assumptions,
            "continuous_object_stability_proved": False,
            "callee_scope": source_record(callee)}


def original_references(check):
    out = {"consumer": copy.deepcopy(check["consumer"]["evidence"]),
           "check": copy.deepcopy(check["evidence"]), "providers": [], "configuration": []}
    for key in ("providers", "configuration"):
        out[key] = [{"architecture": item.get("architecture"), "evidence": copy.deepcopy(item["evidence"])} for item in check.get(key, [])]
    return out


def ast_bindings(predicate, scope, acquire):
    bindings, failures = {}, []
    text = AST.canonical("\n".join(r["code"] for r in scope["source_lines"]))
    for symbol in sorted(AST.symbols(predicate)):
        name = AST.canonical(symbol)
        kind = None
        if name == acquire["argument"]:
            kind = "target_cpu"
        elif name in (acquire["name"], f"cpu_smt_mask({acquire['argument']})"):
            kind = "cpu_set"
        elif name == f"cpumask_weight({acquire['name']})" and name in text:
            kind = "weight"
        elif name == f"cpu_online({acquire['argument']})" and name in text:
            kind = "online"
        if kind is None:
            failures.append("symbol lacks supported same-scope identity: " + symbol)
        else:
            bindings[symbol] = {"kind": kind, "local_scope": scope["function"], "alias_acquisition_line": acquire["line"]}
    return bindings, failures


def diagnostic_projection(check, scope, acquire, connection, archive_loader):
    result = {"status": "unmapped", "at_original_model_event": False,
              "boundary_origin": "posthoc_program_suggested_content_boundary",
              "predicate_changed": False, "consumer_replaced": False,
              "observed_event": "pre_irq_disable_content_sample",
              "suggested_event": "before_mask_iteration",
              "not_exact_iteration_observation": True,
              "value_at_exact_suggested_iteration": "insufficient",
              "inherited_foundation_interpretation": {
                  "same_mask_until_first_consumer": "Equality at several recorded samples only, not continuous stability between samples.",
                  "continuous_object_stability_proved": False},
              "values": [], "reasons": []}
    if check.get("predicate") is None:
        result["reasons"] = ["null predicate remains null"]
        return result
    AST.validate_ast(check["predicate"])
    bindings, failures = ast_bindings(check["predicate"], scope, acquire)
    result["bindings"] = bindings
    if failures:
        result["reasons"] = failures
        return result
    try:
        if AST.infer_type(check["predicate"], bindings) != "bool":
            raise ValueError("predicate is not boolean")
        # This is the only supported observed content boundary.  The name is
        # verified by the automatically recovered call edge before projection.
        if connection["callee"] != "sched_core_lock" or connection["content_read"]["proposed_observation"] != "lock_snapshot":
            raise ValueError("source connection has no supported archival content observation")
        archive = archive_loader()
        result["archival_foundation"] = archive
        if not archive.get("inputs_unchanged") or len(archive["rows"]) != 4 or any(row["failed_foundation"] for row in archive["rows"]):
            raise ValueError("archival foundation is incomplete")
        for row in archive["rows"]:
            first = row["first_consumption"]
            values = {symbol: {"target_cpu": first["cpu"], "cpu_set": {n for n in range(4) if first["mask"] & (1 << n)},
                               "weight": first["weight"], "online": bool(first["online"])}[binding["kind"]]
                      for symbol, binding in bindings.items()}
            value = AST.evaluate_ast(check["predicate"], values)
            if type(value) is not bool or check.get("polarity") not in ("must_hold", "alert_if_true"):
                raise ValueError("unsupported final value/polarity")
            result["values"].append({"profile": row["profile"], "value": value,
                "alert_candidate": not value if check["polarity"] == "must_hold" else value,
                "bound_values": {key: sorted(val) if isinstance(val, set) else val for key, val in values.items()}})
        result["status"] = "diagnostic_values_at_separate_content_boundary"
    except (KeyError, OSError, TypeError, ValueError) as exc:
        result["values"] = []
        result["reasons"].append(str(exc))
    return result


def analyze(request, proposal, input_origin, archive_loader=AST.load_archives):
    result = {"status": "insufficient", "input_origin": input_origin,
              "original_model_scope": proposal.get("scope"), "original_model_references": None,
              "program_expanded_context": [], "source_connection": None,
              "original_event_evaluation": {"status": "insufficient", "values": []},
              "new_boots": 0, "new_builds": 0, "external_calls": 0, "new_cases": 0,
              "predicate_generated_by_program": False, "model_protocol_status_changed": False,
              "validated_detector": False, "reasons": []}
    try:
        index = AST.supplied_documents(request)
        checks = proposal.get("checks")
        if not isinstance(checks, list) or len(checks) != 1:
            raise ValueError("exactly one existing final check is required for context binding")
        check = checks[0]
        result["original_model_check"] = copy.deepcopy(check)
        result["original_model_ast"] = copy.deepcopy(check.get("predicate"))
        result["original_model_consumer"] = copy.deepcopy(check.get("consumer"))
        result["original_model_references"] = original_references(check)
        refs = AST.check_rows(index, check)
        result["original_reference_scope"] = AST.source_scope(refs)
        scopes = function_scopes(index)
        consumer = check["consumer"]
        consumer_refs = AST.extract(index, consumer["evidence"])
        matching = [scope for scope in scopes if scope["function"] == consumer.get("function") and any(
            ref["path"] == scope["path"] and scope["start_line"] <= ref["start_line"] <= ref["end_line"] <= scope["end_line"] for ref in consumer_refs)]
        if len(matching) != 1:
            raise ValueError("original referenced consumer has no unambiguous complete supplied function scope")
        scope = matching[0]
        result["program_expanded_context"].append(source_record(scope))
        anchor = AST.canonical(consumer.get("anchor", ""))
        if not anchor or consumer.get("event") != "first_read":
            raise ValueError("only the existing first_read/acquisition proposal is supported in this development stage")
        acquisitions = [alias for alias in aliases(scope) if anchor in (
            AST.canonical(alias["source_text"]), f"cpu_smt_mask({alias['argument']})")]
        if len(acquisitions) != 1:
            raise ValueError("model anchor is not an unambiguous cpumask pointer acquisition")
        acquire = acquisitions[0]
        if acquire["argument"] not in {param["name"] for param in scope["parameters"]}:
            raise ValueError("getter object is not the enclosing function's parameter")
        if not any(ref["path"] == scope["path"] and ref["start_line"] <= acquire["line"] <= ref["end_line"] for ref in consumer_refs):
            raise ValueError("pointer acquisition is not in original consumer references")
        result["original_position_classification"] = {"kind": "pointer_acquisition", "line": acquire["line"],
            "scope": acquire["scope"], "parameter": acquire["argument"], "local_alias": acquire["name"],
            "observation_status": "unobserved_at_this_exact_point", "is_content_snapshot": False}
        result["original_event_evaluation"]["reason"] = "Obtaining a pointer is not observing its pointee contents; no independent archive observation at this exact acquisition point."
        connection = content_connection(scope, acquire, scopes)
        result["source_connection"] = {key: val for key, val in connection.items() if key != "callee_scope"}
        result["program_expanded_context"].append(connection["callee_scope"])
        result["suggested_content_consumption"] = copy.deepcopy(connection["content_read"])
        result["suggested_content_consumption"].update(origin="program_expanded_context_not_model_reference", replaces_original_consumer=False)
        result["status"] = "context_bound_original_event_insufficient"
        result["diagnostic_content_projection"] = diagnostic_projection(check, scope, acquire, connection, archive_loader)
        result["limits"] = ["Program-added context is not a repaired/model-supplied citation.",
                           "Two pointer getters connected by a local call do not prove continuously stable contents or concurrent correctness.",
                           "Diagnostic values are from a pre-IRQ-disable content sample, not an exact iteration observation; several equal samples do not prove continuous stability.",
                           "No claim that the original early-acquisition predicate was evaluated; optional values are explicitly at a different proposed content boundary.",
                           "Known source/development inputs only; original formal/diagnostic model protocol status is unchanged."]
    except (KeyError, OSError, TypeError, ValueError) as exc:
        result["reasons"].append(str(exc))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--origin", choices=("formal_proposal", "posthoc_diagnostic_not_formal_pass"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    for path in (args.input, args.request):
        if not path.is_file() or not path.resolve().is_relative_to(PREVIOUS):
            parser.error("Only existing prior-stage final/request files may be read")
    if not args.out.resolve().is_relative_to(HERE):
        parser.error("Output must remain in this new stage")
    used = (args.input, args.request, Path(__file__), PREVIOUS / "evaluate_predicates.py")
    fingerprints = {str(path.resolve()): AST.digest(path) for path in used}
    request = json.loads(args.request.read_text(encoding="utf-8-sig"))
    proposal = json.loads(args.input.read_text(encoding="utf-8-sig"))
    result = analyze(request, proposal, args.origin)
    result["input_fingerprints"] = fingerprints
    result["inputs_unchanged"] = all(AST.digest(path) == value for path, value in fingerprints.items())
    if not result["inputs_unchanged"]:
        result["status"] = "insufficient"
        result["reasons"].append("input changed during context binding")
        if "diagnostic_content_projection" in result:
            result["diagnostic_content_projection"].update(status="unmapped", values=[])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "origin": args.origin,
                      "original_event": result["original_event_evaluation"]["status"],
                      "diagnostic_projection": result.get("diagnostic_content_projection", {}).get("status")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
