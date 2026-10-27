"""Audited ordinary-C parsing view and bounded consumer IR, version 2.

The v1 expression/statement frontend is reused read-only. No GNU rewriting,
external effect summaries, architecture norms or whole-program claims.
"""
from __future__ import annotations

import copy
import hashlib
from pycparser import c_lexer
from . import consumer_obligations as v1

need, Unsupported = v1.need, v1.Unsupported


class CRLFLexer(c_lexer.CLexer):
    """pycparser 3.11 whitespace bridge; original text/coordinates untouched."""
    def _match_token(self):
        if self._lexdata[self._pos] == "\r":
            need(self._lexdata[self._pos:self._pos + 2] == "\r\n", "bare_CR_unsupported")
            self._pos += 1
            return None
        return super()._match_token()


def parsing_view(text):
    """Mask comments with equal-length spaces; preserve CR/LF and all columns.

    Mapping is identity in Unicode character offsets (tabs count one character),
    not UTF-8 byte offsets or screen columns. No preprocessing is performed.
    """
    need(isinstance(text, str), "source_text_missing")
    need("\x00" not in text, "NUL_unsupported")
    need("??" not in text, "trigraph_or_double_question_unsupported")
    need("\\\n" not in text and "\\\r\n" not in text and "\\\r" not in text,
         "line_splice_unsupported")
    need(all(char != "\r" or text[index:index + 2] == "\r\n" for index, char in enumerate(text)), "bare_CR_unsupported")
    chars, spans, index = list(text), [], 0
    while index < len(text):
        start = index
        if text.startswith("//", index):
            index += 2
            while index < len(text) and text[index] not in "\r\n": index += 1
        elif text.startswith("/*", index):
            end = text.find("*/", index + 2)
            need(end >= 0, "unterminated_comment")
            index = end + 2
        elif text[index] in {'"', "'"}:
            quote = text[index]; index += 1
            while index < len(text):
                need(text[index] not in "\r\n", "newline_in_quoted_literal")
                if text[index] == "\\":
                    need(index + 1 < len(text), "unterminated_quoted_escape")
                    index += 2
                elif text[index] == quote:
                    index += 1
                    break
                else:
                    index += 1
            else:
                raise Unsupported("unterminated_quoted_literal")
            continue
        else:
            need(text[index] != "#", "directive_unsupported")
            index += 1
            continue
        spans.append({"start": start, "end": index})
        for at in range(start, index):
            if chars[at] not in "\r\n": chars[at] = " "
    view = "".join(chars)
    return {"text": view, "source_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "parsing_view_sha256": hashlib.sha256(view.encode("utf-8")).hexdigest(),
            "comment_spans": spans, "mapping": "identity_Unicode_character_offsets_CR_LF_preserved_tabs_one_character"}


def _walk(nodes):
    for node in nodes:
        yield node
        yield from _walk(node.get("body", []))


def _prefix(body):
    position = 0
    declarations = []
    while position < len(body) and body[position]["kind"] == "decl":
        declarations.append(body[position]); position += 1
    guards = []
    while position < len(body) and v1.sole(body[position], "return"):
        guards.append(body[position]); position += 1
    return declarations, guards, body[position:]


def _validate_scopes(body, parameters, parameter_declarations):
    top, _, _ = _prefix(body)
    objects = {d["name"]: d for d in parameter_declarations}
    need(len(objects) == len(parameters), "duplicate_parameter")
    def expression_check(expr, scope):
        if expr is None: return
        scalars = {name for name, d in scope.items() if d["extent"] is None}
        arrays = set(scope) - scalars
        need(v1.identifiers(expr) <= scalars, "undeclared_or_array_as_scalar")
        need(v1.array_reads(expr) <= arrays, "unknown_or_nonlocal_array")
    def declare(node, scope, in_loop):
        need(node["name"] not in scope, "shadow_or_duplicate_variable")
        if in_loop:
            need(node["extent"] is None and node["init"] is not None, "loop_alias_requires_scalar_initializer")
        for expr in node["init"] if isinstance(node["init"], list) else [node["init"]]:
            expression_check(expr, scope)
        scope[node["name"]] = node
    for node in top: declare(node, objects, False)
    def visit(nodes, scope, in_loop=False):
        for node in nodes:
            if node["kind"] == "decl":
                declare(node, scope, in_loop)
                continue
            for key in ["condition", "value", "target", "bound"]: expression_check(node.get(key), scope)
            if node["kind"] == "assign":
                target = node["target"].get("name", node["target"].get("array"))
                need(target in scope and not scope[target]["const"], "write_to_const_or_unknown_object")
            if node["kind"] == "for":
                need(node["index"] in scope and scope[node["index"]]["extent"] is None
                     and not scope[node["index"]]["const"], "invalid_loop_index_object")
                visit(node["body"], dict(scope), True)
            else:
                need(not any(x["kind"] == "decl" for x in node.get("body", [])), "nested_branch_declaration_unsupported")
                visit(node.get("body", []), dict(scope), in_loop)
    visit(body[len(top):], dict(objects))
    return objects


