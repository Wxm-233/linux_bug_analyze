"""Three saved-source development inputs; no Git, model, C execution or repair.

This emits lexical review locations within a human-reviewed control catalogue.
It never proves CFG, effective configuration, hardware semantics or correctness.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import sys

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
IDENT = r"[A-Za-z_][A-Za-z0-9_]*"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def verify_map(base, mapping):
    for relative, expected in mapping.items():
        assert sha((base / relative).read_bytes()) == expected, relative


def load_parser(reference):
    source = HERE / reference["saved"]
    assert sha(source.read_bytes()) == reference["sha256"]
    spec = importlib.util.spec_from_file_location("frozen_config_lexical_parser", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # imports definitions; never invokes its main()
    return module


def load_text(reference):
    raw = (HERE / reference["saved"]).read_bytes()
    assert sha(raw) == reference["sha256"]
    return raw.decode("utf-8")


def boundaries():
    return {"effective_configuration_binding": "unknown", "actual_build_path": "unknown",
            "actual_execution_path": "unknown", "hardware_mode_contract": "unknown",
            "downstream_consumer_contract": "unknown", "guard_domination_proven": False,
            "consumer_semantics_proven": False, "automatic_replacement": None,
            "runtime_error_certified": False, "compile_error_certified": False}


def find_unique_line(masked_lines, first, last, pattern):
    """Only whole standalone masked code lines, not substrings of operation_lines."""
    matches = []
    for line in range(first, last + 1):
        match = re.fullmatch(pattern, masked_lines[line - 1].strip())
        if match:
            matches.append((line, match))
    return matches[0] if len(matches) == 1 else None


def branch_chain(parser, text, masked_lines, branch, register, mask, set_bit):
    first, last = branch["quote"]["start_line"], branch["quote"]["end_line"]
    op = r"\|=" if set_bit else r"&="
    negate = "" if set_bit else r"~\s*"
    change = find_unique_line(masked_lines, first, last,
                             rf"({IDENT})\s*{op}\s*{negate}{re.escape(mask)}\s*;")
    if change is None:
        return None
    carrier = change[1].group(1)
    reg, var, bit = re.escape(register), re.escape(carrier), re.escape(mask)
    write = find_unique_line(masked_lines, first, last, rf"reg_write\s*\(\s*{reg}\s*,\s*{var}\s*\)\s*;")
    readback = find_unique_line(masked_lines, first, last, rf"{var}\s*=\s*reg_read\s*\(\s*{reg}\s*\)\s*;")
    check_pattern = (rf"if\s*\(\s*!\s*\(\s*{var}\s*&\s*{bit}\s*\)\s*\)\s*\{{" if set_bit else
                     rf"if\s*\(\s*{var}\s*&\s*{bit}\s*\)\s*\{{")
    # More than one bit check is common (initial-state check and readback check).
    # Restrict the latter by source order after the unique readback, not by CFG.
    check = None if readback is None else find_unique_line(masked_lines, readback[0] + 1, last, check_pattern)
    error = None if check is None else find_unique_line(masked_lines, check[0] + 1, last, r"return\s+-\s*EOPNOTSUPP\s*;")
    if any(item is None for item in [write, readback, check, error]):
        return None
    if not change[0] < write[0] < readback[0] < check[0] < error[0]:
        return None
    return {"carrier": carrier, "change_quote": parser.quote_lines(text, change[0], change[0]),
            "write_quote": parser.quote_lines(text, write[0], write[0]),
            "readback_quote": parser.quote_lines(text, readback[0], readback[0]),
            "check_quote": parser.quote_lines(text, check[0], check[0]),
            "error_quote": parser.quote_lines(text, error[0], error[0]),
            "branch_quote": parser.quote_lines(text, first, last)}


def mode_operation(parser, text, masked_lines, guard, control):
    if guard["else"] is None:
        return None
    register, mask = control["register"], control["mask"]
    positive = branch_chain(parser, text, masked_lines, guard["then"], register, mask, True)
    negative = branch_chain(parser, text, masked_lines, guard["else"], register, mask, False)
    if positive is None or negative is None or positive["carrier"] != negative["carrier"]:
        return None
    line = guard["guard_quote"]["start_line"]
    carrier = positive["carrier"]
    initial_pattern = rf"{re.escape(carrier)}\s*=\s*reg_read\s*\(\s*{re.escape(register)}\s*\)\s*;"
    initial = None
    if line > 1 and re.fullmatch(initial_pattern, masked_lines[line - 2].strip()):
        initial = parser.quote_lines(text, line - 1, line - 1)
    return {"register": register, "mask": mask, "carrier": carrier,
            "property_role": control["property_role"],
            "property_association_status": control["association_status"],
            "association_automatically_inferred": False,
            "guard_quote": parser.quote_lines(text, line, line), "initial_read_quote": initial,
            "then_branch_quote": positive["branch_quote"], "else_branch_quote": negative["branch_quote"],
            "set_quote": positive["change_quote"], "clear_quote": negative["change_quote"],
            "then_write_quote": positive["write_quote"], "else_write_quote": negative["write_quote"],
            "then_readback_quote": positive["readback_quote"], "else_readback_quote": negative["readback_quote"],
            "then_readback_check_quote": positive["check_quote"], "else_readback_check_quote": negative["check_quote"],
            "then_error_return_quote": positive["error_quote"], "else_error_return_quote": negative["error_quote"],
            "syntax_relationship_only": True, "cfg_certified": False}


def extract_input(parser, reference, control_catalog, declarations):
    text = load_text(reference)
    facts = parser.c_facts(text)
    masked = parser.mask_c(text)
    masked_lines = masked.splitlines()
    symbols = [r["symbol"] for r in facts["references"]]
    evidence = [d for d in declarations if "CONFIG_" + d["symbol"] in symbols]
    guards = facts["supported_guards"]
    operations = []
    mode_seen = False
    for guard in guards:
        start, end = guard["whole_if_quote"]["start_offset"], guard["whole_if_quote"]["end_offset_exclusive"]
        region = masked[start:end]
        for control in control_catalog["controls"]:
            # Co-occurrence can trigger review even when the strict template fails.
            if re.search(r"\breg_write\s*\(", region) and re.search(r"\b" + re.escape(control["mask"]) + r"\b", region):
                mode_seen = True
            operation = mode_operation(parser, text, masked_lines, guard, control)
            if operation is not None:
                operations.append((guard, operation))
    candidates = []
    for guard, operation in operations:
        guard_evidence = [d for d in evidence if d["symbol"] == guard["symbol"].removeprefix("CONFIG_")]
        candidates.append({"kind": "property_basis_and_mode_operation_review", "source": reference,
                           "config_reference": guard["symbol"], "declaration_evidence": guard_evidence,
                           "declaration_evidence_status": "observed_in_saved_material" if guard_evidence else "unobserved_in_saved_material",
                           "controlled_operation": operation, "boundaries": boundaries(),
                           "verdict": "needs_source_review", "association_catalog": "control_catalog.json",
                           "suggested_check": {"condition": "actual_path_entered_and_successful_mode_region_exit",
                               "obligation": "final_mode_matches_independently_verified_environment_property",
                               "placement": "after_readback_or_no_write_path_before_downstream_use",
                               "placement_certified": False, "first_actual_consumer": None,
                               "error_or_unexecuted_path_counts_as_success": False},
                           "support_scope": "standalone_lexical_set_clear_write_readback_errno_chain_only"})
    decision = "needs_source_review" if candidates else ("insufficient_supported_mode_chain" if mode_seen else
               "insufficient_guard_form" if facts["unsupported_guards"] else "not_applicable_no_mode_operation")
    operation = operations[0][1] if len(operations) == 1 else None
    positions = [] if operation is None else [
        {"role": "property_config_predicate", "line": operation["guard_quote"]["start_line"]},
        {"role": "then_mode_write", "line": operation["then_write_quote"]["start_line"]},
        {"role": "else_mode_write", "line": operation["else_write_quote"]["start_line"]}]
    return {"id": reference["id"], "source": reference, "config_references": symbols,
            "supported_direct_braced_guard_count": len(guards),
            "config_guard_quote": parser.quote_lines(text, guards[0]["guard_quote"]["start_line"],
                                                      guards[0]["guard_quote"]["start_line"]) if len(guards) == 1 else None,
            "candidate_count": len(candidates), "decision": decision,
            "declaration_evidence_status": "observed_in_saved_material" if evidence else "unobserved_in_saved_material",
            "declaration_evidence_count": len(evidence), "declaration_evidence": evidence,
            "absence_scope": "only_two_saved_Kconfig_materials_not_global_Kconfig_absence",
            "mode_operation_observed": mode_seen, "historical_true_negative": False,
            "independent_detection_case": False, "boundaries": boundaries(),
            "controlled_operation": operation, "review_positions": positions, "candidates": candidates,
            "unsupported_guards": facts["unsupported_guards"], "parser_translation_phase_complete": False,
            "reason": "Emit source review locations only; no mode operation means this template does not apply, not a correctness or relevance verdict."}


def differences(actual, expected, prefix=""):
    """Compare all substantive predeclared fields; prose reason is explanatory."""
    errors = []
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [{"field": prefix.rstrip("."), "observed": actual, "expected_type": "object"}]
        for key, value in expected.items():
            if key == "reason":
                continue
            if key not in actual:
                errors.append({"field": prefix + key, "missing": True})
            else:
                errors.extend(differences(actual[key], value, prefix + key + "."))
    elif isinstance(expected, list):
        if not isinstance(actual, list):
            return [{"field": prefix.rstrip("."), "observed": actual, "expected_type": "array"}]
        if len(actual) != len(expected):
            errors.append({"field": prefix, "observed_length": len(actual), "expected_length": len(expected)})
        else:
            for index, value in enumerate(expected):
                errors.extend(differences(actual[index], value, prefix + str(index) + "."))
    elif actual != expected:
        errors.append({"field": prefix.rstrip("."), "observed": actual, "expected": expected})
    return errors


def main():
    pre = read_json(HERE / "implementation_pre.json")
    verify_map(HERE, pre["files"])
    verify_map(HERE, pre["reused_files"])
    inputs = read_json(HERE / "inputs.json")
    assert len(inputs["inputs"]) == inputs["maximum_inputs"] == 3
    run = HERE / "runs" / "initial"
    run.mkdir(parents=True, exist_ok=False)
    parser = load_parser(next(r for r in inputs["helper_and_parser"] if r["kind"] == "frozen_parser"))
    catalog = read_json(HERE / "control_catalog.json")
    wanted = {control["subject_property_reference"].removeprefix("CONFIG_") for control in catalog["controls"]}
    for item in inputs["inputs"]:
        wanted.update(match.group().removeprefix("CONFIG_") for match in parser.CONFIG_TOKEN.finditer(parser.mask_c(load_text(item))))
    declarations = []
    for reference in inputs["kconfig_sources"]:
        facts = parser.kconfig_facts(load_text(reference), wanted)
        for d in facts["declarations"]:
            declarations.append({"source": reference, "symbol": d["symbol"], "item_quote": d["item_quote"],
                                 "kconfig_value_proven": False})
    rows = [extract_input(parser, item, catalog, declarations) for item in inputs["inputs"]]
    observations = {"phase": "first_candidate_extraction_before_oracle_comparison", "rows": rows,
                    "c_facts_calls": 3, "kconfig_facts_calls": 2, "new_confirmed_cases": 0,
                    "independent_positive_cases": 0, "Git_commands": 0, "C_compilations": 0}
    save_json(run / "observations.json", observations)
    # Read the sealed independent expectation only after saving actual observations.
    oracle = read_json(HERE / "oracle_pre/expectations.json")
    actual = {r["id"]: r for r in rows}
    comparisons = []
    for row in oracle["rows"]:
        errors = differences(actual[row["id"]], row["expected"])
        comparisons.append({"id": row["id"], "oracle_agreement": not errors, "differences": errors})
    result = {"input_count": len(rows), "candidate_counts": [r["candidate_count"] for r in rows],
              "decisions": [r["decision"] for r in rows], "oracle_agreements": sum(r["oracle_agreement"] for r in comparisons),
              "comparisons": comparisons, "implementation_pre_sha256": sha((HERE / "implementation_pre.json").read_bytes()),
              "scope": "reviewed_catalog_lexical_development_not_unknown_defect_detection"}
    save_json(run / "results.json", result)
    print(json.dumps({k: result[k] for k in ["input_count", "candidate_counts", "decisions", "oracle_agreements"]}))
    assert result["oracle_agreements"] == 3, "Mismatch saved; do not change first observations or expectations"


if __name__ == "__main__":
    main()
