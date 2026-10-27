"""Partial, source-bound GIMPLE facts in conservative straight-line regions.

This is neither a GIMPLE interpreter nor a CFG/alias/contract verifier. Opaque
statements and every effect/control boundary remain visible and kill bindings.
"""
from __future__ import annotations
import hashlib
import re

ID = r"[A-Za-z_]\w*(?:\.\d+(?:_\d+)?)?"
LABEL = r"(?:<" + ID + r">|" + ID + r")"
ANNOTATION = re.compile(r"\[([^\]\r\n]+):(\d+):(\d+)\]")
ASM_START = re.compile(r"(?:__asm__|asm)\b(?:\s+(?:__volatile__|__inline__|volatile|inline))*\s*\(")
CAST = re.compile(r"^\(\s*(?:(?:const|volatile|unsigned|signed|long|short)\s+)*(?:(?:int|char|bool|_Bool|float|double|void)|struct\s+" + ID + r")(?:\s*\*)*\s*\)\s*")
WORDS = re.compile(r"(?<![\w.])" + ID + r"(?![\w.])")
TYPES = {"void", "const", "volatile", "unsigned", "signed", "long", "short", "int", "char", "bool", "_Bool", "float", "double", "struct", "union", "enum"}


class ScanError(ValueError):
    pass


def need(condition, reason):
    if not condition: raise ScanError(reason)


def _asm_end(text, start):
    match = ASM_START.match(text, start)
    need(match is not None, "asm_opening_unsupported")
    index, depth, quote = match.end(), 1, None
    while index < len(text):
        char = text[index]
        if quote:
            if char == "\\": index += 2; continue
            if char == quote: quote = None
            index += 1; continue
        if char in {'"', "'"}: quote = char; index += 1; continue
        annotation = ANNOTATION.match(text, index)
        if annotation: index = annotation.end(); continue
        if text.startswith("/*", index):
            end = text.find("*/", index + 2); need(end >= 0, "asm_comment_unterminated"); index = end + 2; continue
        if text.startswith("//", index):
            end = text.find("\n", index + 2); index = len(text) if end < 0 else end + 1; continue
        if char == "(": depth += 1
        if char == ")":
            depth -= 1
            if depth == 0:
                index += 1
                while index < len(text) and text[index] in " \t\r\n": index += 1
                need(index < len(text) and text[index] == ";", "asm_terminal_semicolon_missing")
                return index + 1
        need(depth > 0, "asm_unbalanced_parentheses")
        index += 1
    raise ScanError("asm_incomplete_or_ambiguous_quote_boundary")


def _lexical_view(text):
    mask, spans, annotations, asms = list(text), [], [], {}
    index = 0
    def hide(start, end, kind):
        spans.append({"kind": kind, "start_offset": start, "end_offset": end, "raw": text[start:end]})
        for at in range(start, end):
            if mask[at] not in "\r\n": mask[at] = " "
    while index < len(text):
        start = index
        if text.startswith("/*", index):
            stop = text.find("*/", index + 2); need(stop >= 0, "comment_unterminated")
            index = stop + 2; hide(start, index, "comment"); continue
        if text.startswith("//", index):
            stop = text.find("\n", index + 2); index = len(text) if stop < 0 else stop
            hide(start, index, "comment"); continue
        annotation = ANNOTATION.match(text, index)
        if annotation:
            annotations.append({"start_offset": index, "end_offset": annotation.end(), "path": annotation[1],
                                "line": int(annotation[2]), "column": int(annotation[3])})
            index = annotation.end(); hide(start, index, "source_annotation"); continue
        if ASM_START.match(text, index) and (index == 0 or not (text[index - 1].isalnum() or text[index - 1] == "_")):
            index = _asm_end(text, start); asms[start] = index; hide(start, index, "asm"); continue
        if text[index] in {'"', "'"}:
            quote = text[index]; index += 1
            while index < len(text):
                need(text[index] not in "\r\n", "multiline_literal_outside_asm")
                if text[index] == "\\": need(index + 1 < len(text), "quoted_escape_unterminated"); index += 2
                elif text[index] == quote: index += 1; break
                else: index += 1
            else: raise ScanError("quoted_literal_unterminated")
            hide(start, index, "quoted_literal"); continue
        index += 1
    return "".join(mask), spans, annotations, asms