def _alias(node, protected):
    return (node["kind"] == "decl" and node["extent"] is None and node["init"] is not None
            and node["name"] not in protected) or v1.scalar_alias(node, protected)


def classify(body):
    declarations, guards, rest = _prefix(body)
    need(len(rest) in {4, 5} and rest[0]["kind"] == "for" and v1.sole(rest[1], "return")
         and rest[2]["kind"] == "for" and rest[-1]["kind"] == "return", "paired_phase_structure_not_supported")
    search, absence, update = rest[:3]
    final = rest[-1]
    flag_exit = rest[3] if len(rest) == 5 else None
    need(flag_exit is None or v1.sole(flag_exit, "return"), "flag_exit_shape_unsupported")
    constants = {}
    for decl in declarations:
        if decl["extent"] is None and decl["init"] is not None:
            try: constants[decl["name"]] = v1.value(decl["init"], constants)
            except Unsupported: pass  # Unknown initializer stays in executable IR.
    indices = {search["index"], update["index"]}
    bound_names = v1.identifiers(search["bound"]) | v1.identifiers(update["bound"])
    need(not indices & bound_names, "loop_bound_overlaps_index")
    for loop in [search, update]:
        need(loop["bound"]["op"] in {"int", "var"}, "loop_bound_not_literal_or_local_constant")
        loop["bound_value"] = v1.value(loop["bound"], constants)
        need(0 <= loop["bound_value"] <= 16, "loop_bound_outside_0_16")
    need(search["bound_value"] == update["bound_value"], "loop_domains_differ")
    candidate = search["body"][-1] if search["body"] else {}
    need(candidate.get("kind") == "if" and len(candidate["body"]) == 2
         and candidate["body"][0]["kind"] == "assign" and candidate["body"][0]["target"]["op"] == "var"
         and candidate["body"][1]["kind"] == "break", "search_assignment_break_missing")
    witness = candidate["body"][0]["target"]["name"]
    need(witness not in indices | bound_names and witness in constants
         and v1.identifiers(absence["condition"]) == {witness}, "search_absence_exit_not_bound_to_witness")
    need(bool(v1.value(absence["condition"], constants)), "initial_witness_does_not_take_absence_exit")
    protected = indices | bound_names | {witness}
    for part in search["body"][:-1]:
        need(_alias(part, protected) or v1.sole(part, "continue"), "unsupported_search_control_or_write")
    flag = None
    if flag_exit is not None:
        names = v1.identifiers(flag_exit["condition"])
        need(len(names) == 1, "monotone_flag_exit_not_single_scalar")
        flag = next(iter(names))
        need(flag not in protected and constants.get(flag) == 0, "monotone_flag_requires_zero_initializer")
        need(not v1.value(flag_exit["condition"], {flag: 0})
             and bool(v1.value(flag_exit["condition"], {flag: 1})), "monotone_flag_exit_not_zero_false_one_true")
        protected.add(flag)
    writes, checks = [], []
    for part in update["body"]:
        if _alias(part, protected) or v1.sole(part, "continue"): continue
        if flag is None and v1.sole(part, "return"):
            checks.append(part); continue
        assignment = part["body"][0] if v1.sole(part, "assign") else part
        need(assignment["kind"] == "assign", "unsupported_second_loop_control")
        if assignment["target"]["op"] == "at":
            writes.append((part, assignment))
        else:
            need(flag is not None and v1.sole(part, "assign") and assignment["target"].get("name") == flag
                 and v1.value(assignment["value"], {}) == 1, "monotone_flag_only_conditional_set_one")
            checks.append(part)
    need(len(writes) <= 1 and len(checks) <= 1, "multiple_writes_or_checks_unsupported")
    need(flag is None or len(checks) == 1, "monotone_flag_check_missing")
    check = checks[0] if checks else None
    if check is not None:
        need(witness in v1.identifiers(check["condition"])
             and bool(v1.array_reads(check["condition"]) & v1.array_reads(candidate["condition"])), "check_not_search_object_and_witness_linked")
        check["role"] = "member_check"
    for _, assignment in writes:
        need(witness in v1.identifiers(assignment["value"]), "array_update_not_witness_linked")
        assignment["role"] = "member_array_write"
    for node in _walk(rest):
        if node["kind"] == "assign" and node["target"]["op"] == "var":
            name = node["target"]["name"]
            need(name not in bound_names, "loop_bound_is_written")
            if name == witness: need(node is candidate["body"][0], "witness_reassigned_outside_selection")
            if name == flag:
                need(check is not None and node is check["body"][0], "monotone_flag_has_extra_write")
    candidate["role"], absence["role"] = "search_candidate", "search_absence_exit"
    search["role"], update["role"] = "search", "update_check"
    for guard in guards: guard["role"] = "early_bypass"
    if flag_exit is not None: flag_exit["role"] = "accumulated_flag_exit"
    final["role"] = "tail_return"
    order = "none"
    if check is not None:
        order = ("before_potential_array_write" if writes and update["body"].index(check) < update["body"].index(writes[0][0])
                 else "after_potential_array_write" if writes else "no_array_write_in_source")
    return {"witness": witness, "search": search, "candidate": candidate, "absence_exit": absence,
            "update": update, "member_check": check, "check_order": order, "flag": flag, "flag_exit": flag_exit,
            "check_mode": "monotone_flag" if flag is not None else "direct_return" if check is not None else "none",
            "writes": [assignment for _, assignment in writes], "early_guards": guards, "final_return": final}


