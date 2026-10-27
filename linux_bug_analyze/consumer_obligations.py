"""Bounded ordinary-C consumer structure; not a kernel/CFG/effect verifier.

Quantifier roles are inferred from two explicit loop phases, never supplied by
the caller. Unknown control, calls, pointers and GNU C remain insufficient.
"""
from __future__ import annotations

import copy
import hashlib
from pycparser import c_ast, c_parser


class Unsupported(ValueError):
    pass


def need(condition, reason):
    if not condition:
        raise Unsupported(reason)


def coord(node):
    return {"line": node.coord.line, "column": node.coord.column} if node.coord else None


def expression(node):
    at = coord(node)
    if isinstance(node, c_ast.Constant) and node.type == "int":
        try:
            value = int(node.value, 0)
        except ValueError as exc:
            raise Unsupported("integer_literal_unsupported") from exc
        need(-32767 <= value <= 32767, "integer_literal_outside_safe_subset")
        return {"op": "int", "value": value, "coord": at}
    if isinstance(node, c_ast.ID):
        return {"op": "var", "name": node.name, "coord": at}
    if isinstance(node, c_ast.ArrayRef) and isinstance(node.name, c_ast.ID):
        return {"op": "at", "array": node.name.name, "index": expression(node.subscript), "coord": at}
    if isinstance(node, c_ast.UnaryOp) and node.op in {"!", "+", "-"}:
        return {"op": "unary", "operator": node.op, "arg": expression(node.expr), "coord": at}
    if isinstance(node, c_ast.BinaryOp) and node.op in {"+", "-", "*", "==", "!=", "<", "<=", ">", ">=", "&&", "||"}:
        return {"op": "binary", "operator": node.op, "left": expression(node.left), "right": expression(node.right), "coord": at}
    raise Unsupported("unsupported_expression:" + type(node).__name__)


def value(expr, env):
    op = expr["op"]
    if op == "int":
        return expr["value"]
    if op == "var":
        result = env.get(expr["name"])
        need(type(result) is int, "unknown_or_uninitialized_scalar:" + expr["name"])
        return result
    if op == "at":
        array = env.get(expr["array"])
        index = value(expr["index"], env)
        need(isinstance(array, list) and 0 <= index < len(array), "index_legality_not_established:" + expr["array"])
        need(type(array[index]) is int, "uninitialized_array_member:" + expr["array"])
        return array[index]
    if op == "unary":
        arg = value(expr["arg"], env)
        return int(not arg) if expr["operator"] == "!" else arg if expr["operator"] == "+" else checked(-arg)
    left = value(expr["left"], env)
    operator = expr["operator"]
    if operator == "&&" and not left:
        return 0
    if operator == "||" and left:
        return 1
    right = value(expr["right"], env)
    operations = {"+": lambda: checked(left + right), "-": lambda: checked(left - right), "*": lambda: checked(left * right),
                  "==": lambda: int(left == right), "!=": lambda: int(left != right), "<": lambda: int(left < right),
                  "<=": lambda: int(left <= right), ">": lambda: int(left > right), ">=": lambda: int(left >= right),
                  "&&": lambda: int(bool(left) and bool(right)), "||": lambda: int(bool(left) or bool(right))}
    need(operator in operations, "unknown_expression_operator")
    return operations[operator]()


def checked(number):
    need(type(number) is int and -32767 <= number <= 32767, "arithmetic_outside_safe_subset")
    return number


