"""Bounded facts for reviewed source queries; never a whole-kernel verdict.

The caller supplies one revision and an already selected function/field. No
patch, version label, or manual verdict is used to classify an operation.
"""
from __future__ import annotations

import ast
import hashlib
import re
from dataclasses import dataclass
from functools import cached_property

from endian_consumer_single_revision import (
    closing_delimiter, mask_comments_and_literals,
)

IDENT = r"[A-Za-z_]\w*"
SCALAR = r"(?:__(?:le|be)(?:16|32|64)|[us](?:8|16|32|64))"


@dataclass(frozen=True)
class Source:
    path: str
    revision: str
    saved_path: str
    blob: str
    raw: bytes

    @cached_property
    def text(self):
        return self.raw.decode("utf-8")

    @cached_property
    def clean(self):
        return mask_comments_and_literals(self.text)

    def cite(self, begin, end):
        first = self.text.count("\n", 0, begin) + 1
        last = self.text.count("\n", 0, max(begin, end - 1)) + 1
        return dict(revision=self.revision, source_path=self.path,
                    saved_path=self.saved_path, blob_sha1=self.blob,
                    sha256=hashlib.sha256(self.raw).hexdigest(),
                    start_line=first, end_line=last,
                    text="\n".join(self.text.splitlines()[first - 1:last]))


def fail(reason):
    return dict(status="insufficient", reason=reason)


def function(src, name):
    # One-line return type, possibly multiline arguments. No K&R or macro heads.
    pattern = rf"(?m)^[ \t]*[A-Za-z_][\w \t*]*\b(?P<name>{re.escape(name)})\s*\("
    found = []
    for m in re.finditer(pattern, src.clean):
        opening = m.end() - 1
        close = closing_delimiter(src.clean, opening, "(", ")")
        if close is None:
            continue
        body = close + 1
        while body < len(src.clean) and src.clean[body].isspace():
            body += 1
        if body >= len(src.clean) or src.clean[body] != "{":
            continue
        end = closing_delimiter(src.clean, body, "{", "}")
        if end is not None:
            found.append(dict(start=m.start(), name_start=m.start("name"),
                              params=src.clean[opening + 1:close],
                              body=body + 1, end=end,
                              header=src.clean[m.start():body]))
    if len(found) != 1:
        raise ValueError("function definition absent or ambiguous: " + name)
    f = found[0]
    if re.search(r"(?m)^\s*#", src.clean[f["start"]:f["end"]]):
        raise ValueError("conditional/macro directives inside selected function")
    if re.search(r"\(\s*\{|\b_Generic\s*\(", src.clean[f["body"]:f["end"]]):
        raise ValueError("GNU statement expression/_Generic evaluation context unsupported")
    return f


def field(src, structure, member):
    found = []
    for m in re.finditer(rf"\bstruct\s+{re.escape(structure)}\s*\{{", src.clean):
        end = closing_delimiter(src.clean, m.end() - 1, "{", "}")
        if end is None:
            continue
        depth = 0
        begin = m.end()
        for hit in re.finditer(rf"\b(?P<type>{SCALAR})\s+{re.escape(member)}\s*;",
                               src.clean[begin:end]):
            prefix = src.clean[begin:begin + hit.start()]
            depth = prefix.count("{") - prefix.count("}")
            if depth == 0:
                a, b = begin + hit.start(), begin + hit.end()
                found.append(dict(type=hit.group("type"), evidence=src.cite(a, b)))
    if len(found) != 1:
        raise ValueError("direct scalar declaration absent or ambiguous")
    return found[0]


def representation(type_name):
    m = re.fullmatch(r"__(le|be)(16|32|64)", type_name)
    return m.group(1) if m else "unknown_external_format"


