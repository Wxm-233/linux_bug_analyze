"""Bounded, opaque-call paths through forward branches/gotos in complete C.

Loops and other unsupported constructs are explicit per-path frontiers. No
call effects, concrete guard values, type/layout or runtime content are proved.
"""
from __future__ import annotations

import copy
import hashlib
import re

from .source_conditions import SourceError, _comments, _nodes, c_ast, c_generator, c_parser
from .preprocessed_evidence import _lex


def extract_forward_paths(document, *, type_names=("bool", "cpumask_t"), max_paths=64, max_steps=256):
    result = {"document": document.get("id"), "revision": document.get("revision"),
              "path": document.get("path"), "status": "insufficient", "function": None,
              "paths": [], "reasons": [], "whole_contract": "insufficient",
              "call_effects_proved": False, "runtime_reachability_proved": False,
              "semantic_layer": "unpreprocessed_C_forward_structure",
              "assumptions": ["opaque calls return normally; no call effects or hidden macro writes proved",
                              "guard outcomes are structural alternatives, not runtime witnesses",
                              "events list standalone calls only; direct calls inside predicates stay opaque in guard expressions",
                              "symbolic arguments denote source declarations/versions, never pointee contents",
                              "syntax typedef stubs do not establish real types or effective configuration"],
              "type_stubs": list(type_names)}
    try:
        if c_parser is None:
            raise SourceError("optional pycparser unavailable")
        lo, hi, text = document.get("start_line"), document.get("end_line"), document.get("text")
        if (type(lo) is not int or type(hi) is not int or lo < 1 or not isinstance(text, str)
                or len(text.splitlines()) != hi - lo + 1 or not document.get("revision") or not document.get("path")):
            raise SourceError("complete source interval/identity required")
        if type(max_paths) is not int or not 1 <= max_paths <= 256 or type(max_steps) is not int or not 1 <= max_steps <= 1024:
            raise SourceError("invalid path/step bound")
        if any(not isinstance(t, str) or not re.fullmatch(r"[A-Za-z_]\w*", t) for t in type_names):
            raise SourceError("invalid type stub")
        clean = _comments(text)
        if re.search(r"^\s*#", clean, re.M):
            raise SourceError("preprocessor input needs actual preprocessing")
        prefix = "".join("typedef int " + t + ";\n" for t in type_names)
        ast = c_parser.CParser().parse(prefix + clean, filename=document["path"])
        functions = [n for n in ast.ext if isinstance(n, c_ast.FuncDef)]
        if len(functions) != 1 or len(ast.ext) != len(type_names) + 1:
            raise SourceError("one complete function required")
        function = functions[0]
        result.update(function=function.decl.name, source_sha256=hashlib.sha256(text.encode()).hexdigest())
        generator = c_generator.CGenerator()
        def position(node):
            return {"line": node.coord.line - len(type_names) + lo - 1, "column": node.coord.column}
        def show(node):
            return generator.visit(node) if node is not None else None
        parameters = function.decl.type.args.params if function.decl.type.args else []
        declarations = [n for n in _nodes(function) if isinstance(n, c_ast.Decl) and n.name
                        and not isinstance(n.type, c_ast.FuncDecl)]
        names = [n.name for n in declarations]
        shadowed = {n for n in names if names.count(n) > 1}
        parameter_names = {p.name for p in parameters if isinstance(p, c_ast.Decl) and p.name}
        object_names = set(names) | parameter_names
        result["shadowed_names"] = sorted(shadowed)
        result["parameters"] = [{"name": p.name, **position(p)} for p in parameters
                                if isinstance(p, c_ast.Decl) and p.name]
        nodes, labels = [], {}
        top_labels = {id(n) for n in function.body.block_items or [] if isinstance(n, c_ast.Label)}
        def emit(kind, node=None, **data):
            index = len(nodes)
            nodes.append({"kind": kind, **(position(node) if node is not None else {}), **data})
            return index
        end = emit("function_end")
        def build(node, successor):
            if node is None:
                return successor
            if isinstance(node, c_ast.Compound):
                current = successor
                for child in reversed(node.block_items or []):
                    current = build(child, current)
                return current
            if isinstance(node, c_ast.If):
                if any(isinstance(n, c_ast.Assignment) or (isinstance(n, c_ast.UnaryOp)
                       and n.op in {"++", "--", "p++", "p--"}) for n in _nodes(node.cond)):
                    return emit("frontier", node, reason="side effects in branch predicate")
                if any(isinstance(n, c_ast.FuncCall) and (not isinstance(n.name, c_ast.ID)
                       or n.name.name in object_names) for n in _nodes(node.cond)):
                    return emit("frontier", node, reason="indirect call in predicate")
                if any(isinstance(n, c_ast.FuncCall) and n.args is not None
                       and any(isinstance(a, c_ast.FuncCall) for a in _nodes(n.args)) for n in _nodes(node.cond)):
                    return emit("frontier", node, reason="nested call in predicate")
                return emit("branch", node, expression=show(node.cond), ast=node.cond,
                            iftrue=build(node.iftrue, successor), iffalse=build(node.iffalse, successor))
            if isinstance(node, c_ast.Label):
                if id(node) not in top_labels:
                    return emit("frontier", node, reason="nested labels are outside this subset")
                if node.name in labels:
                    raise SourceError("duplicate label")
                target = emit("label", node, name=node.name, next=build(node.stmt, successor))
                labels[node.name] = target
                return target
            if isinstance(node, c_ast.Goto):
                return emit("goto", node, target_label=node.name)
            if isinstance(node, c_ast.Return):
                if node.expr is not None and any(isinstance(n, c_ast.FuncCall) for n in _nodes(node.expr)):
                    return emit("frontier", node, reason="call inside return expression")
                return emit("return", node, expression=show(node.expr), ast=node.expr)
            if isinstance(node, c_ast.FuncCall):
                if not isinstance(node.name, c_ast.ID) or node.name.name in object_names:
                    return emit("frontier", node, reason="indirect/object callee")
                if node.args is not None and any(isinstance(n, (c_ast.FuncCall, c_ast.Assignment))
                       or (isinstance(n, c_ast.UnaryOp) and n.op in {"++", "--", "p++", "p--"})
                       for n in _nodes(node.args)):
                    return emit("frontier", node, reason="nested call/write in call arguments")
                return emit("call", node, callee=node.name.name, ast=node, next=successor)
            if isinstance(node, (c_ast.Decl, c_ast.Assignment, c_ast.UnaryOp, c_ast.EmptyStatement)):
                if any(isinstance(n, c_ast.FuncCall) for n in _nodes(node)):
                    return emit("frontier", node, reason="call embedded in other statement")
                if any((isinstance(n, c_ast.Assignment) and not isinstance(n.lvalue, c_ast.ID))
                       or (isinstance(n, c_ast.UnaryOp) and n.op in {"++", "--", "p++", "p--"}
                           and not isinstance(n.expr, c_ast.ID)) for n in _nodes(node)):
                    return emit("frontier", node, reason="complex write needs alias/value analysis")
                return emit("statement", node, ast=node, next=successor)
            return emit("frontier", node, reason="unsupported " + type(node).__name__)
        entry = build(function.body, end)
        initial = {p.name: {"declaration": {"parameter": i, **position(p)}, "version": "parameter"}
                   for i, p in enumerate(parameters) if isinstance(p, c_ast.Decl) and p.name}
        queue = [{"pc": entry, "events": [], "guards": [], "locals": initial, "escaped": set(), "seen": set()}]
        leaves = []
        def source_version(node):
            p = position(node)
            return str(p["line"]) + ":" + str(p["column"])
        def effects(node, state):
            if node is None:
                return
            if isinstance(node, c_ast.Decl) and node.name and not isinstance(node.type, c_ast.FuncDecl):
                state["locals"][node.name] = {"declaration": {"local": node.name, **position(node),
                                                              "storage": node.storage},
                                               "version": "declaration:" + source_version(node)}
            if isinstance(node, c_ast.Assignment) and isinstance(node.lvalue, c_ast.ID):
                if node.lvalue.name in state["locals"]:
                    state["locals"][node.lvalue.name]["version"] = "write:" + source_version(node)
            if isinstance(node, c_ast.UnaryOp):
                if node.op == "&" and isinstance(node.expr, c_ast.ID):
                    state["escaped"].add(node.expr.name)
                elif node.op in {"++", "--", "p++", "p--"} and isinstance(node.expr, c_ast.ID) and node.expr.name in state["locals"]:
                    state["locals"][node.expr.name]["version"] = "write:" + source_version(node)
            for _, child in node.children():
                effects(child, state)
        def argument(node, state):
            value = {"text": show(node), "binding": "unproved"}
            if isinstance(node, c_ast.ID) and node.name in state["locals"] and node.name not in shadowed | state["escaped"]:
                value.update(binding="source_local_value_version", **copy.deepcopy(state["locals"][node.name]))
            elif (isinstance(node, c_ast.UnaryOp) and node.op == "&" and isinstance(node.expr, c_ast.ID)
                  and node.expr.name in state["locals"] and node.expr.name not in shadowed):
                value.update(binding="named_declaration_address_only",
                             declaration=copy.deepcopy(state["locals"][node.expr.name]["declaration"]))
            return value
        def finish(state, status, endpoint):
            leaves.append({"status": status, "guards": state["guards"], "events": state["events"],
                           "endpoint": endpoint, "runtime_witness": False})
        while queue:
            if len(queue) + len(leaves) > max_paths:
                raise SourceError("path bound exceeded; no partial coverage claim")
            state = queue.pop()
            pc = state["pc"]
            instruction = nodes[pc]
            point = {k: instruction[k] for k in ("line", "column") if k in instruction}
            kind = instruction["kind"]
            if pc in state["seen"] or len(state["seen"]) >= max_steps:
                finish(state, "unsupported_frontier", {"reason": "cycle/step bound", **point})
                continue
            state["seen"].add(pc)
            if kind in {"frontier", "function_end", "return"}:
                finish(state, "unsupported_frontier" if kind == "frontier" else "structural_terminal",
                       {"kind": kind, **point, **({"reason": instruction["reason"]} if kind == "frontier" else {})})
                continue
            if kind == "branch":
                effects(instruction["ast"], state)
                for taken, next_pc in [(True, instruction["iftrue"]), (False, instruction["iffalse"])]:
                    alternative = copy.deepcopy(state)
                    alternative["guards"].append({"expression": instruction["expression"], "taken": taken, **point})
                    alternative["pc"] = next_pc
                    queue.append(alternative)
                continue
            if kind == "goto":
                target = labels.get(instruction["target_label"])
                target_point = nodes[target] if target is not None else {}
                if target is None or (target_point.get("line", 0), target_point.get("column", 0)) <= (point["line"], point["column"]):
                    finish(state, "unsupported_frontier", {"reason": "unresolved/nested/backward goto", **point})
                    continue
                state["events"].append({"kind": "forward_goto", "label": instruction["target_label"],
                                        "target_line": target_point["line"], **point})
                state["pc"] = target
            else:
                if kind == "call":
                    call = instruction["ast"]
                    effects(call, state)
                    state["events"].append({"kind": "call", "callee": instruction["callee"],
                                            "arguments": [argument(a, state) for a in call.args.exprs] if call.args else [],
                                            "guards_at_event": copy.deepcopy(state["guards"]), **point})
                elif kind == "statement":
                    effects(instruction["ast"], state)
                state["pc"] = instruction["next"]
            queue.append(state)
        if len(leaves) > max_paths:
            raise SourceError("path bound exceeded")
        result["paths"] = leaves
        result["status"] = "partial_forward_structure" if any(p["status"] == "unsupported_frontier" for p in leaves) else "supported_forward_structure"
    except Exception as error:
        result["paths"] = []
        result["reasons"].append(type(error).__name__ + ": " + str(error))
    return result