def declaration(node):
    kind = node.type
    dimension = None
    need(set(node.quals or []) <= {"const"}, "nonconst_qualifier_unsupported")
    if isinstance(kind, c_ast.ArrayDecl):
        need(not kind.dim_quals, "array_dimension_qualifier_unsupported")
        dimension = value(expression(kind.dim), {})
        need(1 <= dimension <= 16, "local_array_extent_unsupported")
        kind = kind.type
    need(isinstance(kind, c_ast.TypeDecl) and isinstance(kind.type, c_ast.IdentifierType)
         and kind.type.names == ["int"], "pointer_or_noninteger_declaration")
    need(set(kind.quals or []) <= {"const"}, "nonconst_qualifier_unsupported")
    need(not node.storage and not node.bitsize, "storage_or_bitfield_unsupported")
    if dimension is None:
        init = expression(node.init) if node.init else None
    else:
        need(node.init is None or isinstance(node.init, c_ast.InitList), "array_initializer_unsupported")
        init = [expression(x) for x in node.init.exprs] if node.init else None
        need(init is None or len(init) <= dimension, "array_initializer_too_long")
    return {"kind": "decl", "name": node.name, "extent": dimension, "const": "const" in node.quals,
            "init": init, "coord": coord(node)}


def statements(node):
    return [statement(x) for x in node.block_items or []] if isinstance(node, c_ast.Compound) else [statement(node)]


def statement(node):
    at = coord(node)
    if isinstance(node, c_ast.Decl):
        return declaration(node)
    if isinstance(node, c_ast.Assignment) and node.op == "=":
        lhs = expression(node.lvalue)
        need(lhs["op"] in {"var", "at"}, "assignment_target_unsupported")
        return {"kind": "assign", "target": lhs, "value": expression(node.rvalue), "coord": at}
    if isinstance(node, c_ast.If):
        need(node.iffalse is None, "else_control_unsupported")
        return {"kind": "if", "condition": expression(node.cond), "body": statements(node.iftrue), "coord": at}
    if isinstance(node, (c_ast.Return, c_ast.Continue, c_ast.Break)):
        return {"kind": type(node).__name__.lower(), "value": expression(node.expr) if isinstance(node, c_ast.Return) else None, "coord": at}
    if isinstance(node, c_ast.For):
        init = statement(node.init)
        need(init["kind"] == "assign" and init["target"]["op"] == "var" and value(init["value"], {}) == 0,
             "for_initialization_not_zero_scalar")
        index = init["target"]["name"]
        condition = expression(node.cond)
        need(condition["op"] == "binary" and condition["operator"] == "<"
             and condition["left"]["op"] == "var" and condition["left"]["name"] == index, "for_condition_unsupported")
        need(isinstance(node.next, c_ast.UnaryOp) and node.next.op in {"p++", "++"}
             and isinstance(node.next.expr, c_ast.ID) and node.next.expr.name == index, "for_increment_unsupported")
        return {"kind": "for", "index": index, "bound": condition["right"], "body": statements(node.stmt), "coord": at}
    raise Unsupported("unsupported_statement:" + type(node).__name__)


def sole(node, kind):
    return node["kind"] == "if" and len(node["body"]) == 1 and node["body"][0]["kind"] == kind


def identifiers(expr):
    if not isinstance(expr, dict):
        return set()
    return ({expr["name"]} if expr.get("op") == "var" else set()) | set().union(
        *(identifiers(x) for x in expr.values() if isinstance(x, dict)))


def scalar_alias(node, protected):
    return node["kind"] == "assign" and node["target"]["op"] == "var" and node["target"]["name"] not in protected


def array_reads(expr):
    if not isinstance(expr, dict):
        return set()
    return ({expr["array"]} if expr.get("op") == "at" else set()) | set().union(
        *(array_reads(x) for x in expr.values() if isinstance(x, dict)))


def validate_objects(body, parameters, const_parameters=()):
    declarations = {x["name"]: x for x in body if x["kind"] == "decl"}
    scalar_names = set(parameters) | {name for name, d in declarations.items() if d["extent"] is None}
    array_names = {name for name, d in declarations.items() if d["extent"] is not None}
    const_names = {name for name, d in declarations.items() if d["const"]} | set(const_parameters)
    def expr_check(expr):
        if expr is None:
            return
        need(identifiers(expr) <= scalar_names, "undeclared_or_array_as_scalar")
        need(array_reads(expr) <= array_names, "unknown_or_nonlocal_array")
    def visit(nodes):
        for node in nodes:
            if node["kind"] == "decl":
                for expr in node["init"] if isinstance(node["init"], list) else [node["init"]]: expr_check(expr)
            else:
                for key in ["condition", "value", "target", "bound"]:
                    expr_check(node.get(key))
            if node["kind"] == "assign":
                name = node["target"].get("name", node["target"].get("array"))
                need(name not in const_names, "assignment_to_const_object")
            if node["kind"] == "for":
                need(node["index"] in scalar_names and node["index"] not in const_names, "invalid_loop_index_object")
            visit(node.get("body", []))
    visit(body)