def _units(text, mask, asms):
    units, start, index, parens, brackets, expression_braces, scopes = [], 0, 0, 0, 0, 0, 0
    def emit(end, forced=None):
        nonlocal start
        if text[start:end].strip(): units.append((start, end, forced))
        start = end
    while index < len(text):
        if index in asms:
            need(not mask[start:index].strip(), "asm_embedded_in_unhandled_statement")
            emit(asms[index], "asm"); index = asms[index]; continue
        char = mask[index]
        if char == "(": parens += 1
        if char == ")": parens -= 1; need(parens >= 0, "unbalanced_statement_parenthesis")
        if char == "[": brackets += 1
        if char == "]": brackets -= 1; need(brackets >= 0, "unbalanced_statement_bracket")
        if not parens and not brackets:
            if char == "{":
                if expression_braces or "=" in mask[start:index]: expression_braces += 1
                else: scopes += 1; emit(index + 1)
            elif char == "}":
                if expression_braces: expression_braces -= 1
                else:
                    need(not mask[start:index].strip(), "unterminated_statement_before_scope_end")
                    scopes -= 1; need(scopes >= 0, "scope_closing_without_opening"); emit(index + 1)
            elif char == ":" and not expression_braces:
                if re.fullmatch(r"\s*" + LABEL + r"\s*:", mask[start:index + 1]): emit(index + 1)
            elif char == ";" and not expression_braces:
                current = " ".join(mask[start:index + 1].split())
                if current.startswith("if ") and "else" not in current and re.match(r"\s*else\b", mask[index + 1:]):
                    pass
                else: emit(index + 1)
        index += 1
    need(parens == brackets == expression_braces == scopes == 0, "incomplete_statement_or_scope")
    if text[start:].strip(): units.append((start, len(text), "opaque"))
    return units


def _ids(expression):
    return list(dict.fromkeys(word for word in WORDS.findall(expression) if word not in TYPES))


def _pure(expression):
    # Only a small side-effect-free scalar token grammar. In particular this
    # does not erase unknown dereferences, nested calls or increment operators.
    if not expression.strip() or re.search(r"\+\s*\+|-\s*-", expression): return False
    token = re.compile(ID + r"|\d+(?:B|[uUlL]+)?|==|!=|<=|>=|<<|>>|&&|\|\||[()+\-*/%&|^~!<>]")
    tokens, position = [], 0
    for match in token.finditer(expression):
        if expression[position:match.start()].strip(): return False
        tokens.append(match[0]); position = match.end()
    if expression[position:].strip(): return False
    operand, depth = True, 0
    for part in tokens:
        if operand:
            if part == "(": depth += 1
            elif part in {"+", "-", "!", "~"}: pass
            elif re.fullmatch(ID + r"|\d+(?:B|[uUlL]+)?", part): operand = False
            else: return False
        elif part == ")":
            if depth == 0: return False
            depth -= 1
        elif part in {"+", "-", "*", "/", "%", "&", "|", "^", "==", "!=", "<", ">", "<=", ">=", "<<", ">>", "&&", "||"}:
            operand = True
        else: return False
    return bool(tokens) and not operand and depth == 0


def _call_args(arguments):
    if not arguments.strip(): return True
    # Nested calls/compound addresses remain opaque, not simplified away.
    return all(_pure(part.strip()) or re.fullmatch(r"&\s*" + ID, part.strip())
               for part in arguments.split(","))


def _call_operands(arguments):
    values, addresses = [], []
    for part in arguments.split(","):
        address = re.fullmatch(r"&\s*(" + ID + r")", part.strip())
        if address: addresses.append(address[1])
        else: values.extend(_ids(part))
    return list(dict.fromkeys(values)), list(dict.fromkeys(addresses))


