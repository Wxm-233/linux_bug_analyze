"""Bounded lexical facts from saved source; no Git, preprocessing, CFG or repair.

The only supported C guard is if (IS_ENABLED(CONFIG_name)) { ... }, with an
optional braced else. Its blocks are lexical ranges, not executable paths.
"""
from pathlib import Path
import hashlib
import json
import re

BASE = Path(__file__).resolve().parent
PARENT = "7ff730ca458e841dbcdc87f264d7afe3eaed525e"
CONFIG_TOKEN = re.compile(r"\bCONFIG_[A-Za-z_][A-Za-z0-9_]*\b")
KCOMMAND = re.compile(r"^(\s*)(mainmenu|menuconfig|config|source|rsource|osource|orsource|choice|endchoice|menu|endmenu|comment|if|endif)\b")
DECLARATION = re.compile(r"^(\s*)(menuconfig|config)\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:#.*)?$")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def save(name, value):
    (BASE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def source_identity(item):
    return {key: item[key] for key in ("path", "revision", "saved", "blob", "sha256", "bytes")}


def quote_lines(text, begin, end):
    lines = text.splitlines()
    assert 1 <= begin <= end <= len(lines)
    return {"start_line": begin, "end_line": end, "text": "\n".join(lines[begin - 1:end])}


def at_line(text, offset):
    return text.count("\n", 0, offset) + 1


def span_quote(text, begin, end):
    assert 0 <= begin < end <= len(text)
    return {"start_offset": begin, "end_offset_exclusive": end,
            "start_line": at_line(text, begin), "end_line": at_line(text, end - 1),
            "text": text[begin:end]}


def mask_c(text):
    """Replace comments and literal contents with spaces, preserving offsets.

    Escaped newlines in // comments and in literals are retained as newlines.
    Unterminated comments/literals are conservatively masked to EOF.
    """
    result = list(text)
    i = 0
    while i < len(text):
        if text.startswith("//", i):
            start = i
            i += 2
            while i < len(text):
                if text[i] == "\n" and (i == 0 or text[i - 1] != "\\"):
                    break
                i += 1
            for k in range(start, i):
                if result[k] not in "\r\n": result[k] = " "
        elif text.startswith("/*", i):
            start = i
            close = text.find("*/", i + 2)
            i = len(text) if close < 0 else close + 2
            for k in range(start, i):
                if result[k] not in "\r\n": result[k] = " "
        elif text[i] in "\"'":
            delim = text[i]
            start = i
            i += 1
            while i < len(text):
                if text[i] == "\\":
                    i = min(len(text), i + 2)
                elif text[i] == delim:
                    i += 1
                    break
                else:
                    i += 1
            for k in range(start, i):
                if result[k] not in "\r\n": result[k] = " "
        else:
            i += 1
    return "".join(result)


def matching(masked, opening, left, right):
    assert masked[opening] == left
    depth = 0
    for pos in range(opening, len(masked)):
        if masked[pos] == left: depth += 1
        elif masked[pos] == right:
            depth -= 1
            if depth == 0: return pos
    return None


def skip_space(masked, pos):
    while pos < len(masked) and masked[pos].isspace(): pos += 1
    return pos


def lexical_operations(text, masked, begin, end):
    """Original nonempty code lines; no semantic classification is certified."""
    output = []
    original_lines = text.splitlines()
    masked_lines = masked.splitlines()
    first, last = at_line(text, begin), at_line(text, end - 1)
    for line in range(first, last + 1):
        visible = masked_lines[line - 1].strip()
        if not visible or visible in ("{", "}") or re.match(r"^(if\s*\(|}\s*else\b|else\b)", visible):
            continue
        output.append({"kind": "lexical_nonempty_code_line", "line": line,
                       "quote": original_lines[line - 1], "executed": None})
    return output


def c_facts(text):
    masked = mask_c(text)
    references = []
    for match in CONFIG_TOKEN.finditer(masked):
        line = at_line(text, match.start())
        references.append({"symbol": match.group(), "offset": match.start(),
                           "quote": quote_lines(text, line, line),
                           "kind": "lexical_identifier_reference", "actually_reachable": None})
    guards, unsupported = [], []
    for match in re.finditer(r"\bif\s*\(", masked):
        opening = masked.find("(", match.start(), match.end())
        close = matching(masked, opening, "(", ")")
        if close is None:
            if CONFIG_TOKEN.search(masked[opening:]):
                unsupported.append({"reason": "unbalanced_condition", "line": at_line(text, match.start())})
            continue
        condition = masked[opening + 1:close]
        symbols = [m.group() for m in CONFIG_TOKEN.finditer(condition)]
        if not symbols: continue
        condition_quote = span_quote(text, opening + 1, close)
        exact = re.fullmatch(r"\s*IS_ENABLED\s*\(\s*(CONFIG_[A-Za-z_][A-Za-z0-9_]*)\s*\)\s*", condition)
        if exact is None:
            unsupported.append({"reason": "unsupported_condition_form", "symbols": symbols,
                                "condition_quote": condition_quote})
            continue
        body_start = skip_space(masked, close + 1)
        if body_start >= len(masked) or masked[body_start] != "{":
            unsupported.append({"reason": "then_not_braced", "symbols": symbols,
                                "condition_quote": condition_quote})
            continue
        body_end = matching(masked, body_start, "{", "}")
        if body_end is None:
            unsupported.append({"reason": "unbalanced_then", "symbols": symbols,
                                "condition_quote": condition_quote})
            continue
        after = skip_space(masked, body_end + 1)
        else_quote = None
        else_ops = []
        end = body_end + 1
        if re.match(r"else\b", masked[after:]):
            else_start = skip_space(masked, after + 4)
            if else_start >= len(masked) or masked[else_start] != "{":
                unsupported.append({"reason": "else_not_braced", "symbols": symbols,
                                    "condition_quote": condition_quote})
                continue
            else_end = matching(masked, else_start, "{", "}")
            if else_end is None:
                unsupported.append({"reason": "unbalanced_else", "symbols": symbols,
                                    "condition_quote": condition_quote})
                continue
            else_quote = span_quote(text, else_start, else_end + 1)
            else_ops = lexical_operations(text, masked, else_start, else_end + 1)
            end = else_end + 1
        guards.append({"symbol": exact.group(1), "support": "direct_braced_is_enabled_if",
                       "condition_quote": condition_quote,
                       "guard_quote": span_quote(text, match.start(), close + 1),
                       "whole_if_quote": span_quote(text, match.start(), end),
                       "then": {"quote": span_quote(text, body_start, body_end + 1),
                                "condition_polarity": "IS_ENABLED result true",
                                "operation_lines": lexical_operations(text, masked, body_start, body_end + 1)},
                       "else": None if else_quote is None else {"quote": else_quote,
                                "condition_polarity": "IS_ENABLED result false", "operation_lines": else_ops},
                       "cfg_certified": False, "preprocessor_value_certified": False,
                       "actual_execution_certified": False, "enclosing_conditions_certified": False})
    return {"references": references, "supported_guards": guards, "unsupported_guards": unsupported,
            "scope": "restricted_lexical_only", "translation_phase_splicing_complete": False,
            "function_or_cfg_analysis": False, "comments_and_literals_masked": True}


def kconfig_facts(text, wanted):
    """Literal declarations/items from complete saved files, no Kconfig solver."""
    lines = text.splitlines()
    commands = []
    sources = []
    help_indent = None
    for index, line in enumerate(lines):
        if not line.strip(): continue
        indent = len(line) - len(line.lstrip())
        width = len(line[:indent].expandtabs(8))
        if help_indent is not None:
            if width > help_indent: continue
            help_indent = None
        if re.match(r"^\s*(help|---help---)\s*(?:#.*)?$", line):
            help_indent = width
            continue
        command = KCOMMAND.match(line)
        if command:
            commands.append((index, command.group(2), width))
            if command.group(2) in ("source", "rsource", "osource", "orsource"):
                sources.append({"directive": command.group(2), "quote": quote_lines(text, index + 1, index + 1),
                                "resolved_or_loaded": False})
    declarations = []
    for command_index, (index, kind, width) in enumerate(commands):
        if kind not in ("config", "menuconfig"): continue
        declaration = DECLARATION.match(lines[index])
        if declaration is None: continue
        symbol = declaration.group(3)
        if symbol not in wanted: continue
        end = len(lines)
        for next_index, _, next_width in commands[command_index + 1:]:
            if next_width <= width:
                end = next_index
                break
        while end > index + 1 and not lines[end - 1].strip(): end -= 1
        fields = []
        in_help = False
        for field_index in range(index + 1, end):
            entry = lines[field_index]
            if re.match(r"^\s*(help|---help---)\s*(?:#.*)?$", entry): in_help = True
            if in_help: continue
            if re.match(r"^\s*(bool|tristate|string|int|hex|depends on|select|imply|default|def_bool|def_tristate|prompt|range)\b", entry):
                fields.append(quote_lines(text, field_index + 1, field_index + 1))
        declarations.append({"symbol": symbol, "kind": kind,
                             "declaration_quote": quote_lines(text, index + 1, index + 1),
                             "item_quote": quote_lines(text, index + 1, end), "property_line_quotes": fields,
                             "complete_saved_file_available": True,
                             "kconfig_context_resolved": False, "value_or_reachability_certified": False})
    return {"declarations": declarations, "source_directives": sources,
            "semantics": "literal_items_only_not_full_Kconfig_parse", "solver_run": False}


def read_queries(receipts, manifest):
    queries = []
    for receipt in receipts[1:]:
        label = receipt["label"]
        raw = (BASE / "raw" / (label + ".stdout.bin")).read_bytes()
        assert digest(raw) == receipt["stdout_sha256"]
        assert receipt["exit"] in (0, 1)
        hits = []
        for line in raw.decode("utf8").splitlines():
            match = re.fullmatch(r"([0-9a-f]{40}):(.+):(\d+):(.*)", line)
            assert match and match.group(1) == manifest["parent"]
            hits.append({"revision": match.group(1), "path": match.group(2),
                         "line": int(match.group(3)), "text": match.group(4),
                         "evidence_kind": "grep_hit_only", "complete_definition_text_available": any(
                             item["path"] == match.group(2) and item["status"] == "available" for item in manifest["sources"])})
        queries.append({"label": label, "argv": receipt["argv"], "exit": receipt["exit"],
                        "stdout_sha256": receipt["stdout_sha256"], "hit_count": len(hits), "hits": hits,
                        "truncated": False, "query_complete_for_all_kconfig_syntax": False,
                        "generated_outputs_or_external_definitions_covered": False})
    return queries


def run_probes(inputs):
    assert len(inputs["probes"]) <= 8
    results = []
    for probe in inputs["probes"]:
        if probe["kind"] == "c":
            actual = c_facts(probe["text"])
            summary = {"reference_symbols": [r["symbol"] for r in actual["references"]],
                       "supported_guard_count": len(actual["supported_guards"]),
                       "unsupported_reasons": [r["reason"] for r in actual["unsupported_guards"]]}
        else:
            assert probe["kind"] == "kconfig"
            actual = kconfig_facts(probe["text"], set(probe["wanted"]))
            summary = {"declaration_symbols": [r["symbol"] for r in actual["declarations"]],
                       "item_quotes": [r["item_quote"]["text"] for r in actual["declarations"]]}
        results.append({"id": probe["id"], "kind": probe["kind"], "expected": probe["expected"],
                        "actual_summary": summary, "passed": summary == probe["expected"], "facts": actual})
    return {"kind": "synthetic_implementation_probes_not_cases", "count": len(results),
            "passed": sum(r["passed"] for r in results), "results": results}


def main():
    # This entry point cannot be run before its implementation/expected inputs seal.
    pre = json.loads((BASE / "implementation_pre.json").read_text(encoding="utf8"))
    assert pre["phase"] == "pre_first_extraction"
    for name, expected in pre["files"].items():
        assert digest((BASE / name).read_bytes()) == expected, (name, "pre seal mismatch")
    manifest = json.loads((BASE / "retrieval_manifest.json").read_text(encoding="utf8"))
    assert manifest["parent"] == PARENT and len(manifest["sources"]) == 8
    identities, loaded = [], {}
    for item in manifest["sources"]:
        assert item["revision"] == PARENT and item["status"] == "available"
        raw = (BASE / item["saved"]).read_bytes()
        assert digest(raw) == item["sha256"] and len(raw) == item["bytes"]
        assert hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == item["blob"]
        loaded[item["path"]] = raw.decode("utf8")
        identities.append(source_identity(item))
    c = c_facts(loaded[manifest["target"]])
    target_item = next(s for s in identities if s["path"] == manifest["target"])
    c["source"] = target_item
    wanted = {"BIG_ENDIAN", "CPU_BIG_ENDIAN", "I3C", "MIPI_I3C_HCI"}
    configs = []
    for item in identities:
        if "Kconfig" in Path(item["path"]).name:
            facts = kconfig_facts(loaded[item["path"]], wanted)
            facts["source"] = item
            configs.append(facts)
    receipts = json.loads((BASE / manifest["receipts"]).read_text(encoding="utf8"))
    queries = read_queries(receipts, manifest)
    candidates = []
    declaration_hits = queries[0]["hits"]
    for guard in c["supported_guards"]:
        symbol = guard["symbol"].removeprefix("CONFIG_")
        related = [h for h in declaration_hits if re.fullmatch(r"(?:menu)?config\s+" + re.escape(symbol), h["text"])]
        if not related:
            candidates.append({"kind": "config_property_source_insufficient", "symbol": guard["symbol"],
                               "guard_quote": guard["guard_quote"], "verdict": "needs_source_review",
                               "basis": "no_matching_declaration_in_frozen_exact_query",
                               "query_complete_for_all_kconfig_syntax": False,
                               "automatic_replacement": None, "runtime_or_compile_error_certified": False,
                               "property_contract_certified": False})
    facts = {"parent": PARENT, "scope": "message_informed_development", "source_identities": identities,
             "c": c, "kconfig": configs, "queries": queries, "candidates": candidates,
             "unknowns": ["actual_configuration", "generated_config_headers", "external_defines",
                          "build_reachability", "full_preprocessor_semantics", "enclosing_control_flow",
                          "hardware_property_contract", "runtime_execution"],
             "new_confirmed_cases": 0, "independent_positive_cases": 0,
             "repair_patch_read": False, "new_git_commands": 0}
    inputs = json.loads((BASE / "probe_inputs.json").read_text(encoding="utf8"))
    probes = run_probes(inputs)
    save("facts.json", facts)
    save("probe_results.json", probes)
    assert probes["passed"] == probes["count"], "Saved mismatching probe results: do not alter first run silently"
    print(json.dumps({"source_count": len(identities), "references": len(c["references"]),
                      "supported_guards": len(c["supported_guards"]), "candidates": len(candidates),
                      "probe_passed": probes["passed"], "probe_count": probes["count"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