def classify(body):
    position = 0
    declarations = []
    while position < len(body) and body[position]["kind"] == "decl":
        declarations.append(body[position]); position += 1
    guards = []
    while position < len(body) and sole(body[position], "return"):
        guards.append(body[position]); position += 1
    need(len(body) - position == 4 and body[position]["kind"] == "for" and sole(body[position + 1], "return")
         and body[position + 2]["kind"] == "for" and body[position + 3]["kind"] == "return", "paired_phase_structure_not_supported")
    search, exit_check, update, final_return = body[position:]
    constants = {}
    local_names = {x["name"] for x in declarations}
    for decl in declarations:
        if decl["extent"] is None and decl["init"] is not None:
            try:
                constants[decl["name"]] = value(decl["init"], constants)
            except Unsupported:
                pass  # Not a bound proof; its expression remains in the IR.
    for loop in [search, update]:
        need(loop["index"] in local_names, "loop_index_not_local")
        need(loop["bound"]["op"] in {"int", "var"}, "loop_bound_not_literal_or_local_constant")
        need(not identifiers(loop["bound"]) & {search["index"], update["index"]}, "loop_bound_overlaps_index")
        loop["bound_value"] = value(loop["bound"], constants)
        need(0 <= loop["bound_value"] <= 16, "loop_bound_outside_0_16")
    need(search["bound_value"] == update["bound_value"], "loop_domains_differ")
    candidate = search["body"][-1] if search["body"] else {}
    need(candidate.get("kind") == "if" and len(candidate["body"]) == 2
         and candidate["body"][0]["kind"] == "assign" and candidate["body"][0]["target"]["op"] == "var"
         and candidate["body"][1]["kind"] == "break", "search_assignment_break_missing")
    witness = candidate["body"][0]["target"]["name"]
    need(witness not in {search["index"], update["index"]}
         and witness not in identifiers(search["bound"]) | identifiers(update["bound"]), "witness_overlaps_loop_control")
    protected = {witness, search["index"], update["index"]} | identifiers(search["bound"]) | identifiers(update["bound"])
    need(witness in constants and identifiers(exit_check["condition"]) == {witness}, "search_absence_exit_not_bound_to_witness")
    need(bool(value(exit_check["condition"], constants)), "initial_witness_does_not_take_absence_exit")
    for part in search["body"][:-1]:
        need(scalar_alias(part, protected) or sole(part, "continue"), "unsupported_search_control_or_write")
    need(len(update["body"]) >= 2 and sole(update["body"][-1], "return"), "per_member_exit_missing")
    member_check = update["body"][-1]
    writes = []
    for part in update["body"][:-1]:
        if scalar_alias(part, protected) or sole(part, "continue"):
            continue
        assignment = part["body"][0] if sole(part, "assign") else part
        need(assignment["kind"] == "assign" and assignment["target"]["op"] == "at", "unsupported_update_control_or_write")
        writes.append((part, assignment))
    need(len(writes) == 1, "exactly_one_member_update_required")
    update_branch, assignment = writes[0]
    need(witness in identifiers(assignment["value"]) and witness in identifiers(member_check["condition"]), "update_and_check_not_witness_linked")
    need(assignment["target"]["array"] in array_reads(candidate["condition"])
         and assignment["target"]["array"] in array_reads(member_check["condition"]), "search_update_check_array_not_linked")
    bound_names = identifiers(search["bound"]) | identifiers(update["bound"])
    def walk(nodes):
        for item in nodes:
            yield item
            yield from walk(item.get("body", []))
    for item in walk(body[position:]):
        if item["kind"] == "assign" and item["target"]["op"] == "var":
            need(item["target"]["name"] not in bound_names, "loop_bound_is_written")
    candidate["role"] = "search_candidate"
    exit_check["role"] = "search_absence_exit"
    member_check["role"] = "member_post_update_check"
    search["role"], update["role"] = "search", "update_check"
    for item in guards:
        item["role"] = "early_bypass"
    final_return["role"] = "tail_return"
    return {"witness": witness, "search": search, "candidate": candidate, "absence_exit": exit_check,
            "update": update, "update_branch": update_branch, "member_check": member_check, "early_guards": guards,
            "final_return": final_return}