def indexed_field_candidates(document):
    """Find an adjacent address assignment/member-call syntax pattern.

    No loop execution, dominance, C type/alias or callee identity is inferred.
    A macro-shaped enclosing header is copied verbatim, not interpreted.
    """
    source = document["text"]
    lo, hi = document["start_line"], document["end_line"]
    if (not document.get("revision") or not document.get("path") or type(lo) is not int
            or type(hi) is not int or len(source.splitlines()) != hi - lo + 1):
        raise SourceError("source identity/interval required for binding candidate")
    tokens, pairs, _ = _lex(source)
    reverse = {end: begin for begin, end in pairs.items()}
    values = [t.value for t in tokens]
    def identifier(value):
        return bool(re.fullmatch(r"[A-Za-z_]\w*", value))
    def point(token):
        return {"line": lo + source.count("\n", 0, token.start),
                "column": token.start - source.rfind("\n", 0, token.start)}
    found = []
    for i in range(len(tokens) - 18):
        part = values[i:i + 19]
        if (not all(identifier(part[j]) for j in [0, 3, 5, 8, 11, 14, 16])
                or part[1:3] != ["=", "&"] or part[4] != "[" or part[6:8] != ["]", ";"]
                or part[9:11] != ["(", "&"] or part[12:14] != ["-", ">"]
                or part[15] != "," or part[17:19] != [")", ";"]
                or part[0] != part[11] or part[5] != part[16]):
            continue
        enclosing = [opening for opening, closing in pairs.items()
                     if values[opening] == "{" and opening < i < closing]
        header = None
        if enclosing:
            opening = max(enclosing)
            if opening > 0 and values[opening - 1] == ")":
                begin = reverse[opening - 1]
                if begin > 0 and identifier(values[begin - 1]):
                    header = {"text": source[tokens[begin - 1].start:tokens[opening].start].strip(),
                              **point(tokens[begin - 1]), "semantics": "not_resolved"}
        found.append({"document": document["id"], "revision": document["revision"], "path": document["path"],
                      "status": "lexical_binding_candidate", "alias_spelling": part[0],
                      "indexed_base_spelling": part[3], "index_spelling": part[5],
                      "callee_spelling": part[8], "member_spelling": part[14],
                      "assignment": point(tokens[i]), "call": point(tokens[i + 8]),
                      "text": source[tokens[i].start:tokens[i + 18].end], "enclosing_header": header,
                      "iteration_reaches_target": "unknown", "object_identity_proved": False,
                      "call_effects_proved": False, "evidence_layer": "adjacent_original_source_tokens"})
    return found