def bind_object(src, f, obj, structure):
    segment = src.clean[f["start"]:f["end"]]
    if multi_declaration_mentions(src.clean[f["body"]:f["end"]], obj):
        raise ValueError("multi-declarator object binding unsupported")
    # Reject aliases/shadows even if their declaration is later than the target.
    expected = list(re.finditer(rf"\bstruct\s+{re.escape(structure)}\s*\*\s*{re.escape(obj)}\b", segment))
    declarations = list(re.finditer(
        rf"\b(?:struct\s+{IDENT}|{SCALAR}|int|long|unsigned\s+int|char|void)\s+\**\s*{re.escape(obj)}\b", segment))
    if len(expected) != 1 or len(declarations) != 1:
        raise ValueError("object binding absent, unsupported, or shadowed")
    # An opaque typedef must not evade the known-type shadow check. This
    # deliberately also rejects some exotic expressions rather than guessing.
    for m in re.finditer(rf"\b({IDENT})\s+\**\s*{re.escape(obj)}\s*(?=[;,=)\[])", segment):
        if m.group(1) not in (structure, "return"):
            raise ValueError("opaque local declaration may shadow object")
    return src.cite(f["start"] + expected[0].start(),
                    f["start"] + expected[0].end())


def multi_declaration_mentions(body, identifier):
    for m in re.finditer(r"(?:\A|(?<=[;{}]))([^;{}]+);", body):
        statement = m.group(1).strip()
        if statement.startswith(("return ", "goto ")):
            continue
        if re.match(rf"(?:struct\s+{IDENT}|{IDENT})\s+[*\w]", statement) and "," in statement and re.search(rf"\b{re.escape(identifier)}\b", statement):
            return True
    return False


def calls(src, begin, end, name):
    result = []
    for m in re.finditer(rf"\b{re.escape(name)}\s*\(", src.clean[begin:end]):
        opening = begin + m.end() - 1
        close = closing_delimiter(src.clean, opening, "(", ")")
        if close is None or close > end:
            raise ValueError("unbalanced call")
        args, start, stack = [], opening + 1, []
        for i in range(opening + 1, close):
            c = src.clean[i]
            if c in "([{":
                stack.append(c)
            elif c in ")]}":
                if not stack or "([{\"".index(stack[-1]) != ")]}\"".index(c):
                    raise ValueError("unbalanced argument")
                stack.pop()
            elif c == "," and not stack:
                args.append(src.clean[start:i].strip())
                start = i + 1
        args.append(src.clean[start:close].strip())
        result.append(dict(begin=begin + m.start(), end=close + 1,
                           args=args, evidence=src.cite(begin + m.start(), close + 1)))
    return result


def unwrap(expr):
    expr = expr.strip()
    while expr.startswith("("):
        end = closing_delimiter(expr, 0, "(", ")")
        if end != len(expr) - 1:
            break
        expr = expr[1:-1].strip()
    return expr


def exact_call(expression, name):
    expression = expression.strip()
    start = re.match(rf"{re.escape(name)}\s*\(", expression)
    if not start:
        return False
    return closing_delimiter(expression, start.end() - 1, "(", ")") == len(expression) - 1


def macro_override(src, names):
    alternatives = "|".join(re.escape(n) for n in names)
    return bool(re.search(rf"(?m)^\s*#\s*(?:define|undef)\s+(?:{alternatives})\b", src.clean))


def constant(src, expression):
    """Literal integer/OR and unique direct integer macros. No C execution."""
    evidence = []
    expression = unwrap(expression)
    for name in set(re.findall(IDENT, re.sub(r"0[xX][0-9a-fA-F]+", "0", expression))):
        definitions = list(re.finditer(rf"(?m)^\s*#\s*define\s+{re.escape(name)}\s+([^\n]+)", src.clean))
        if len(definitions) != 1:
            raise ValueError("macro absent or multiply defined")
        value = unwrap(definitions[0].group(1))
        if not re.fullmatch(r"(?:0[xX][0-9a-fA-F]+|0|[1-9][0-9]*)(?:[uUlL]+)?", value):
            raise ValueError("macro is not a direct literal")
        value = re.sub(r"[uUlL]+$", "", value)
        expression = re.sub(rf"\b{re.escape(name)}\b", value, expression)
        evidence.append(src.cite(definitions[0].start(), definitions[0].end()))
    expression = re.sub(r"(?<=[0-9a-fA-F])[uUlL]+\b", "", expression)
    tree = ast.parse(expression, mode="eval")

    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) is int and node.value >= 0:
            return node.value
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return visit(node.left) | visit(node.right)
        raise ValueError("expression outside literal/OR grammar")
    return dict(value=visit(tree.body), evidence=evidence,
                limitation="visible literal definitions; no preprocessor configuration proof")