def analyze_consumer(document):
    result = {"status": "insufficient", "document": document.get("id"), "path": document.get("path"),
              "revision": document.get("revision"), "source_sha256": None, "reasons": [],
              "architecture_contract_proved": False, "memory_legality_proved": False, "quantifiers": []}
    try:
        text = document.get("text")
        need(isinstance(text, str), "source_text_missing")
        result["source_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        try:
            tree = c_parser.CParser().parse(text, filename=document.get("path") or "input.c")
        except Exception as exc:
            raise Unsupported("ordinary_C_parse_unsupported:" + str(exc)) from exc
        need(len(tree.ext) == 1 and isinstance(tree.ext[0], c_ast.FuncDef), "one_complete_function_only")
        function = tree.ext[0]
        need(not function.decl.quals, "qualified_function_return_unsupported")
        need(isinstance(function.decl.type.type, c_ast.TypeDecl)
             and function.decl.type.type.type.names == ["int"], "int_return_function_required")
        parameters, const_parameters = [], []
        for param in function.decl.type.args.params if function.decl.type.args else []:
            decl = declaration(param)
            need(decl["extent"] is None and decl["init"] is None, "scalar_parameters_only")
            parameters.append(decl["name"])
            if decl["const"]: const_parameters.append(decl["name"])
        body = statements(function.body)
        declarations = [x for x in body if x["kind"] == "decl"]
        names = parameters + [x["name"] for x in declarations]
        need(len(names) == len(set(names)), "shadow_or_duplicate_variable")
        validate_objects(body, parameters, const_parameters)
        shape = classify(body)
        result.update(status="extracted_bounded_conditions", function=function.decl.name, parameters=parameters, ir=body, structure=shape,
                      assumptions=["Only declared scalar/local-array objects; no pointers, addresses, calls or outside effects",
                                   "Indices, initialized reads and arithmetic safety are checked per finite evaluation, not proved for all inputs",
                                   "Early-return role is syntactic; negative code is not automatically a defect or architecture norm"],
                      quantifiers=[{"kind": "exists_visited_search_candidate", "phase": "avoid_selected_post_search_exit",
                                    "predicate": copy.deepcopy(shape["candidate"]["condition"]), "coord": shape["candidate"]["coord"],
                                    "witness_assignment": copy.deepcopy(shape["candidate"]["body"][0]),
                                    "post_search_exit_condition": copy.deepcopy(shape["absence_exit"]["condition"]),
                                    "ordered_first_match_only": True, "sufficiency_proved": False,
                                    "strength": "necessary_for_avoiding_exit_not_general_sufficiency"},
                                   {"kind": "forall_reached_post_update_branch_not_taken", "phase": "after_conditional_member_update",
                                    "early_return_predicate": copy.deepcopy(shape["member_check"]["condition"]),
                                    "coord": shape["member_check"]["coord"], "strength": "branches_for_actual_visited_iterations_only_not_pre_state_forall"}])
    except (Unsupported, ValueError, TypeError, KeyError, AttributeError) as exc:
        result["reasons"].append(str(exc))
    return result


def evaluate_consumer(analysis, parameters):
    result = {"status": "insufficient", "return_value": None, "phase": "not_started", "trace": [], "conditions": {}, "unknown": []}
    try:
        need(analysis.get("status") == "extracted_bounded_conditions", "source_structure_not_extracted")
        need(isinstance(parameters, dict) and set(parameters) == set(analysis["parameters"]), "parameter_identity_mismatch")
        env = {name: checked(number) for name, number in parameters.items()}
        conditions = {"search_predicates": [], "post_update_branches_not_taken": [], "search_exit_taken": None, "bypassed": False,
                      "search_reached": False, "update_check_reached": False}
        result["conditions"] = conditions
        def put(target, number):
            checked(number)
            if target["op"] == "var":
                need(target["name"] in env, "assignment_to_undeclared_scalar")
                env[target["name"]] = number
            else:
                array, index = env.get(target["array"]), value(target["index"], env)
                need(isinstance(array, list) and 0 <= index < len(array), "index_legality_not_established:" + target["array"])
                array[index] = number
        def execute(nodes):
            for node in nodes:
                kind, role = node["kind"], node.get("role")
                if kind == "decl":
                    if node["extent"] is None:
                        env[node["name"]] = value(node["init"], env) if node["init"] else None
                    else:
                        init = [value(x, env) for x in node["init"]] if node["init"] is not None else None
                        env[node["name"]] = init + [0] * (node["extent"] - len(init)) if init is not None else [None] * node["extent"]
                elif kind == "assign":
                    number = value(node["value"], env); put(node["target"], number)
                    result["trace"].append({"event": "write", "phase": result["phase"], "coord": node["coord"], "target": node["target"], "value": number})
                elif kind == "if":
                    taken = bool(value(node["condition"], env))
                    result["trace"].append({"event": "branch", "role": role, "phase": result["phase"], "coord": node["coord"], "taken": taken})
                    if role == "search_candidate": conditions["search_predicates"].append(taken)
                    if role == "search_absence_exit": conditions["search_exit_taken"] = taken
                    if role == "member_post_update_check": conditions["post_update_branches_not_taken"].append(not taken)
                    if role == "early_bypass" and taken: conditions["bypassed"] = True
                    if taken:
                        if role in {"early_bypass", "search_absence_exit", "member_post_update_check"}:
                            result["exit_class"] = role
                        signal = execute(node["body"])
                        if signal: return signal
                elif kind == "for":
                    result["phase"] = node["role"]
                    conditions["search_reached" if node["role"] == "search" else "update_check_reached"] = True
                    bound = value(node["bound"], env)
                    need(bound == node["bound_value"] and 0 <= bound <= 16, "runtime_loop_bound_mismatch")
                    env[node["index"]] = 0
                    while env[node["index"]] < bound:
                        result["trace"].append({"event": "iteration", "phase": node["role"], "index": env[node["index"]], "coord": node["coord"]})
                        signal = execute(node["body"])
                        if signal and signal[0] == "return": return signal
                        if signal and signal[0] == "break": break
                        env[node["index"]] += 1
                elif kind == "return":
                    result["return_coord"] = node["coord"]
                    if role == "tail_return": result["exit_class"] = "tail_return"
                    return ("return", value(node["value"], env))
                elif kind in {"break", "continue"}:
                    result["trace"].append({"event": kind, "phase": result["phase"], "coord": node["coord"]})
                    return (kind, None)
                else:
                    raise Unsupported("unknown_IR_statement")
            return None
        signal = execute(copy.deepcopy(analysis["ir"]))
        need(signal is not None and signal[0] == "return", "finite_function_did_not_return")
        result.update(status="evaluated_under_explicit_inputs", return_value=signal[1], final_state=copy.deepcopy(env))
        conditions["exists_among_reached_search_predicates"] = any(conditions["search_predicates"]) if conditions["search_reached"] else None
        conditions["all_reached_post_update_branches_not_taken"] = all(conditions["post_update_branches_not_taken"]) if conditions["update_check_reached"] else None
        conditions["post_check_domain"] = ("not_reached" if not conditions["update_check_reached"] else
                                           "vacuous_no_reached_checks" if not conditions["post_update_branches_not_taken"] else "actual_reached_checks")
        result["memory_legality_checked_for_this_execution_only"] = True
    except (Unsupported, ValueError, TypeError, KeyError, AttributeError) as exc:
        result["unknown"].append(str(exc))
    return result
