"""Syntax-grounded local call/guard evidence, not arbitrary kernel semantics.

Only complete C function snippets in a deliberately small subset are accepted.
Calls are opaque and assumed to return normally for intraprocedural reasoning.
Source order never establishes preparation effects, object contents or runtime
reachability. Unsupported control flow retains inventory but yields no proof.
"""

from __future__ import annotations

import copy
import hashlib
import re
from typing import Any

try:
    from pycparser import c_ast, c_generator, c_parser
except ImportError:  # Optional research dependency; ordinary CLIs are unaffected.
    c_ast = c_generator = c_parser = None


class SourceError(ValueError):
    pass


def _comments(text: str) -> str:
    # Reject translation-phase constructs this small frontend does not normalize.
    if "\\\n" in text or "\\\r\n" in text or "??" in text:
        raise SourceError("line splicing/trigraph handling is outside this frontend")
    pattern = r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''
    def replace(match):
        token = match[0]
        return "".join("\n" if c == "\n" else " " for c in token) if token.startswith(("/*", "//")) else token
    return re.sub(pattern, replace, text, flags=re.S)


def analyze_function(document: dict[str, Any], *, type_names=("bool", "cpumask_t"),
                     annotations=(), max_paths: int = 64) -> dict[str, Any]:
    """Extract source facts; no architecture/function names are built into core."""
    result = {
        "document": document.get("id"), "revision": document.get("revision"),
        "path": document.get("path"), "function": None, "status": "insufficient",
        "calls": [], "conditions": [], "paths": [], "reasons": [],
        "whole_contract": "insufficient", "runtime_reachability_proved": False,
        "semantic_layer": "unpreprocessed_C_shape",
        "assumptions": ["opaque calls return normally; no interprocedural effects proof",
                        "branch alternatives are structural overapproximations, not feasible runtime witnesses",
                        "syntax-only typedef stubs do not establish real C types or configuration",
                        "call-shaped names are treated as C calls; hidden macro expansion is not established"],
        "type_stubs": list(type_names), "masked_annotations": list(annotations),
    }
    try:
        if c_parser is None:
            raise SourceError("optional research dependency pycparser is unavailable")
        lo, hi, source = document.get("start_line"), document.get("end_line"), document.get("text")
        if type(lo) is not int or type(hi) is not int or lo < 1 or not isinstance(source, str) or len(source.splitlines()) != hi - lo + 1:
            raise SourceError("source interval is missing/noncontiguous")
        if not document.get("revision") or not document.get("path"):
            raise SourceError("source identity is missing")
        if type(max_paths) is not int or not 1 <= max_paths <= 256:
            raise SourceError("invalid path bound")
        result.update(start_line=lo, end_line=hi, source_sha256=hashlib.sha256(source.encode()).hexdigest())
        clean = _comments(source)
        if re.search(r"^\s*#", clean, re.M):
            raise SourceError("preprocessor directives require effective preprocessing, not deletion")
        for name in (*type_names, *annotations):
            if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z_]\w*", name):
                raise SourceError("invalid parse-stub/annotation identifier")
        if not set(annotations) <= {"__init", "__always_inline", "__maybe_unused"}:
            raise SourceError("unsupported annotation masking request")
        header_end = clean.find("{")
        for name in annotations:
            tokens = r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|\b' + re.escape(name) + r'\b'
            header = re.sub(tokens, lambda m: m[0] if m[0].startswith(('"', "'")) else " " * len(m[0]), clean[:header_end])
            clean = header + clean[header_end:]
        prefix = "".join("typedef int " + name + ";\n" for name in type_names)
        ast = c_parser.CParser().parse(prefix + clean, filename=document["path"])
        functions = [n for n in ast.ext if isinstance(n, c_ast.FuncDef)]
        if len(functions) != 1 or len(ast.ext) != len(type_names) + 1:
            raise SourceError("exactly one complete function is required")
        function = functions[0]
        result["function"] = function.decl.name
        parameters = function.decl.type.args.params if function.decl.type.args else []
        parameter_names = {p.name for p in parameters if isinstance(p, c_ast.Decl) and p.name}
        generator = c_generator.CGenerator()
        prefix_lines = len(type_names)
        def position(node):
            return {"line": node.coord.line - prefix_lines + lo - 1, "column": node.coord.column}
        def text(node):
            return generator.visit(node)
        class Inventory(c_ast.NodeVisitor):
            def __init__(self):
                self.unsupported = []
                self.declarations = {}
                self.pointer_names = set()
                self.object_names = set()
            def generic_visit(self, node):
                if isinstance(node, (c_ast.For, c_ast.While, c_ast.DoWhile, c_ast.Goto,
                                     c_ast.Label, c_ast.Switch, c_ast.Break, c_ast.Continue,
                                     c_ast.TernaryOp)):
                    self.unsupported.append({"kind": type(node).__name__, **position(node)})
                super().generic_visit(node)
            def visit_FuncCall(self, node):
                direct = isinstance(node.name, c_ast.ID)
                result["calls"].append({"callee": node.name.name if direct else text(node.name),
                                        "arguments": [text(a) for a in node.args.exprs] if node.args else [],
                                        "direct": direct, **position(node)})
                if not direct:
                    self.unsupported.append({"kind": "indirect_call", **position(node)})
                self.generic_visit(node)
            def visit_If(self, node):
                result["conditions"].append({"expression": text(node.cond), **position(node)})
                self.generic_visit(node)
            def visit_Decl(self, node):
                if node.name:
                    self.declarations[node.name] = self.declarations.get(node.name, 0) + 1
                    if not isinstance(node.type, c_ast.FuncDecl):
                        self.object_names.add(node.name)
                    if not isinstance(node.type, c_ast.FuncDecl) and any(isinstance(n, c_ast.FuncDecl) for n in _nodes(node.type)):
                        self.pointer_names.add(node.name)
                self.generic_visit(node)
        inventory = Inventory()
        inventory.visit(function)
        result["calls"].sort(key=lambda x: (x["line"], x["column"]))
        for call in result["calls"]:
            if call["callee"] in inventory.pointer_names | inventory.object_names | parameter_names:
                call["direct"] = False
                inventory.unsupported.append({"kind": "function_pointer_identifier", "line": call["line"], "column": call["column"]})
        if inventory.unsupported:
            result["unsupported"] = inventory.unsupported
            raise SourceError("unsupported control flow/call: inventory only, no complete-flow claim")
        shadowed = {name for name, count in inventory.declarations.items() if count > 1}
        initial = {p.name: "parameter:" + p.name for p in parameters if isinstance(p, c_ast.Decl) and p.name}
        if shadowed:
            result["shadowed_names"] = sorted(shadowed)
        result["parameters"] = sorted(initial)
        complete = []
        def version(node):
            p = position(node)
            return str(p["line"]) + ":" + str(p["column"])
        def effects(node, state):
            if node is None:
                return
            if isinstance(node, c_ast.UnaryOp) and node.op == "&" and isinstance(node.expr, c_ast.ID):
                state["escaped"].add(node.expr.name)
            if isinstance(node, c_ast.Assignment) and isinstance(node.lvalue, c_ast.ID):
                state["locals"][node.lvalue.name] = "write:" + version(node)
            if isinstance(node, c_ast.UnaryOp) and node.op in {"p++", "p--", "++", "--"} and isinstance(node.expr, c_ast.ID):
                state["locals"][node.expr.name] = "write:" + version(node)
            for _, child in node.children():
                effects(child, state)
        def check_bound(states):
            if len(states) + len(complete) > max_paths:
                raise SourceError("structural path bound exceeded")
            return states
        def walk(node, state):
            if node is None:
                return [state]
            if isinstance(node, c_ast.Compound):
                states = [state]
                for child in node.block_items or []:
                    states = check_bound([out for current in states for out in walk(child, current)])
                return states
            if isinstance(node, c_ast.If):
                # Side effects in predicates require a richer expression CFG.
                if any(isinstance(n, (c_ast.Assignment, c_ast.UnaryOp)) and
                       (isinstance(n, c_ast.Assignment) or n.op in {"p++", "p--", "++", "--"})
                       for n in _nodes(node.cond)):
                    raise SourceError("side effects in condition are unsupported")
                effects(node.cond, state)
                states = []
                for taken, branch in ((True, node.iftrue), (False, node.iffalse)):
                    alternative = copy.deepcopy(state)
                    alternative["guards"].append({"expression": text(node.cond), "taken": taken, **position(node)})
                    states.extend(walk(branch, alternative))
                return check_bound(states)
            if isinstance(node, c_ast.Return):
                effects(node.expr, state)
                state["exit"] = {"kind": "return", **position(node)}
                complete.append(state)
                check_bound([])
                return []
            if isinstance(node, c_ast.Decl):
                if node.name:
                    state["locals"][node.name] = "declaration:" + version(node)
                effects(node.init, state)
                return [state]
            if isinstance(node, c_ast.FuncCall):
                effects(node, state)
                args = node.args.exprs if node.args else []
                local_args = []
                for arg in args:
                    identity = None
                    if isinstance(arg, c_ast.ID) and arg.name not in state["escaped"] | shadowed:
                        identity = state["locals"].get(arg.name)
                    local_args.append(identity)
                state["events"].append({"callee": node.name.name, "arguments": [text(a) for a in args],
                                         "local_argument_versions": local_args,
                                         "guards_at_event": copy.deepcopy(state["guards"]), **position(node)})
                return [state]
            if isinstance(node, (c_ast.Assignment, c_ast.UnaryOp, c_ast.EmptyStatement)):
                effects(node, state)
                return [state]
            raise SourceError("unsupported statement: " + type(node).__name__)
        live = walk(function.body, {"guards": [], "events": [], "locals": initial, "escaped": set()})
        for state in live:
            state["exit"] = {"kind": "function_end"}
        for state in complete + live:
            state["escaped"] = sorted(state["escaped"])
        result["paths"] = complete + live
        result["status"] = "bounded_local_flow"
    except Exception as exc:
        # Parsing failures and unsupported syntax are data, not model retries.
        result["reasons"].append(type(exc).__name__ + ": " + str(exc))
        result["paths"] = []
    return result