def _classify(code):
    result = {"kind": "opaque", "defines": [], "uses": [], "barrier": True}
    label = re.fullmatch(r"(" + LABEL + r")\s*:", code)
    if label: return dict(result, kind="label", label=label[1].strip("<>"))
    branch = re.fullmatch(r"if\s*\((.*)\)\s*goto\s+(" + LABEL + r");\s*else\s+goto\s+(" + LABEL + r");", code)
    if branch and _pure(branch[1]):
        return dict(result, kind="branch", condition=branch[1], uses=_ids(branch[1]),
                    targets=[{"branch": "true", "label": branch[2].strip("<>")}, {"branch": "false", "label": branch[3].strip("<>")}])
    goto = re.fullmatch(r"goto\s+(" + LABEL + r");", code)
    if goto: return dict(result, kind="goto", targets=[{"branch": "unconditional", "label": goto[1].strip("<>")}])
    returned = re.fullmatch(r"return(?:\s+(.*))?;", code)
    if returned and (not returned[1] or _pure(returned[1])): return dict(result, kind="return", uses=_ids(returned[1] or ""))
    if code in {"{", "}"}: return dict(result, kind="scope")
    if code in {"try {", "finally {"}: return dict(result, kind=code.split()[0])
    if re.fullmatch(r"(?:[A-Za-z_]\w*(?:\s+|\s*\*\s*))+" + ID + r"\s*\([^;]*\)\s*\{", code):
        return dict(result, kind="function")
    declared = re.fullmatch(r"(?:[A-Za-z_]\w*(?:\s+|\s*\*\s*))+?(" + ID + r");", code)
    if declared: return dict(result, kind="declaration", declares=[declared[1]], barrier=False)
    assignment = re.fullmatch(r"(.+?)\s*=\s*(.*);", code)
    if assignment:
        lhs, rhs = assignment[1].strip(), assignment[2].strip()
        if re.fullmatch(ID, lhs) and re.fullmatch(r"\{CLOBBER\([^)]*\)\}", rhs): return dict(result, kind="clobber", defines=[lhs])
        field_lhs = re.fullmatch(r"(" + ID + r")->(" + ID + r")", lhs)
        field_rhs = re.fullmatch(r"(" + ID + r")->(" + ID + r")", rhs)
        index_lhs = re.fullmatch(r"(" + ID + r")\[(.*)\]", lhs)
        index_rhs = re.fullmatch(r"(" + ID + r")\[(.*)\]", rhs)
        if field_lhs and _pure(rhs):
            return dict(result, kind="store", field={"base": field_lhs[1], "field": field_lhs[2], "access": "write"}, uses=list(dict.fromkeys([field_lhs[1]] + _ids(rhs))))
        if index_lhs and _pure(index_lhs[2]) and _pure(rhs):
            return dict(result, kind="store", indexed={"base": index_lhs[1], "index": index_lhs[2]}, uses=list(dict.fromkeys([index_lhs[1]] + _ids(index_lhs[2]) + _ids(rhs))))
        if re.fullmatch(ID, lhs) and field_rhs:
            return dict(result, kind="load", defines=[lhs], uses=[field_rhs[1]], field={"base": field_rhs[1], "field": field_rhs[2], "access": "read"}, barrier=False)
        if re.fullmatch(ID, lhs) and index_rhs and _pure(index_rhs[2]):
            return dict(result, kind="load", defines=[lhs], uses=list(dict.fromkeys([index_rhs[1]] + _ids(index_rhs[2]))), indexed={"base": index_rhs[1], "index": index_rhs[2]}, barrier=False)
        call = re.fullmatch(r"(" + ID + r")\s*\((.*)\)", rhs)
        if re.fullmatch(ID, lhs) and call and _call_args(call[2]):
            values, addresses = _call_operands(call[2])
            return dict(result, kind="call", defines=[lhs], uses=values, address_operands=addresses,
                        call={"callee": call[1], "args": call[2]}, result_unknown=True)
        if re.fullmatch(ID, lhs):
            cast = CAST.match(rhs)
            remainder = rhs[cast.end():] if cast else rhs
            if _pure(remainder):
                kind = "cast" if cast else "copy" if re.fullmatch(ID, rhs) else "constant" if re.fullmatch(r"-?\d+(?:B|[uUlL]+)?", rhs) else "pure"
                return dict(result, kind="scalar_assign", defines=[lhs], uses=_ids(remainder), assignment_kind=kind,
                            cast_value_equivalence_proved=False, barrier=False)
    call = re.fullmatch(r"(" + ID + r")\s*\((.*)\);", code)
    if call and _call_args(call[2]):
        values, addresses = _call_operands(call[2])
        return dict(result, kind="call", uses=values, address_operands=addresses,
                    call={"callee": call[1], "args": call[2]}, result_unknown=True)
    return result