def scalar_reads(src, declaration_src, name, obj, structure, member):
    if src.revision != declaration_src.revision:
        raise ValueError("declaration from different revision")
    f = function(src, name)
    declaration = field(declaration_src, structure, member)
    if macro_override(src, [obj, member, "le16_to_cpu", "le32_to_cpu", "le64_to_cpu", "be16_to_cpu", "be32_to_cpu", "be64_to_cpu", "cpu_to_le32", "cpu_to_le64", "cpu_to_be32", "cpu_to_be64"]) or macro_override(declaration_src, [structure, member]):
        raise ValueError("local macro override of a field/helper binding")
    binding = bind_object(src, f, obj, structure)
    access = rf"{re.escape(obj)}\s*->\s*{re.escape(member)}\b"
    output = []
    for condition in calls(src, f["body"], f["end"], "if"):
        if len(condition["args"]) != 1:
            continue
        expression = condition["args"][0]
        for occurrence in re.finditer(access, expression):
            # Classification is restricted to a standalone logical atom, with
            # any conversion tied to this exact occurrence, not the whole if.
            pieces = re.split(r"&&|\|\|", expression)
            cursor = 0
            atom = None
            for piece in pieces:
                if cursor <= occurrence.start() < cursor + len(piece):
                    atom = unwrap(piece)
                    break
                cursor += len(piece) + 2
            status, use, reason = "insufficient", "unresolved_expression", "outside atomic grammar"
            text = occurrence.group()
            literal = re.escape(text)
            rep = representation(declaration["type"])
            bits = re.search(r"(16|32|64)$", declaration["type"]).group(1)
            convert = rf"{rep}{bits}_to_cpu\s*\(\s*{literal}\s*\)"
            subject = rf"(?:{literal}|{convert})"
            if atom and len(list(re.finditer(access, atom))) == 1:
                if re.fullmatch(rf"!?\s*{subject}", atom) or re.fullmatch(rf"{subject}\s*(?:==|!=)\s*0", atom) or re.fullmatch(rf"0\s*(?:==|!=)\s*{subject}", atom):
                    status, use, reason = "normal", "zero_presence", "local endian-invariant zero/presence test"
                elif re.fullmatch(rf"{convert}\s*&\s*.+", atom, re.S):
                    status, use, reason = "normal", "masked_read", "conversion of this read before mask"
                elif re.fullmatch(rf"{literal}\s*&\s*.+", atom, re.S):
                    mask = re.fullmatch(rf"{literal}\s*&\s*(.+)", atom, re.S).group(1)
                    if rep in ("le", "be") and exact_call(mask, f"cpu_to_{rep}{bits}"):
                        status, use, reason = "normal", "masked_read", "whole mask operand converted into the field domain"
                    elif rep in ("le", "be"):
                        status, use, reason = "candidate", "masked_read", "declared endian field used with an unconverted mask; mask value needs evidence"
                elif re.fullmatch(rf"{convert}\s*(?:==|!=|<|>)\s*[0-9]+", atom):
                    status, use, reason = "normal", "numeric_read", "conversion of this occurrence before numeric comparison"
            if not atom or len(list(re.finditer(access, atom))) != 1:
                reason = "multiple/complex references in one logical atom"
            output.append(dict(status=status, reason=reason, use_kind=use,
                               direction="read", runtime_operation="evaluated_if_reached",
                               expression=atom or expression,
                               format_carriers=[dict(kind="type_annotation", **declaration)],
                               object_binding=binding, evidence=condition["evidence"],
                               applicability="unknown_runtime_path", whole_condition_certified=False,
                               normal_scope="local_occurrence_shape", helper_semantics_from_full_preprocessing=False))
    return output or [fail("no supported if occurrence")]