def analyze_consumer(document):
    result = {"status": "insufficient", "document": document.get("id"), "path": document.get("path"),
              "revision": document.get("revision"), "source_sha256": None, "reasons": [], "quantifiers": [],
              "architecture_contract_proved": False, "memory_legality_proved": False}
    try:
        view = parsing_view(document.get("text"))
        result["frontend"] = {k: val for k, val in view.items() if k != "text"}
        result["source_sha256"], result["parsing_view_sha256"] = view["source_sha256"], view["parsing_view_sha256"]
        try: tree = v1.c_parser.CParser(lexer=CRLFLexer).parse(view["text"], filename=document.get("path") or "input.c")
        except Exception as exc: raise Unsupported("ordinary_C_parse_unsupported:" + str(exc)) from exc
        need(len(tree.ext) == 1 and isinstance(tree.ext[0], v1.c_ast.FuncDef), "one_complete_function_only")
        function = tree.ext[0]
        need(not function.decl.quals and isinstance(function.decl.type.type, v1.c_ast.TypeDecl)
             and function.decl.type.type.type.names == ["int"], "ordinary_int_return_function_required")
        parameter_declarations = [v1.declaration(p) for p in function.decl.type.args.params] if function.decl.type.args else []
        need(all(p["extent"] is None and p["init"] is None for p in parameter_declarations), "scalar_parameters_only")
        parameters = [p["name"] for p in parameter_declarations]
        body = v1.statements(function.body)
        _validate_scopes(body, parameters, parameter_declarations)
        structure = classify(body)
        quantifiers = [{"kind": "exists_visited_search_candidate", "phase": "avoid_selected_post_search_exit",
                        "predicate": copy.deepcopy(structure["candidate"]["condition"]), "coord": structure["candidate"]["coord"],
                        "witness_assignment": copy.deepcopy(structure["candidate"]["body"][0]),
                        "post_search_exit_condition": copy.deepcopy(structure["absence_exit"]["condition"]),
                        "ordered_first_match_only": True, "sufficiency_proved": False}]
        if structure["member_check"] is not None:
            quantifiers.append({"kind": "forall_reached_member_branch_not_taken", "phase": structure["check_order"],
                                "early_return_or_flag_predicate": copy.deepcopy(structure["member_check"]["condition"]),
                                "coord": structure["member_check"]["coord"], "complete_iteration_domain_proved": False})
        result.update(status="extracted_bounded_conditions", function=function.decl.name, parameters=parameters,
                      ir=body, structure=structure, quantifiers=quantifiers,
                      assumptions=["Coordinate mapping is by Unicode characters, not byte/display columns",
                                   "Only admitted local ordinary-C syntax; raw GNU/macros remain unsupported",
                                   "Indices, initialized values and bounded arithmetic checked for each explicit execution",
                                   "Actual write counts do not prove write/check object identity or architecture norms"])
    except (Unsupported, ValueError, TypeError, KeyError, AttributeError) as exc:
        result["reasons"].append(str(exc))
    return result


