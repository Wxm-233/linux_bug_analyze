"""Neutral, deliberately narrow AST-to-archived-observation adapter.

No oracle, prior registered predicate, non-final model reasoning, API or kernel
runner is read.  The old replay module supplies archival foundation checks only;
its status/predicates are discarded.  Successful projection is not synthesis or
a proof that the candidate is a necessary condition.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASE_ROOT = HERE.parent
REPLAY = CASE_ROOT / "arch_witness_checks_20261014/first_use_replay.py"
OLD = "88b604263f3d6eedae0b1c2c3bbd602d1e2e8775"
REVISIONS = {"old": OLD, "fixed": "a052096bdd6809eeab809202726634d1ac975aa1"}
ARITIES = {"contains": (2, 2), "nonempty": (1, 1), "eq": (2, 2),
           "ne": (2, 2), "lt": (2, 2), "le": (2, 2), "gt": (2, 2),
           "ge": (2, 2), "and": (2, 4), "or": (2, 4), "not": (1, 1),
           "precedes": (2, 2)}
FUNCTIONS = ("sched_core_cpu_starting", "sched_core_lock")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(text):
    return re.sub(r"\s+", "", text).rstrip(";")


def supplied_documents(request):
    if request.get("revision") != OLD:
        raise ValueError("request is outside the fixed old-source revision")
    out = {}
    for doc in request["documents"]:
        if doc["id"] in out or not isinstance(doc.get("path"), str):
            raise ValueError("duplicate document or invalid path")
        lo, hi = doc["start_line"], doc["end_line"]
        if type(lo) is not int or type(hi) is not int or lo < 1 or hi < lo:
            raise ValueError("invalid supplied source interval")
        lines = {}
        for line in doc["text"].splitlines():
            match = re.fullmatch(r"\s*(\d+): ?(.*)", line)
            if not match or int(match[1]) in lines:
                raise ValueError("invalid original numbered source")
            lines[int(match[1])] = match[2]
        if list(lines) != list(range(lo, hi + 1)):
            raise ValueError("noncontiguous supplied source")
        out[doc["id"]] = (doc, lines)
    return out


def extract(index, refs):
    if not isinstance(refs, list):
        raise ValueError("evidence is not a list")
    rows = []
    for ref in refs:
        if not isinstance(ref, dict) or ref.get("document") not in index:
            raise ValueError("unknown evidence document")
        doc, lines = index[ref["document"]]
        lo, hi = ref.get("start_line"), ref.get("end_line")
        if type(lo) is not int or type(hi) is not int or hi < lo or any(n not in lines for n in range(lo, hi + 1)):
            raise ValueError("reference outside supplied source")
        rows.append({"document": doc["id"], "path": doc["path"], "kind": doc["kind"],
                     "start_line": lo, "end_line": hi,
                     "source_text": "\n".join(lines[n] for n in range(lo, hi + 1))})
    return rows


def check_rows(index, check):
    rows = []
    for key in ("providers", "configuration"):
        if not isinstance(check.get(key), list):
            raise ValueError("missing " + key + " evidence block")
        for entry in check[key]:
            rows.extend(extract(index, entry.get("evidence")))
    consumer = check.get("consumer")
    if not isinstance(consumer, dict):
        raise ValueError("consumer must be an object")
    rows.extend(extract(index, consumer.get("evidence")))
    rows.extend(extract(index, check.get("evidence")))
    return rows


def source_scope(rows):
    archs = sorted({m[1] for row in rows if row["kind"] == "source"
                    and (m := re.match(r"^arch/(x86|s390)/", row["path"]))})
    configs = {}
    for arch, arch_key in (("x86", "CONFIG_X86_64"), ("s390", "CONFIG_S390")):
        found = []
        for row in rows:
            if row["kind"] != "configuration":
                continue
            values = dict(re.findall(r"^(CONFIG_\w+)=(.*)$", row["source_text"], re.M))
            values.update({key: "n" for key in re.findall(r"^# (CONFIG_\w+) is not set$", row["source_text"], re.M)})
            if values.get(arch_key) == "y":
                required = ("CONFIG_SMP", "CONFIG_SCHED_SMT", "CONFIG_SCHED_CORE") + (("CONFIG_SCHED_TOPOLOGY",) if arch == "s390" else ())
                found.append("disabled" if any(values.get(k) == "n" for k in required) else
                             "enabled" if all(values.get(k) == "y" for k in required) else "missing")
        # Repeated identical evidence is harmless; contradictory sources remain unknown.
        configs[arch] = found[0] if found and len(set(found)) == 1 else "missing_or_ambiguous"
    return {"provider_architectures_cited": archs, "configuration_cited": configs,
            "classification": "cross_arch_source_candidate" if archs == ["s390", "x86"]
                and all(v == "enabled" for v in configs.values()) else "local_or_conditional_candidate",
            "semantic_provider_relation_proved": False,
            "note": "Cited architecture/configuration coverage is separate from AST projection; path/keywords alone do not prove causality."}


def validate_ast(node, depth=1, counter=None):
    counter = [0] if counter is None else counter
    counter[0] += 1
    if depth > 5 or counter[0] > 32 or not isinstance(node, dict):
        raise ValueError("AST depth, size or node type invalid")
    if set(node) == {"symbol"}:
        if not isinstance(node["symbol"], str) or not 0 < len(node["symbol"]) <= 160:
            raise ValueError("invalid symbol")
    elif set(node) == {"literal"}:
        value = node["literal"]
        if type(value) not in (int, float, bool, str) or isinstance(value, str) and len(value) > 100:
            raise ValueError("invalid literal")
        if type(value) is float and not math.isfinite(value):
            raise ValueError("nonfinite literal")
    elif set(node) == {"op", "args"}:
        op, args = node["op"], node["args"]
        if op not in ARITIES or not isinstance(args, list) or not ARITIES[op][0] <= len(args) <= ARITIES[op][1]:
            raise ValueError("invalid operator or arity")
        for child in args:
            validate_ast(child, depth + 1, counter)
    else:
        raise ValueError("unknown AST fields")


def symbols(node):
    if "symbol" in node:
        return {node["symbol"]}
    return set().union(*(symbols(n) for n in node.get("args", [])))


def cited_scope(rows, function):
    """Only contiguous, actually cited source can establish a lexical function.

    This is a two-function recognizer, not a general C parser.  It refuses a
    missing function header; gaps cannot be bridged by unrelated material.
    """
    lines = {}
    for row in rows:
        if row["kind"] == "source" and row["path"] == "kernel/sched/core.c":
            for number, text in enumerate(row["source_text"].splitlines(), row["start_line"]):
                if number in lines and lines[number] != text:
                    raise ValueError("contradictory cited source line")
                lines[number] = text
    starts = [n for n, text in lines.items() if re.search(r"\b(?:static\s+)?void\s+" + re.escape(function) + r"\s*\(.*\b(?:int|unsigned\s+int)\s+cpu\b", text)]
    if len(starts) != 1:
        raise ValueError("cited consumer function signature/cpu parameter missing or ambiguous")
    start = starts[0]
    selected = []
    balance, opened = 0, False
    number = start
    while number in lines:
        text = lines[number]
        selected.append((number, text))
        balance += text.count("{") - text.count("}")
        opened = opened or "{" in text
        if opened and balance <= 0:
            break
        number += 1
    if not opened:
        raise ValueError("consumer opening brace not cited")
    return selected


def bind_symbols(check, rows):
    consumer = check["consumer"]
    function = consumer.get("function")
    if function not in FUNCTIONS:
        raise ValueError("consumer function has no archived first-consumer projection")
    scope = cited_scope(rows, function)
    text = "\n".join(line for _, line in scope)
    anchor, event = consumer.get("anchor"), consumer.get("event")
    if not isinstance(anchor, str) or not canonical(anchor):
        raise ValueError("missing consumer anchor")
    ca, ct = canonical(anchor), canonical(text)
    if ca not in ct:
        raise ValueError("consumer anchor is not in the cited lexical function")
    # No event is manufactured for update/notify, and entry is not silently
    # interpreted as first_read.  These anchors correspond to the observed
    # interval through sched_core_lock's first mask use.
    allowed = {("sched_core_cpu_starting", "before_call", "sched_core_lock(cpu,&flags)"),
               ("sched_core_cpu_starting", "first_read", "cpu_smt_mask(cpu)"),
               ("sched_core_lock", "first_read", "cpu_smt_mask(cpu)"),
               ("sched_core_lock", "first_read", "for_each_cpu(t,smt_mask)")}
    if (function, event, ca) not in allowed:
        raise ValueError("consumer event/anchor has no exact archived first-read binding")
    alias = "conststructcpumask*smt_mask=cpu_smt_mask(cpu);" in re.sub(r"\s+", "", text)
    needed = symbols(check["predicate"])
    bindings, failures = {}, []
    for raw in sorted(needed):
        symbol = canonical(raw)
        kind = None
        if symbol == "cpu":
            kind = "target_cpu"
        elif symbol == "cpu_smt_mask(cpu)" and symbol in ct:
            kind = "cpu_set"
        elif symbol == "smt_mask" and alias:
            kind = "cpu_set"
        elif symbol == "cpumask_weight(smt_mask)" and alias and symbol in ct:
            kind = "weight"
        elif symbol == "cpu_online(cpu)" and symbol in ct:
            kind = "online"
        if kind is None:
            failures.append("unsupported or uncited same-scope symbol: " + raw)
            continue
        bindings[raw] = {"kind": kind, "function": function, "phase": "lock_snapshot",
                         "evidence": [{"path": "kernel/sched/core.c", "start_line": n, "source_text": line}
                                      for n, line in scope],
                         "observation_basis": "Archive foundation must confirm same CPU, actual first lock snapshot and unchanged mask through first consumption; not name substitution."}
    return bindings, failures


def literal_type(value):
    return "bool" if type(value) is bool else "number" if type(value) in (int, float) else "string"


def infer_type(node, bindings):
    if "literal" in node:
        return literal_type(node["literal"])
    if "symbol" in node:
        kind = bindings[node["symbol"]]["kind"]
        return {"target_cpu": "number", "cpu_set": "cpu_set", "weight": "number", "online": "bool"}[kind]
    op = node["op"]
    types = [infer_type(child, bindings) for child in node["args"]]
    if op == "contains" and types != ["cpu_set", "number"]:
        raise ValueError("contains needs CPU set and numeric member")
    if op == "nonempty" and types != ["cpu_set"]:
        raise ValueError("nonempty needs CPU set")
    if op in ("eq", "ne") and (types[0] != types[1] or types[0] not in ("number", "bool", "string", "cpu_set")):
        raise ValueError("equality operands have incompatible types")
    if op in ("lt", "le", "gt", "ge") and types != ["number", "number"]:
        raise ValueError("ordering requires numeric operands")
    if op in ("and", "or", "not") and any(t != "bool" for t in types):
        raise ValueError("boolean operator needs boolean operands")
    if op == "precedes":
        raise ValueError("precedes endpoints have no independently observed event binding")
    return "bool"


def evaluate_ast(node, values):
    if "literal" in node:
        return node["literal"]
    if "symbol" in node:
        return values[node["symbol"]]
    args = [evaluate_ast(child, values) for child in node["args"]]  # Never short-circuit missing leaves.
    op = node["op"]
    if op == "contains":
        if type(args[1]) is not int:
            raise ValueError("CPU membership target is not an integer")
        return args[1] in args[0]
    if op == "nonempty":
        return bool(args[0])
    if op == "eq": return args[0] == args[1]
    if op == "ne": return args[0] != args[1]
    if op == "lt": return args[0] < args[1]
    if op == "le": return args[0] <= args[1]
    if op == "gt": return args[0] > args[1]
    if op == "ge": return args[0] >= args[1]
    if op == "and": return all(args)
    if op == "or": return any(args)
    if op == "not": return not args[0]
    raise ValueError("unmapped operator")


def archive_from_materials(module, materials):
    """Discard dependency judgments; retain independently validated observations."""
    if len(materials) != 4 or {m["profile"] for m in materials} != set(module.PROFILES):
        raise ValueError("four archival profiles are required")
    pair_checks = {}
    for arch in ("x86", "s390"):
        pair = {m["build"].get("variant"): m for m in materials if m["details"].get("arch") == arch}
        if set(pair) != {"old", "fixed"}:
            raise ValueError("archival architecture/version pair missing")
        differing = [key for key in set(pair["old"]["cfg"]) | set(pair["fixed"]["cfg"])
                     if pair["old"]["cfg"].get(key) != pair["fixed"]["cfg"].get(key)]
        pair_checks[arch] = set(differing) <= {"CONFIG_LOCALVERSION"}
    common = all(len({m["source_hashes"].get(path) for m in materials}) == 1
                 and all(m["source_hashes"].get(path) for m in materials)
                 for path in ("kernel/cpu.c", "kernel/sched/core.c", "arch/x86/kernel/smpboot.c"))
    rows = []
    for material in materials:
        parsed = module.replay(material)
        # Intentionally never inspect parsed['status'], parsed['predicates'],
        # expected observations, or compare an AST value with version labels.
        foundation = dict(parsed.get("foundation", {}))
        first = dict(parsed.get("first_consumption", {}))
        foundation["registered_archival_revision"] = material["build"].get("revision") == REVISIONS.get(material["build"].get("variant"))
        foundation["same_arch_pair_config"] = pair_checks.get(material["details"].get("arch"), False)
        foundation["same_common_original_sources"] = common
        foundation["first_cpu_object_and_phase"] = first.get("cpu") == first.get("current") == 1 and first.get("phase") == "lock_snapshot"
        required_fields = ("mask", "weight", "online")
        foundation["typed_observed_values"] = all(type(first.get(k)) is int for k in required_fields)
        foundation["bounded_mask_and_consistent_weight"] = foundation["typed_observed_values"] and 0 <= first["mask"] < 16 and first["weight"] == first["mask"].bit_count() and first["online"] in (0, 1)
        rows.append({"profile": material["profile"], "arch": material["details"].get("arch"),
                     "revision": material["build"].get("revision"), "foundation": foundation,
                     "failed_foundation": [key for key, value in foundation.items() if value is not True],
                     "first_consumption": {k: first.get(k) for k in ("cpu", "current", "phase", "mask", "weight", "online", "line", "seq")}})
    return rows


def load_archives():
    spec = importlib.util.spec_from_file_location("predicate_archival_foundation", REPLAY)
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    materials = [module.metadata(profile) for profile in module.PROFILES]
    rows = archive_from_materials(module, materials)
    unchanged = all(module.digest((CASE_ROOT / rel).read_bytes()) == value for rel, value in module.INPUTS.items())
    if not unchanged:
        for row in rows:
            row["failed_foundation"].append("archival_inputs_changed")
    return {"rows": rows, "dependency_sha256": digest(REPLAY),
            "input_fingerprints": dict(module.INPUTS), "inputs_unchanged": unchanged,
            "source_binding_limit": "Archived observer/config/build/boot receipts only; no fresh ELF certification."}


def adapt(request, proposal, archive_loader=load_archives):
    result = {"status": "unmapped", "origin": "model_final_ast_with_program_observation_adapter",
              "original_scope": proposal.get("scope") if isinstance(proposal, dict) else None,
              "checks": [], "predicate_rewritten": False, "oracle_read": False,
              "new_boots": 0, "new_builds": 0, "external_calls": 0, "independent_cases": 0,
              "validated_general_detector": False}
    try:
        index = supplied_documents(request)
        checks = proposal.get("checks")
        if not isinstance(checks, list) or len(checks) > 1:
            raise ValueError("expected zero or one final check")
        if not checks:
            result["reasons"] = ["model returned no check"]
            return result
        check = checks[0]
        if not isinstance(check, dict):
            raise ValueError("check must be an object")
        row = {"id": check.get("id"), "predicate": check.get("predicate"),
               "polarity": check.get("polarity"), "authority_status": check.get("authority_status"),
               "status": "unmapped", "bindings": {}, "unmapped_reasons": [], "archived_values": [],
               "semantic_necessity_proved": False}
        result["checks"].append(row)
        refs = check_rows(index, check)
        row["source_scope"] = source_scope(refs)
        if check.get("predicate") is None:
            row["unmapped_reasons"] = ["model predicate is null; no condition inferred from prose"]
            return result
        validate_ast(check["predicate"])
        if check.get("polarity") not in ("must_hold", "alert_if_true"):
            raise ValueError("unknown predicate polarity")
        try:
            bindings, failures = bind_symbols(check, refs)
            row["bindings"] = bindings
            row["unmapped_reasons"] = failures
            if failures:
                return result
            if infer_type(check["predicate"], bindings) != "bool":
                raise ValueError("top-level predicate is not boolean")
            archives = archive_loader()
            row["archival_foundation"] = archives
            if len(archives["rows"]) != 4 or any(r["failed_foundation"] for r in archives["rows"]) or not archives.get("inputs_unchanged"):
                row["unmapped_reasons"] = ["one or more archival foundation checks failed"]
                return result
            for observation in archives["rows"]:
                first = observation["first_consumption"]
                values = {}
                for symbol, binding in bindings.items():
                    values[symbol] = {"target_cpu": first["cpu"],
                                      "cpu_set": {n for n in range(4) if first["mask"] & (1 << n)},
                                      "weight": first["weight"], "online": bool(first["online"])}[binding["kind"]]
                value = evaluate_ast(check["predicate"], values)
                if type(value) is not bool:
                    raise ValueError("nonboolean final value")
                row["archived_values"].append({"profile": observation["profile"], "value": value,
                    "condition_satisfied": value if check["polarity"] == "must_hold" else None,
                    "alert_candidate": not value if check["polarity"] == "must_hold" else value,
                    "bound_values": {key: sorted(val) if isinstance(val, set) else val for key, val in values.items()}})
            row["status"] = result["status"] = "mapped"
            row["limits"] = ["Value projection does not prove candidate necessity or architectural causality.",
                             "Weak conditions are evaluated without strengthening; original AST/polarity retained.",
                             "Known four archived ordinary initial boots; not new runs, real SMT, hotplug, concurrency or unseen detection."]
        except (KeyError, OSError, ValueError, TypeError) as exc:
            row["archived_values"] = []
            row["unmapped_reasons"].append(str(exc))
    except (KeyError, ValueError, TypeError) as exc:
        result["status"] = "invalid"
        result["error"] = str(exc)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    for path in (args.input, args.request):
        if not path.resolve().is_relative_to(HERE) or not path.is_file():
            parser.error("Input/request must be existing files in this experiment stage")
    if not args.out.resolve().is_relative_to(HERE / "mapped"):
        parser.error("Output must remain below this stage's mapped directory")
    before = {str(path.resolve()): digest(path) for path in (args.input, args.request, Path(__file__))}
    request = json.loads(args.request.read_text(encoding="utf-8-sig"))
    proposal = json.loads(args.input.read_text(encoding="utf-8-sig"))
    result = adapt(request, proposal)
    result["input_fingerprints"] = before
    result["inputs_unchanged"] = all(digest(path) == value for path, value in before.items())
    if not result["inputs_unchanged"]:
        result["status"] = "unmapped"
        for row in result["checks"]:
            row.update(status="unmapped", archived_values=[], unmapped_reasons=["inputs changed during adaptation"])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "check_count": len(result["checks"]), "new_boots": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