def sizeof_references(src, declaration_src, name, obj, structure, member):
    if src.revision != declaration_src.revision:
        raise ValueError("declaration from different revision")
    f = function(src, name)
    declaration = field(declaration_src, structure, member)
    binding = bind_object(src, f, obj, structure)
    result = []
    for call in calls(src, f["body"], f["end"], "sizeof"):
        if call["args"] == [f"{obj}->{member}"]:
            result.append(dict(status="not_value_read", use_kind="fixed_scalar_size_reference",
                               direction="none", runtime_operation="operand_not_evaluated",
                               declaration=declaration, object_binding=binding,
                               evidence=call["evidence"], scalar_only=True))
    return result or [fail("no fixed direct scalar sizeof reference")]


def visible_call_domain(src, name, argument_index):
    f = function(src, name)
    if not re.search(r"\bstatic\b", f["header"]):
        return fail("function not static; visible file does not bound references")
    references = list(re.finditer(rf"\b{re.escape(name)}\b", src.clean))
    direct = calls(src, 0, len(src.clean), name)
    direct = [c for c in direct if c["begin"] != f["name_start"]]
    if len(references) != len(direct) + 1 or not direct:
        return fail("address escape, hidden/noncall reference, or no caller")
    # Conditional compilation in the reference file requires a real frontend.
    if re.search(r"(?m)^\s*#\s*(?:if|ifdef|ifndef|elif|else|undef)\b", src.clean):
        return fail("preprocessor conditional domain unsupported")
    values, citations = [], []
    for call in direct:
        if len(call["args"]) <= argument_index:
            return fail("argument count")
        try:
            parsed = constant(src, call["args"][argument_index])
        except (ValueError, SyntaxError):
            return fail("call argument value not established")
        # Calls inside selected function would need recursive value flow.
        if f["body"] <= call["begin"] <= f["end"]:
            return fail("recursive caller domain unsupported")
        values.append(parsed["value"])
        citations.extend([call["evidence"], *parsed["evidence"]])
    return dict(status="visible_direct_calls_only", values=sorted(set(values)),
                all_zero=all(v == 0 for v in values), call_count=len(direct),
                evidence=citations, runtime_reachability="unknown",
                limitation="same saved file direct references; not a runtime or tree-wide proof")


def initializer_write(src, name, structure, obj, member, parameter):
    f = function(src, name)
    declaration = field(src, structure, member)
    params = list(re.finditer(rf"\b({SCALAR})\s+{re.escape(parameter)}\b", f["params"]))
    body = src.clean[f["body"]:f["end"]]
    if multi_declaration_mentions(body, obj) or multi_declaration_mentions(body, parameter):
        return fail("multi-declarator source/target binding unsupported")
    initializers = list(re.finditer(rf"\bstruct\s+{re.escape(structure)}\s+{re.escape(obj)}\s*=\s*\{{", body))
    if len(params) != 1 or len(initializers) != 1:
        return fail("parameter/object binding ambiguous")
    object_declarations = list(re.finditer(rf"\b(?:struct\s+{IDENT}|{SCALAR}|{IDENT})\s+\**\s*{re.escape(obj)}\s*(?=[=;,])", body))
    if len(object_declarations) != 1:
        return fail("target object shadow/alias declaration")
    # Unsupported local declarations of source parameter or target object reject.
    if re.search(rf"\b(?:{SCALAR}|int|long|struct\s+{IDENT})\s+\**\s*{re.escape(parameter)}\b", body):
        return fail("source parameter shadowed")
    if re.search(rf"\b{IDENT}\s+\**\s*{re.escape(parameter)}\s*(?=[=;,])", body):
        return fail("opaque source parameter shadow")
    if re.search(rf"(?<![\w.>]){re.escape(parameter)}\s*(?:=(?!=)|[+\-*/|&^]=|\+\+|--)|(?:\+\+|--|&)\s*\b{re.escape(parameter)}\b", body):
        return fail("source parameter reassigned or address escapes")
    start = f["body"] + initializers[0].end() - 1
    end = closing_delimiter(src.clean, start, "{", "}")
    if end is None:
        return fail("initializer not closed")
    assignments = list(re.finditer(rf"\.{re.escape(member)}\s*=\s*([^,{{}}]+)", src.clean[start + 1:end]))
    if len(assignments) != 1:
        return fail("member initializer ambiguous")
    rhs = assignments[0].group(1).strip()
    rhs_begin = start + 1 + assignments[0].start(1) - f["body"]
    rhs_end = start + 1 + assignments[0].end(1) - f["body"]
    source_refs = list(re.finditer(rf"(?<![\w.>]){re.escape(parameter)}\b", body))
    if len(source_refs) != 1 or not (rhs_begin <= source_refs[0].start() < rhs_end):
        return fail("source parameter has references outside the direct initializer; value flow unsupported")
    rep = representation(declaration["type"])
    bits = re.search(r"(16|32|64)$", declaration["type"]).group(1)
    if macro_override(src, [parameter, obj, member, f"cpu_to_{rep}{bits}"]):
        return fail("local macro override of source/target/conversion")
    same_width_host = params[0].group(1) == "u" + bits
    status = "normal" if same_width_host and re.fullmatch(rf"cpu_to_{rep}{bits}\s*\(\s*{re.escape(parameter)}\s*\)", rhs) else "candidate" if rhs == parameter and same_width_host else "insufficient"
    return dict(status=status, use_kind="designated_initializer", direction="write",
                runtime_operation="evaluated_if_reached", source_type=params[0].group(1),
                format_carriers=[dict(kind="type_annotation", **declaration)], rhs=rhs,
                source_parameter_unchanged_in_supported_body=True,
                handoff_value_certified=False,
                evidence=src.cite(start + 1 + assignments[0].start(), start + 1 + assignments[0].end()),
                runtime_fault_proven=False,
                check_proposal="check field representation at the actual handoff, subject to value domain and format authority")