def analyze_gimple(document):
    text = document.get("text")
    result = {"status": "insufficient_lexical_input", "document": document.get("id"), "path": document.get("path"),
              "revision": document.get("revision"), "source_sha256": None, "events": [], "dependencies": [],
              "unresolved_uses": [], "control_edges": [], "barriers": [], "unknowns": [],
              "whole_function_proved": False, "contract_or_alias_proved": False}
    try:
        need(isinstance(text, str), "text_missing")
        result["source_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        mask, spans, annotations, asms = _lexical_view(text)
        result["lexical_spans"] = spans
        units = _units(text, mask, asms)
        environment, versions, region = {}, {}, 0
        for number, (start, end, forced) in enumerate(units):
            code = " ".join(mask[start:end].split())
            if any(span["kind"] == "quoted_literal" and start <= span["start_offset"] < end for span in spans): forced = "opaque"
            event = ({"kind": "asm", "defines": [], "uses": [], "barrier": True} if forced == "asm" else
                     {"kind": "opaque", "defines": [], "uses": [], "barrier": True} if forced else _classify(code))
            exact_locations = []
            for loc in annotations:
                if not start <= loc["start_offset"] < end: continue
                line_start = text.rfind("\n", 0, loc["start_offset"]) + 1
                line_stop = text.find("\n", loc["end_offset"])
                if line_stop < 0: line_stop = len(text)
                visible = mask[max(start, line_start):min(end, line_stop)].strip()
                asm_same_line = forced == "asm" and any(loc["end_offset"] <= asm < line_stop for asm in asms if start <= asm < end)
                # An annotation on an otherwise comment-only/prefix line does
                # not become the next statement's exact source location.
                if visible or asm_same_line:
                    exact_locations.append({key: loc[key] for key in ["path", "line", "column"]})
            event.update(id="E" + str(number + 1), raw=text[start:end], code=code,
                         start_offset=start, end_offset=end, dump_line_start=text.count("\n", 0, start) + 1,
                         dump_line_end=text.count("\n", 0, end - 1) + 1,
                         source_locations=exact_locations)
            if event["kind"] in {"scope", "function", "try", "finally", "label", "asm", "opaque", "clobber"}:
                environment.clear(); region += 1
            event["region"] = region
            for variable in event["uses"]:
                definition = environment.get(variable)
                if definition is not None:
                    result["dependencies"].append({"use_event": event["id"], "variable": variable,
                                                   "definition_event": definition["event"], "definition_version": definition["version"], "region": region})
                else:
                    result["unresolved_uses"].append({"use_event": event["id"], "variable": variable, "region": region, "reason": "live_in_or_barrier_cleared"})
            if event["kind"] == "declaration":
                for variable in event["declares"]: environment.pop(variable, None)
            if not event["barrier"]:
                for variable in event["defines"]:
                    versions[variable] = versions.get(variable, 0) + 1
                    environment[variable] = {"event": event["id"], "version": versions[variable]}
            if event["barrier"]:
                result["barriers"].append({"event": event["id"], "kind": event["kind"], "region": region})
                environment.clear(); region += 1
            if event["kind"] in {"asm", "opaque", "clobber"}:
                result["unknowns"].append({"event": event["id"], "reason": event["kind"] + "_effects_or_shape_unresolved"})
            result["events"].append(event)
        labels = {}
        for event in result["events"]:
            if event["kind"] == "label": labels.setdefault(event["label"], []).append(event["id"])
        for event in result["events"]:
            for target in event.get("targets", []):
                matches = labels.get(target["label"], [])
                result["control_edges"].append({"source_event": event["id"], "target_label": target["label"],
                                                "target_event": matches[0] if len(matches) == 1 else None, "branch": target["branch"],
                                                "resolution": "unique_displayed_label" if len(matches) == 1 else "missing_or_ambiguous_label",
                                                "reachability_proved": False})
        result.update(status="partial_local_facts", coverage={"events": len(result["events"]),
                      "opaque_events": sum(x["kind"] == "opaque" for x in result["events"]),
                      "asm_events": sum(x["kind"] == "asm" for x in result["events"]),
                      "located_character_ranges": [[start, end] for start, end, _ in units],
                      "unlocated_nonwhitespace_characters": sum(not char.isspace() for char in text[units[-1][1]:]) if units else sum(not char.isspace() for char in text)})
    except (ScanError, ValueError, TypeError, KeyError, AttributeError) as exc:
        result["unknowns"].append({"reason": str(exc)})
    return result