def evaluate_consumer(analysis, parameters):
    result = {"status": "insufficient", "return_value": None, "phase": "not_started", "trace": [],
              "check_observations": [], "conditions": {}, "unknown": []}
    try:
        need(analysis.get("status") == "extracted_bounded_conditions", "source_structure_not_extracted")
        need(isinstance(parameters, dict) and set(parameters) == set(analysis["parameters"]), "parameter_identity_mismatch")
        env = {name: v1.checked(number) for name, number in parameters.items()}
        conditions = {"search_predicates": [], "search_exit_taken": None, "search_reached": False,
                      "second_loop_reached": False, "bypassed": False}
        result["conditions"] = conditions
        context = {"iteration": None, "writes": 0}
        def execute(nodes):
            for node in nodes:
                kind, role = node["kind"], node.get("role")
                if kind == "decl":
                    if node["extent"] is None:
                        env[node["name"]] = v1.value(node["init"], env) if node["init"] else None
                    else:
                        init = [v1.value(x, env) for x in node["init"]] if node["init"] is not None else None
                        env[node["name"]] = init + [0] * (node["extent"] - len(init)) if init is not None else [None] * node["extent"]
                elif kind == "assign":
                    number = v1.checked(v1.value(node["value"], env)); target = node["target"]
                    index = None
                    if target["op"] == "var":
                        need(target["name"] in env, "assignment_to_unknown_scalar")
                        env[target["name"]] = number
                    else:
                        array, index = env.get(target["array"]), v1.value(target["index"], env)
                        need(isinstance(array, list) and 0 <= index < len(array), "index_legality_not_established:" + target["array"])
                        array[index] = number
                        if result["phase"] == "update_check": context["writes"] += 1
                    result["trace"].append({"event": "write", "phase": result["phase"], "coord": node["coord"],
                                            "target": target, "resolved_index": index, "value": number})
                elif kind == "if":
                    taken = bool(v1.value(node["condition"], env))
                    result["trace"].append({"event": "branch", "role": role, "phase": result["phase"], "coord": node["coord"], "taken": taken})
                    if role == "search_candidate": conditions["search_predicates"].append(taken)
                    if role == "search_absence_exit": conditions["search_exit_taken"] = taken
                    if role == "member_check":
                        result["check_observations"].append({"iteration": context["iteration"], "predicate_value": taken, "writes_before": context["writes"]})
                    if role == "early_bypass" and taken: conditions["bypassed"] = True
                    if taken:
                        if role in {"early_bypass", "search_absence_exit", "accumulated_flag_exit"}: result["exit_class"] = role
                        if role == "member_check" and analysis["structure"]["check_mode"] == "direct_return": result["exit_class"] = "member_direct_return"
                        signal = execute(node["body"])
                        if signal: return signal
                elif kind == "for":
                    result["phase"] = node["role"]
                    conditions["search_reached" if node["role"] == "search" else "second_loop_reached"] = True
                    bound = v1.value(node["bound"], env)
                    need(bound == node["bound_value"] and 0 <= bound <= 16, "runtime_loop_bound_mismatch")
                    env[node["index"]] = 0
                    local_names = [x["name"] for x in node["body"] if x["kind"] == "decl"]
                    while env[node["index"]] < bound:
                        context["iteration"], context["writes"] = env[node["index"]], 0
                        result["trace"].append({"event": "iteration", "phase": node["role"], "index": env[node["index"]], "coord": node["coord"]})
                        try: signal = execute(node["body"])
                        finally:
                            for name in local_names: env.pop(name, None)
                        if signal and signal[0] == "return": return signal
                        if signal and signal[0] == "break": break
                        env[node["index"]] += 1
                elif kind == "return":
                    result["return_coord"] = node["coord"]
                    if role == "tail_return": result["exit_class"] = "tail_return"
                    return ("return", v1.value(node["value"], env))
                elif kind in {"break", "continue"}:
                    result["trace"].append({"event": kind, "phase": result["phase"], "coord": node["coord"]})
                    return (kind, None)
                else: raise Unsupported("unsupported_IR_statement")
            return None
        signal = execute(copy.deepcopy(analysis["ir"]))
        need(signal is not None and signal[0] == "return", "finite_function_did_not_return")
        observations = result["check_observations"]
        conditions["exists_among_reached_search_predicates"] = any(conditions["search_predicates"]) if conditions["search_reached"] else None
        conditions["all_reached_member_branches_not_taken"] = all(not x["predicate_value"] for x in observations) if conditions["second_loop_reached"] else None
        conditions["check_domain"] = ("not_reached" if not conditions["second_loop_reached"] else
                                      "no_check_in_source" if analysis["structure"]["check_mode"] == "none" else
                                      "vacuous_no_reached_checks" if not observations else "actual_reached_checks")
        result.update(status="evaluated_under_explicit_inputs", return_value=signal[1], final_state=copy.deepcopy(env),
                      memory_legality_checked_for_this_execution_only=True)
    except (Unsupported, ValueError, TypeError, KeyError, AttributeError) as exc:
        result["unknown"].append(str(exc))
    return result