def api_format(src, helper_src, name):
    if src.revision != helper_src.revision:
        raise ValueError("helper from different revision")
    f = function(src, name)
    matches = calls(src, f["body"], f["end"], "utf8s_to_utf16s")
    if len(matches) != 1 or len(matches[0]["args"]) != 5:
        return fail("API call not unique/unsupported arity")
    call = matches[0]
    selector = call["args"][2]
    selected = src.clean[f["start"]:f["end"]]
    if len(re.findall(r"\butf8s_to_utf16s\b", selected)) != 1:
        return fail("API symbol has additional local references/declaration")
    if re.search(rf"\b{IDENT}\s+\**\s*UTF16_LITTLE_ENDIAN\s*(?=[=;,)])", selected) or re.search(r"(?:\{|,)\s*UTF16_LITTLE_ENDIAN\s*=", selected):
        return fail("format selector locally shadowed")
    for unit in (src, helper_src):
        if re.search(r"(?m)^\s*#\s*(?:define|undef)\s+(?:UTF16_LITTLE_ENDIAN|utf8s_to_utf16s|put_utf16|__cpu_to_le16)\b", unit.clean):
            return fail("API/selector/helper macro override in saved file")
    helper = function(helper_src, "put_utf16")
    body = helper_src.clean[helper["body"]:helper["end"]]
    pattern = r"case\s+UTF16_LITTLE_ENDIAN\s*:\s*\*s\s*=\s*__cpu_to_le16\s*\(\s*c\s*\)\s*;"
    implementation = list(re.finditer(pattern, body))
    # Presence is a local implementation fact, not proof of the whole encoder.
    # Refuse branch, overwrite, or dispatcher variations instead of treating a
    # coincidental LE assignment as semantics of the complete helper.
    helper_shape = r"\s*switch\s*\(\s*endian\s*\)\s*\{\s*default\s*:\s*\*s\s*=\s*\(wchar_t\)\s*c\s*;\s*break\s*;\s*case\s+UTF16_LITTLE_ENDIAN\s*:\s*\*s\s*=\s*__cpu_to_le16\s*\(\s*c\s*\)\s*;\s*break\s*;\s*case\s+UTF16_BIG_ENDIAN\s*:\s*\*s\s*=\s*__cpu_to_be16\s*\(\s*c\s*\)\s*;\s*break\s*;\s*\}\s*"
    parameter_shape = r"\s*wchar_t\s*\*\s*s\s*,\s*unsigned\s+c\s*,\s*enum\s+utf16_endian\s+endian\s*"
    helper_matches = bool(re.fullmatch(helper_shape, body, re.S) and re.fullmatch(parameter_shape, helper["params"]))
    forwarding = []
    try:
        encoder = function(helper_src, "utf8s_to_utf16s")
        forwarding = calls(helper_src, encoder["body"], encoder["end"], "put_utf16")
        forwarding_valid = bool(forwarding) and all(len(c["args"]) == 3 and c["args"][2] == "endian" for c in forwarding)
    except ValueError:
        forwarding_valid = False
    supported = selector == "UTF16_LITTLE_ENDIAN" and len(implementation) == 1 and helper_matches and forwarding_valid
    carriers = [dict(kind="api_parameter", value=selector, argument_index=2,
                     evidence=call["evidence"])]
    if len(implementation) == 1:
        m = implementation[0]
        carriers.append(dict(kind="local_helper_implementation", format="le16",
            evidence=helper_src.cite(helper["body"] + m.start(), helper["body"] + m.end())))
    return dict(status="normal" if supported else "insufficient",
                use_kind="api_output_buffer", direction="write", runtime_operation="evaluated_if_reached",
                output_argument=call["args"][3], format_carriers=carriers,
                pointer_spelling_determines_format=False, whole_encoder_certified=False,
                bounded_helper_shape_supported=helper_matches,
                encoder_helper_forwarding=[c["evidence"] for c in forwarding],
                encoder_dataflow_certified=False, normal_scope="explicit_selector_and_supported_local_helper_shape",
                helper_semantics_from_full_preprocessing=False,
                check_proposal="check explicit selector and actual reader; pointer cast alone is not a format repair")


