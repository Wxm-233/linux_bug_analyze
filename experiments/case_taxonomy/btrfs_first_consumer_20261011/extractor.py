"""Limited C lexical facts. No preprocessor, AST, CFG, or defect classifier.

Inputs are source text and two manually selected function names. This module
does not read files, accept a target field/line, or use expected results.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
import re


IDENT = re.compile(r"[A-Za-z_]\w*\Z")
TOKEN = re.compile(
    r"[A-Za-z_]\w*|(?:0[xX][0-9a-fA-F]+|\d+)(?:[A-Za-z_]\w*)?"
    r"|>>=|<<=|->|\+\+|--|==|!=|<=|>=|&&|\|\||\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<|>>|[^\s]"
)
ASSIGN = {"=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>="}
CONTROL = {"if", "else", "while", "for", "switch", "case", "return", "goto", "break", "continue", "do", "sizeof", "typeof", "__typeof__"}
UNPROVEN = [
    "CFG_dominance", "external_call_side_effects", "true_path_reachability",
    "complete_field_type_and_layout", "source_call_definition_and_semantics",
    "macro_expansion_and_semantics", "local_assignment_reaches_field_write",
    "consumer_call_return_and_success", "applicable_format_specification",
    "actual_execution",
]


class Unsupported(ValueError):
    """A binding cannot be established within this deliberately small scope."""


def mask_noncode(text: str) -> str:
    """Blank comments/literals/directives without changing offsets or lines."""
    chars = list(text)
    i = 0
    while i < len(text):
        end = None
        if text.startswith("//", i):
            end = text.find("\n", i + 2)
            end = len(text) if end < 0 else end
        elif text.startswith("/*", i):
            close = text.find("*/", i + 2)
            if close < 0:
                raise Unsupported("unterminated_comment")
            end = close + 2
        elif text[i] in "\"'":
            quote = text[i]
            j = i + 1
            while j < len(text):
                if text[j] == "\\":
                    j += 2
                elif text[j] == quote:
                    end = j + 1
                    break
                else:
                    j += 1
            if end is None:
                raise Unsupported("unterminated_literal")
        if end is not None:
            for j in range(i, end):
                if chars[j] not in "\r\n":
                    chars[j] = " "
            i = end
        else:
            i += 1
    masked = "".join(chars)
    # Directives are not expanded. A continued directive remains fully masked.
    continuation = False
    offset = 0
    for line in masked.splitlines(keepends=True):
        directive = continuation or line.lstrip().startswith("#")
        if directive:
            for j in range(offset, offset + len(line)):
                if chars[j] not in "\r\n":
                    chars[j] = " "
        continuation = directive and line.rstrip("\r\n").rstrip().endswith("\\")
        offset += len(line)
    return "".join(chars)


@dataclass(frozen=True)
class Tok:
    value: str
    start: int
    end: int
    line: int


class Source:
    def __init__(self, text: str):
        self.text = text
        masked = mask_noncode(text)
        newlines = [i for i, c in enumerate(text) if c == "\n"]
        self.tokens = [Tok(m.group(), m.start(), m.end(), bisect_right(newlines, m.start()) + 1)
                       for m in TOKEN.finditer(masked)]
        self.pairs = {}
        self.depth = []
        stack = []
        brace_depth = 0
        for i, token in enumerate(self.tokens):
            self.depth.append(brace_depth)
            value = token.value
            if value in {"(", "[", "{"}:
                stack.append(i)
                if value == "{":
                    brace_depth += 1
            elif value in {")", "]", "}"}:
                if not stack or self.tokens[stack[-1]].value != {")": "(", "]": "[", "}": "{"}[value]:
                    raise Unsupported("unbalanced_delimiters")
                opening = stack.pop()
                self.pairs[opening] = i
                self.pairs[i] = opening
                if value == "}":
                    brace_depth -= 1
        if stack:
            raise Unsupported("unbalanced_delimiters")

    def text_between(self, first: int, last: int) -> str:
        if first > last:
            return ""
        return self.text[self.tokens[first].start:self.tokens[last].end]

    def split(self, first: int, last: int, separator: str = ",") -> list[tuple[int, int]]:
        groups = []
        start = first
        i = first
        while i <= last:
            if self.tokens[i].value in {"(", "[", "{"}:
                i = self.pairs[i] + 1
            elif self.tokens[i].value == separator:
                groups.append((start, i - 1))
                start = i + 1
                i += 1
            else:
                i += 1
        groups.append((start, last))
        return groups

    def function(self, name: str) -> dict:
        if not IDENT.fullmatch(name):
            raise Unsupported("invalid_function_name")
        definitions = []
        tokens = self.tokens
        for i, token in enumerate(tokens[:-1]):
            if token.value != name or self.depth[i] != 0 or tokens[i + 1].value != "(":
                continue
            # Only translation-unit definitions: calls inside functions cannot
            # qualify, and an initializer's '=' disqualifies its prefix.
            start = i - 1
            while start >= 0 and tokens[start].value not in {";", "}", "{"}:
                start -= 1
            prefix = [t.value for t in tokens[start + 1:i]]
            if not prefix or not any(IDENT.fullmatch(v) for v in prefix):
                continue
            if any(v in ASSIGN or v in {",", "return"} for v in prefix):
                continue
            closing = self.pairs[i + 1]
            body = closing + 1
            # Arbitrary identifier modifiers and balanced attribute arguments
            # may follow the parameter list; ';' still marks a declaration.
            while body < len(tokens) and tokens[body].value != "{":
                value = tokens[body].value
                if IDENT.fullmatch(value) or value == "*":
                    body += 1
                elif value == "(":
                    body = self.pairs[body] + 1
                else:
                    break
            if body >= len(tokens) or tokens[body].value != "{" or self.depth[body] != 0:
                continue
            definitions.append({"name_index": i, "parameter_start": i + 2,
                                "parameter_end": closing - 1, "body_start": body,
                                "body_end": self.pairs[body], "name": name})
        if len(definitions) != 1:
            raise Unsupported("function_definition_missing_or_ambiguous:" + name)
        return definitions[0]


def declarator(source: Source, first: int, last: int, inherited: list[str] | None = None) -> dict | None:
    """Recognize only simple local/parameter names, never aliases or typedef layout."""
    tokens = source.tokens
    values = [t.value for t in tokens[first:last + 1]]
    if not values or any(v in CONTROL for v in values):
        return None
    stop = next((i for i, v in enumerate(values) if v in ASSIGN or v == "["), len(values))
    head = values[:stop]
    if not head or not IDENT.fullmatch(head[-1]):
        return None
    name = head[-1]
    spec = head[:-1]
    if inherited is None:
        if not spec or any(not IDENT.fullmatch(v) and v != "*" for v in spec):
            return None
        base = [v for v in spec if v != "*"]
    else:
        if any(v != "*" and v not in {"const", "volatile", "restrict"} for v in spec):
            return None
        base = inherited
    if not base:
        return None
    pointer_count = spec.count("*")
    tag = None
    if "struct" in base:
        index = base.index("struct")
        if index + 1 < len(base):
            tag = base[index + 1]
    name_index = first + len(head) - 1
    initializer = first + stop if stop < len(values) and values[stop] == "=" else None
    return {"name": name, "struct_tag": tag, "pointer_count": pointer_count,
            "line": tokens[name_index].line, "index": name_index,
            "initializer_index": initializer, "base": base}


def locals_in(source: Source, function: dict) -> list[dict]:
    result = []
    start = function["body_start"] + 1
    tokens = source.tokens
    for i in range(start, function["body_end"]):
        if tokens[i].value in {"{", "}"}:
            start = i + 1
        elif tokens[i].value == ";":
            parts = source.split(start, i - 1)
            initial = declarator(source, *parts[0])
            if initial:
                result.append(initial)
                for part in parts[1:]:
                    extra = declarator(source, *part, inherited=initial["base"])
                    if extra:
                        result.append(extra)
            start = i + 1
    return result


def rhs_end(source: Source, first: int, body_end: int) -> int | None:
    i = first
    while i < body_end:
        value = source.tokens[i].value
        if value in {"(", "["}:
            i = source.pairs[i] + 1
        elif value == ";":
            return i - 1
        elif value in {"{", "}"}:
            return None
        else:
            i += 1
    return None


def strip_parentheses(source: Source, first: int, last: int) -> tuple[int, int]:
    while first < last and source.tokens[first].value == "(" and source.pairs[first] == last:
        first, last = first + 1, last - 1
    return first, last


def direct_call(source: Source, first: int, last: int) -> dict | None:
    first, last = strip_parentheses(source, first, last)
    tokens = source.tokens
    if first + 2 > last or not IDENT.fullmatch(tokens[first].value) or tokens[first].value in CONTROL:
        return None
    if tokens[first + 1].value != "(" or source.pairs[first + 1] != last:
        return None
    return {"name": tokens[first].value, "line": tokens[first].line,
            "expression": source.text_between(first, last), "index": first}


def simple_name_use(source: Source, index: int, name: str) -> bool:
    return (source.tokens[index].value == name and
            (index == 0 or source.tokens[index - 1].value not in {"->", "."}))


def wrapped_use(source: Source, first: int, last: int) -> tuple[int, int]:
    """Expand only parentheses that enclose exactly this token span."""
    while first > 0 and source.tokens[first - 1].value == "(" and source.pairs[first - 1] == last + 1:
        first, last = first - 1, last + 1
    return first, last


def unevaluated_use(source: Source, first: int, last: int, body_start: int) -> bool:
    """Recognize direct operands and enclosing sizeof/typeof parentheses."""
    tokens = source.tokens
    keywords = {"sizeof", "typeof", "__typeof__"}
    if first > 0 and tokens[first - 1].value in keywords:
        return True
    for opening in range(body_start + 1, first):
        if (tokens[opening].value == "(" and source.pairs[opening] >= last
                and tokens[opening - 1].value in keywords):
            return True
    return False


def name_modifications(source: Source, function: dict, name: str, declaration: dict | None = None) -> list[dict]:
    result = []
    tokens = source.tokens
    for i in range(function["body_start"] + 1, function["body_end"]):
        if not simple_name_use(source, i, name):
            continue
        left, right = wrapped_use(source, i, i)
        following = tokens[right + 1].value
        previous = tokens[left - 1].value
        if following in ASSIGN and (previous not in {"*", "&"} or
                                    declaration and declaration["initializer_index"] == right + 1):
            end = rhs_end(source, right + 2, function["body_end"])
            result.append({"index": i, "lhs_start": left, "operator": following, "rhs_start": right + 2, "rhs_end": end})
        elif following in {"++", "--"} or previous in {"++", "--"}:
            result.append({"index": i, "operator": following if following in {"++", "--"} else previous,
                           "rhs_start": None, "rhs_end": None})
    return result


def field_uses(source: Source, function: dict, object_name: str) -> list[dict]:
    result = []
    tokens = source.tokens
    for i in range(function["body_start"] + 1, function["body_end"] - 2):
        if not simple_name_use(source, i, object_name) or tokens[i + 1].value != "->" or not IDENT.fullmatch(tokens[i + 2].value):
            continue
        left, right = wrapped_use(source, i, i + 2)
        following = tokens[right + 1].value
        previous = tokens[left - 1].value
        kind = "write" if following == "=" else "read"
        if following in ASSIGN - {"="} or following in {"++", "--"} or previous in {"++", "--"}:
            kind = "read_write"
        if previous == "&":
            kind = "address_use"
        # The field may sit deep inside an unevaluated parenthesized expression.
        if unevaluated_use(source, left, right, function["body_start"]):
            kind = "unevaluated_use"
        result.append({"field": tokens[i + 2].value, "line": tokens[i].line,
                       "index": i, "lhs_start": left, "rhs_start": right + 2,
                       "kind": kind, "operator": following if following in ASSIGN else None})
    return result


def function_bounds(source: Source, function: dict) -> dict:
    return {"name": function["name"], "definition_line": source.tokens[function["name_index"]].line,
            "body_start_line": source.tokens[function["body_start"]].line,
            "body_end_line": source.tokens[function["body_end"]].line}


def extract_facts(caller_text: str, consumer_text: str, caller_name: str, consumer_name: str) -> dict:
    """Return intersecting lexical candidates, without semantic or success claims."""
    result = {"status": "limited_facts", "records": [], "unproven": list(UNPROVEN),
              "interpretation": "Text positions only; no path, reaching-definition, macro, or execution proof."}
    try:
        caller = Source(caller_text)
        consumer = Source(consumer_text)
        entry = caller.function(caller_name)
        callee = consumer.function(consumer_name)
        result["functions"] = {"caller": function_bounds(caller, entry), "consumer": function_bounds(consumer, callee)}
        first_parameter = consumer.split(callee["parameter_start"], callee["parameter_end"])[0]
        parameter = declarator(consumer, *first_parameter)
        if not parameter or not parameter["struct_tag"] or parameter["pointer_count"] != 1:
            raise Unsupported("first_parameter_not_simple_struct_pointer")
        parameter_name = parameter["name"]
        callee_locals = locals_in(consumer, callee)
        if name_modifications(consumer, callee, parameter_name) or any(d["name"] == parameter_name for d in callee_locals):
            raise Unsupported("consumer_parameter_reassigned_or_shadowed")
        reads = {}
        for use in field_uses(consumer, callee, parameter_name):
            if use["kind"] in {"read", "read_write"}:
                reads.setdefault(use["field"], []).append(use["line"])
        reads = {field: sorted(set(lines)) for field, lines in sorted(reads.items())}
        result["consumer_parameter"] = {"name": parameter_name, "struct_pointer_type": "struct " + parameter["struct_tag"] + " *",
                                        "declaration_line": parameter["line"]}
        result["consumer_direct_field_reads"] = [{"field": field, "lines": lines, "first_line": lines[0]}
                                                   for field, lines in reads.items()]
        declarations = locals_in(caller, entry)
        tokens = caller.tokens
        calls = []
        for i in range(entry["body_start"] + 1, entry["body_end"] - 1):
            if not simple_name_use(caller, i, consumer_name) or tokens[i + 1].value != "(":
                continue
            closing = caller.pairs[i + 1]
            args = caller.split(i + 2, closing - 1)
            first, last = strip_parentheses(caller, *args[0])
            if first != last or not IDENT.fullmatch(tokens[first].value):
                raise Unsupported("consumer_first_argument_not_simple_local_name")
            object_name = tokens[first].value
            matching = [d for d in declarations if d["name"] == object_name]
            if len(matching) != 1 or matching[0]["index"] >= i:
                raise Unsupported("caller_object_declaration_missing_or_shadowed")
            declaration = matching[0]
            if declaration["struct_tag"] != parameter["struct_tag"] or declaration["pointer_count"] != 1:
                raise Unsupported("caller_and_consumer_struct_pointer_types_differ")
            modifications = name_modifications(caller, entry, object_name, declaration)
            if any(m["index"] != declaration["index"] or declaration["initializer_index"] is None for m in modifications):
                raise Unsupported("caller_object_reassigned")
            calls.append({"name": consumer_name, "line": tokens[i].line, "index": i, "object": object_name,
                          "object_declaration_line": declaration["line"], "expression": caller.text_between(i, closing)})
        if not calls:
            raise Unsupported("consumer_call_not_found_in_caller")
        result["consumer_calls"] = [{k: v for k, v in call.items() if k != "index"} for call in calls]
        inventories = {}
        for call in calls:
            object_name = call["object"]
            uses = field_uses(caller, entry, object_name)
            inventories[object_name] = [{"field": u["field"], "line": u["line"], "operator": u["operator"]}
                                         for u in uses if u["kind"] in {"write", "read_write"}]
            for write in uses:
                if write["kind"] != "write" or write["field"] not in reads:
                    continue
                first = write["rhs_start"]
                last = rhs_end(caller, first, entry["body_end"])
                if last is None:
                    continue
                source_call = direct_call(caller, first, last)
                local_assignment = None
                if not source_call:
                    rhs_first, rhs_last = strip_parentheses(caller, first, last)
                    if rhs_first != rhs_last or not IDENT.fullmatch(tokens[rhs_first].value):
                        continue
                    local_name = tokens[rhs_first].value
                    local_declarations = [d for d in declarations if d["name"] == local_name]
                    if len(local_declarations) != 1:
                        continue
                    local_declaration = local_declarations[0]
                    earlier = [m for m in name_modifications(caller, entry, local_name, local_declaration)
                               if local_declaration["index"] <= m["index"] < write["index"]]
                    if not earlier:
                        continue
                    assignment = earlier[-1]
                    if assignment["operator"] != "=" or assignment["rhs_end"] is None:
                        continue
                    source_call = direct_call(caller, assignment["rhs_start"], assignment["rhs_end"])
                    if not source_call:
                        continue
                    local_assignment = {"variable": local_name, "line": tokens[assignment["index"]].line,
                                        "expression": caller.text_between(assignment["lhs_start"], assignment["rhs_end"]),
                                        "index": assignment["index"]}
                positions = [("source_call", source_call["index"]), ("field_write", write["index"]),
                             ("consumer_call", call["index"])]
                if local_assignment:
                    positions.append(("local_assignment", local_assignment["index"]))
                result["records"].append({
                    "field": write["field"], "object": object_name,
                    "struct_pointer_type": "struct " + parameter["struct_tag"] + " *",
                    "source_call": {k: v for k, v in source_call.items() if k != "index"},
                    "local_assignment": {k: v for k, v in local_assignment.items() if k != "index"} if local_assignment else None,
                    "field_write": {"line": write["line"], "expression": caller.text_between(write["lhs_start"], last)},
                    "consumer_call": {"name": call["name"], "line": call["line"], "first_argument": object_name},
                    "consumer_first_field_read_line": reads[write["field"]][0],
                    "consumer_field_read_lines": reads[write["field"]],
                    "relation": "source_write_before_call" if write["index"] < call["index"] else "source_write_after_call",
                    "caller_text_order": [label for label, _ in sorted(positions, key=lambda p: p[1])],
                    "evidence_status": "lexical_candidate",
                })
        result["caller_field_writes"] = inventories
    except Unsupported as error:
        result["status"] = "insufficient"
        result["reason"] = str(error)
        result["records"] = []
    return result