def _nodes(node):
    yield node
    for _, child in node.children():
        yield from _nodes(child)


def check_source_claim(analysis: dict[str, Any], claim: dict[str, Any]) -> dict[str, Any]:
    """Check an unchanged source claim; never auto-adopt it as a contract."""
    result = {"claim_id": claim.get("id"), "status": "insufficient", "reasons": [],
              "whole_contract": "insufficient", "runtime_witness": False,
              "object_identity": "unproved", "source_claim": copy.deepcopy(claim)}
    try:
        if analysis["status"] != "bounded_local_flow":
            raise SourceError("complete supported function flow unavailable")
        if (claim.get("document") != analysis["document"] or claim.get("function") != analysis["function"]
                or claim.get("revision") != analysis["revision"]):
            raise SourceError("claim has a different document/revision/function scope")
        if "path" in claim and claim["path"] != analysis["path"]:
            raise SourceError("claim has a different source path")
        def anchor(key):
            supplied = claim.get(key)
            if not isinstance(supplied, dict):
                raise SourceError("missing call anchor: " + key)
            if type(supplied.get("line")) is not int or ("column" in supplied and type(supplied["column"]) is not int):
                raise SourceError("invalid call coordinates: " + key)
            choices = [c for c in analysis["calls"] if c["callee"] == supplied.get("callee")
                       and c["line"] == supplied.get("line")
                       and ("column" not in supplied or c["column"] == supplied["column"])]
            if len(choices) != 1:
                raise SourceError("missing/ambiguous source call anchor: " + key)
            if "arguments" in supplied and supplied["arguments"] != choices[0]["arguments"]:
                raise SourceError("call arguments differ from the source anchor: " + key)
            return choices[0]
        def matches(event, selected):
            return all(event[k] == selected[k] for k in ("callee", "line", "column"))
        target = anchor("target")
        reached = []
        for path in analysis["paths"]:
            indices = [i for i, event in enumerate(path["events"]) if matches(event, target)]
            if indices:
                reached.append((path, indices[0]))
        if not reached:
            raise SourceError("anchor is nested/conditional expression or not a standalone call event")
        kind = claim.get("kind")
        if kind == "before":
            first = anchor("first")
            decisions = [any(matches(e, first) for e in p["events"][:i]) for p, i in reached]
            pairs = [(next(e for e in p["events"][:i] if matches(e, first)), p["events"][i])
                     for (p, i), ok in zip(reached, decisions) if ok]
            if pairs and all(decisions):
                index = claim.get("argument_index")
                if type(index) is int and index >= 0:
                    result["object_identity"] = "same_local_argument_version_only" if all(
                        len(a["local_argument_versions"]) > index and len(b["local_argument_versions"]) > index
                        and a["local_argument_versions"][index] is not None
                        and a["local_argument_versions"][index] == b["local_argument_versions"][index]
                        for a, b in pairs) else "unproved"
        elif kind == "unconditional_call":
            decisions = [any(matches(e, target) for e in p["events"]) for p in analysis["paths"]]
        elif kind == "requires_branch":
            branch = claim.get("branch", {})
            if type(branch.get("line")) is not int or type(branch.get("taken")) is not bool:
                raise SourceError("invalid branch anchor")
            choices = [c for c in analysis["conditions"] if c["line"] == branch["line"]]
            if len(choices) != 1:
                raise SourceError("ambiguous/missing branch anchor")
            decisions = [any(g["line"] == branch["line"] and g["taken"] == branch["taken"]
                             for g in p["events"][i]["guards_at_event"]) for p, i in reached]
        else:
            raise SourceError("unsupported source claim kind")
        result["status"] = "verified_local_structure" if all(decisions) else "not_established"
        result["guards_to_target"] = [p["events"][i]["guards_at_event"] for p, i in reached]
        result["reasons"].append("Conditional, intraprocedural structure only; calls' effects, feasible paths and interface authority are not proved.")
    except (SourceError, KeyError, TypeError) as exc:
        result["reasons"].append(str(exc))
    return result