def bitfield_read(src, declaration_src, name, obj, structure, member, mode_src):
    if len({src.revision, declaration_src.revision, mode_src.revision}) != 1:
        raise ValueError("declaration/mode from different revision")
    f = function(src, name)
    declaration = field(declaration_src, structure, member)
    binding = bind_object(src, f, obj, structure)
    segment = src.clean[f["body"]:f["end"]]
    pattern = rf"\b({IDENT})\s*=\s*((?:u|le|be)64_get_bits)\s*\(\s*{re.escape(obj)}->{re.escape(member)}\s*,\s*({IDENT})\s*\)\s*;"
    matches = list(re.finditer(pattern, segment))
    if len(matches) != 1:
        return fail("direct bitfield read absent/ambiguous")
    m = matches[0]
    rep = representation(declaration["type"])
    if macro_override(src, [m.group(2), obj, member]) or macro_override(declaration_src, [structure, member]):
        return fail("local macro override of bitfield binding/helper")
    helper_rep = "le" if m.group(2).startswith("le") else "be" if m.group(2).startswith("be") else "host_numeric_helper"
    same_width = declaration["type"].endswith("64")
    status = "normal" if same_width and rep in ("le", "be") and rep == helper_rep else "candidate" if same_width and rep in ("le", "be") else "insufficient"
    modes = [mode_src.cite(x.start(), x.end()) for x in re.finditer(r"\bHAL_SRNG_FLAGS_DATA_TLV_SWAP\b", mode_src.clean)]
    return dict(status=status, use_kind="bitfield_extract", direction="read",
                runtime_operation="evaluated_if_reached", object_binding=binding,
                format_carriers=[dict(kind="type_annotation", **declaration),
                                 dict(kind="helper_name", value=m.group(2), helper_implementation_proven=False)],
                representation_contract=rep,
                evidence=src.cite(f["body"] + m.start(), f["body"] + m.end()),
                result_variable=m.group(1), mask_name=m.group(3),
                local_switch_reference=bool(re.search(rf"\bswitch\s*\(\s*{re.escape(m.group(1))}\s*\)", segment[m.end():])),
                result_dataflow_proven=False, normal_scope="field_width_and_helper_name_only",
                hardware_mode=dict(symbol_evidence=modes, actual_selected_ring_flags="unknown",
                                   symbol_presence_proves_activation=False),
                runtime_fault_proven=False, check_proposal="establish external descriptor format and actual swap mode before judging the read")
