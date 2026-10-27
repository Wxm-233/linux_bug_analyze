"""Finite source-shape checks for encoded scalars used as host byte counts.

The caller chooses one function and supplies saved, same-revision declarations.
This is neither C preprocessing nor a proof of value flow, length completeness,
include resolution, object validity or a runtime fault.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import sys

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
_spec = importlib.util.spec_from_file_location(
    "encoded_length_fixed_interface_facts",
    BASE / "interface_facts_20261008/interface_fact_extractor.py",
)
old = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = old
_spec.loader.exec_module(old)
Source = old.Source

ID = r"[A-Za-z_]\w*"
INTEGER = r"(?:unsigned\s+int|unsigned|int|[us](?:8|16|32|64))"
ACCESS = rf"(?P<object>{ID})\s*->\s*(?P<member>{ID})"
DECODERS = tuple(f"{order}{bits}_to_cpu" for order in ("le", "be") for bits in (16, 32, 64))
APIS = ("memcpy", "memmove", "skb_put", "skb_tailroom")
LENGTH_ARGS = {"memcpy": (3, 2), "memmove": (3, 2), "skb_put": (2, 1)}


def limits():
    return dict(
        function_selection="caller",
        normal_scope="local_assignment_representation_shape",
        whole_function_certified=False,
        length_contract_certified=False,
        runtime_value_proven=False,
        control_flow_certified=False,
        pointer_origin_certified=False,
        actual_path="unknown",
        full_preprocessing_certified=False,
        actual_include_binding_certified=False,
        external_format_authority_certified=False,
        value_range_certified=False,
    )


def _word(name, text):
    # A member base (p->length or p.length) is not a use of integer local p.
    return bool(re.search(rf"(?<![\w.>]){re.escape(name)}\b(?!\s*(?:->|\.))", text))


def _top_ops(text, operators):
    depth, found, index = 0, [], 0
    while index < len(text):
        if text.startswith("->", index):
            index += 2
            continue
        character = text[index]
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth < 0:
                raise ValueError("unbalanced expression")
        elif depth == 0:
            op = next((op for op in operators if text.startswith(op, index)), None)
            if op:
                found.append((index, op))
                index += len(op)
                continue
        index += 1
    if depth:
        raise ValueError("unbalanced expression")
    return found


def _literal(text):
    text = old.unwrap(text)
    if not re.fullmatch(r"(?:0[xX][0-9a-fA-F]+|0|[1-9][0-9]*)(?:[uUlL]+)?", text):
        raise ValueError("not a nonnegative literal")
    text = re.sub(r"[uUlL]+$", "", text)
    value = int(text, 16 if text.lower().startswith("0x") else 10)
    if value >= 2**64:
        raise ValueError("literal outside bounded range")
    return value


def _constant(src, expression, assignment_site):
    expression = old.unwrap(expression)
    try:
        return dict(kind="nonnegative_literal", expression=expression,
                    value=_literal(expression), evidence=[])
    except ValueError:
        pass
    if not re.fullmatch(ID, expression):
        raise ValueError("offset outside literal/simple object-macro grammar")
    escaped = re.escape(expression)
    if re.search(rf"(?m)^\s*#\s*undef\s+{escaped}\b", src.clean):
        raise ValueError("offset macro undefined/rebound")
    definitions = list(re.finditer(
        rf"(?m)^[ \t]*#\s*define\s+{escaped}\b(?P<after>[^\n]*)", src.clean))
    if len(definitions) != 1:
        raise ValueError("offset macro absent or multiply defined")
    definition = definitions[0]
    if definition.end() > assignment_site:
        raise ValueError("offset macro definition is not visible before assignment")
    after = definition.group("after")
    if not after or not after[0].isspace():
        raise ValueError("function-like offset macro unsupported")
    conditional_depth = 0
    for directive in re.finditer(r"(?m)^\s*#\s*(if|ifdef|ifndef|endif)\b", src.clean[:definition.start()]):
        conditional_depth += -1 if directive.group(1) == "endif" else 1
    if conditional_depth:
        raise ValueError("conditional offset macro not certified")
    return dict(kind="simple_object_macro", expression=expression,
                value=_literal(after.strip()), evidence=[src.cite(definition.start(), definition.end())],
                full_preprocessing_certified=False)


def _shadow(src, f, names):
    type_names = tuple(f"{sign}{width}" for sign in ("u", "s") for width in (8, 16, 32, 64))
    if old.macro_override(src, [*names, "int", "unsigned", *type_names]):
        return "local macro define/undef overrides object, type, helper or consumer"
    body = src.clean[f["body"]:f["end"]]
    type_pattern = "|".join(type_names)
    if re.search(rf"\btypedef\b[^;]*\b(?:{type_pattern})\s*;", src.clean):
        return "saved fixed-width local-type typedef override not certified"
    for match in re.finditer(rf"\b({ID})\s+\**\s*({type_pattern})\b", f["params"]+";"+body):
        if match.group(1) not in ("return", "sizeof", "case", "struct"):
            return "ordinary name may shadow a fixed-width integer type"
    for name in names:
        if re.search(rf"\b{re.escape(name)}\b", f["params"]) and name in (*APIS, *DECODERS):
            return "helper/consumer name occurs in parameters"
        if name in (*APIS, *DECODERS):
            if re.search(rf"\(\s*\*\s*{re.escape(name)}\b", src.clean):
                return "helper/consumer function-pointer shadow"
            for match in re.finditer(rf"\b({ID})\s+\**\s*{re.escape(name)}\b", body):
                if match.group(1) not in ("return", "case"):
                    return "helper/consumer local declaration shadow"
            # Saved custom declarations are not certified implementations of APIs.
            for match in re.finditer(rf"(?m)^[ \t]*([A-Za-z_][\w \t*]*)\b{re.escape(name)}\s*\(", src.clean):
                prefix = match.group(1).strip()
                if prefix.startswith(("return", "if", "while", "for")):
                    continue
                end = old.closing_delimiter(src.clean, match.end()-1, "(", ")")
                if end is not None and src.clean[end+1:].lstrip().startswith(("{", ";")):
                    return "saved helper/consumer declaration or definition not certified"
    return None


def _consumers(src, f):
    result = []
    for api, (arity, index) in LENGTH_ARGS.items():
        for call in old.calls(src, f["body"], f["end"], api):
            expression = call["args"][index] if len(call["args"]) == arity else None
            result.append(dict(api=api, role=f"argument_{index+1}_host_byte_count",
                               begin=call["begin"], end=call["end"], length_expression=expression,
                               supported_argument_count=len(call["args"]) == arity,
                               evidence=call["evidence"], lexical_only=True,
                               runtime_execution_certified=False))
    for call in old.calls(src, f["body"], f["end"], "if"):
        if len(call["args"]) != 1 or not re.search(r"\bskb_tailroom\s*\(", call["args"][0]):
            continue
        expression = old.unwrap(call["args"][0])
        comparisons = _top_ops(expression, ("!=", "==", "<=", ">=", "<", ">"))
        length = None
        if len(comparisons) == 1:
            offset, operator = comparisons[0]
            left, right = expression[:offset].strip(), expression[offset+len(operator):].strip()
            if old.exact_call(left, "skb_tailroom"):
                length = right
            elif old.exact_call(right, "skb_tailroom"):
                length = left
        room_calls = old.calls(src, call["begin"], call["end"], "skb_tailroom")
        valid_arity = len(room_calls) == 1 and len(room_calls[0]["args"]) == 1
        result.append(dict(api="skb_tailroom", role="comparison_to_host_byte_count",
                           begin=call["begin"], end=call["end"], length_expression=length,
                           supported_argument_count=length is not None and valid_arity,
                           observed_tailroom_argument_counts=[len(item["args"]) for item in room_calls],
                           evidence=call["evidence"], lexical_only=True,
                           runtime_execution_certified=False))
    return sorted(result, key=lambda item: (item["begin"], item["api"]))


def _local_declaration(src, f, name):
    body = src.clean[f["body"]:f["end"]]
    if re.search(rf"\b{re.escape(name)}\b", f["params"]):
        raise ValueError("length local is a parameter or shadows parameter")
    declarations = []
    for match in re.finditer(rf"(?:\A|(?<=[;{{}}]))\s*(?P<type>{INTEGER})\s+(?P<entries>[^;{{}}]+);", body):
        if not _word(name, match.group("entries")):
            continue
        entry = re.fullmatch(rf"{re.escape(name)}(?:\s*=\s*(?P<init>.*))?", match.group("entries").strip(), re.S)
        if entry is None:
            raise ValueError("multiple/array/pointer/complex integer declarator")
        declarations.append(dict(type=match.group("type"),
                                 begin=f["body"]+match.start(), end=f["body"]+match.end(),
                                 initializer=entry.group("init")))
    if len(declarations) != 1:
        raise ValueError("unique plain integer local declaration unavailable")
    chosen = declarations[0]
    for match in re.finditer(rf"\b({ID})\s+\**\s*{re.escape(name)}\s*(?=[;,=\[])" , body):
        if match.group(1) not in (*chosen["type"].split(), "return"):
            raise ValueError("opaque or different-type local shadow")
    if re.search(rf"(?<!&)\&\s*{re.escape(name)}\b", body):
        raise ValueError("local address/unsupported ampersand reference")
    if re.search(rf"(?:\+\+|--)\s*{re.escape(name)}\b|\b{re.escape(name)}\s*(?:\+\+|--)", body):
        raise ValueError("local increment/decrement unsupported")
    return chosen


def _field(src, f, declarations, expression, consumer_calls):
    access = re.fullmatch(ACCESS, old.unwrap(expression))
    if access is None:
        raise ValueError("source is not one direct scalar field")
    obj, member = access.group("object"), access.group("member")
    pointers = list(re.finditer(rf"\bstruct\s+({ID})\s*\*\s*{re.escape(obj)}\b", f["params"]))
    if len(pointers) != 1:
        raise ValueError("only unique direct structure-pointer parameter supported")
    structure = pointers[0].group(1)
    binding = old.bind_object(src, f, obj, structure)
    body = src.clean[f["body"]:f["end"]]
    if re.search(rf"(?<![\w.>]){re.escape(obj)}\s*(?:=(?!=)|\+=|-=|\+\+|--)", body):
        raise ValueError("structure pointer rebound/modified")
    if re.search(rf"(?<!&)\&\s*{re.escape(obj)}\b", body):
        raise ValueError("structure pointer/field address escape unsupported")
    # A bare pointer may only be read as a conventional known API argument.
    allowed = [(call["begin"], call["end"]) for call in consumer_calls]
    for match in re.finditer(rf"(?<![\w.>]){re.escape(obj)}\b", body):
        position = f["body"]+match.start()
        tail = body[match.end():]
        if re.match(r"\s*->", tail):
            continue
        if not any(begin <= position < end for begin, end in allowed):
            raise ValueError("bare structure pointer alias/escape or unknown call use")
    found = []
    for declaration_source in declarations:
        try:
            declaration = old.field(declaration_source, structure, member)
        except ValueError as error:
            if re.search(rf"\bstruct\s+{re.escape(structure)}\s*\{{", declaration_source.clean):
                raise ValueError("visible structure definition has unsupported/conflicting field: "+str(error))
            continue
        found.append((declaration_source, declaration))
    if len(found) != 1:
        raise ValueError("same-revision encoded field declaration absent/ambiguous")
    declaration_source, declaration = found[0]
    encoded = re.fullmatch(r"__(le|be)(16|32|64)", declaration["type"])
    if encoded is None:
        raise ValueError("field is not a direct annotated encoded scalar")
    names = [obj, member, structure, declaration["type"], *DECODERS, *APIS]
    if old.macro_override(src, names) or old.macro_override(declaration_source, names):
        raise ValueError("field/object/type/helper/consumer macro override")
    if any(re.search(rf"\btypedef\b[^;]*\b{re.escape(declaration['type'])}\s*;", item.clean)
           for item in (src, declaration_source)):
        raise ValueError("saved encoded-type typedef override not certified")
    return dict(object=obj, structure=structure, field=member, type=declaration["type"],
                domain=encoded.group(1), width=int(encoded.group(2)),
                evidence=[declaration["evidence"], binding], pointer_origin_certified=False)


def _source_expression(src, f, declarations, expression, consumer_calls, assignment_site):
    expression = old.unwrap(expression)
    plus = _top_ops(expression, ("+",))
    if len(plus) > 1:
        raise ValueError("only one nonnegative additive component supported")
    components = []
    base = expression
    if plus:
        offset, _ = plus[0]
        base, component = expression[:offset].strip(), expression[offset+1:].strip()
        components.append(_constant(src, component, assignment_site))
    base = old.unwrap(base)
    decode = re.fullmatch(r"(le|be)(16|32|64)_to_cpu\s*\((.*)\)", base, re.S)
    raw = decode.group(3) if decode else base
    field = _field(src, f, declarations, raw, consumer_calls)
    if decode and (decode.group(1) != field["domain"] or int(decode.group(2)) != field["width"]):
        raise ValueError("decode direction/width does not match source field")
    return dict(source_field=field, representation="host" if decode else "encoded_"+field["domain"],
                conversion=decode.group(0).split("(")[0].strip() if decode else None,
                length_components=components, arithmetic_shape="field_plus_component" if plus else "field_only",
                conversion_implementation_certified=False, length_contract_certified=False)


def _preconsumer_uses(src, name, assignment_end, first_consumer_begin):
    """Refuse unknown call/macro use before the first lexical count consumer."""
    keywords = ("if", "while", "for", "switch", "sizeof", "return")
    segment = src.clean[assignment_end:first_consumer_begin]
    for match in re.finditer(rf"\b({ID})\s*\(", segment):
        callee = match.group(1)
        opening = assignment_end+match.end()-1
        closing = old.closing_delimiter(src.clean, opening, "(", ")")
        if closing is None:
            raise ValueError("unbalanced call before consumer")
        args = src.clean[opening+1:closing]
        if not _word(name, args):
            continue
        if old.macro_override(src, [callee]):
            raise ValueError("visible macro uses local before consumer")
        if callee in keywords:
            continue
        if callee in DECODERS:
            calls = old.calls(src, assignment_end+match.start(), closing+1, callee)
            if len(calls) == 1 and len(calls[0]["args"]) == 1:
                continue
        raise ValueError("unknown call/macro uses local before first lexical consumer")


def inspect_function(src, function_name, declaration_sources=None):
    """Enumerate the fixed assignment/consumer subset, with no patch or target hint."""
    result = dict(function=function_name, execution_status="ok", assignments=[],
                  assignment_syntax_sites=[], consumer_sites=[], **limits())
    try:
        supplied = declaration_sources if declaration_sources is not None else [src]
        if not supplied or any(item.revision != src.revision for item in supplied):
            raise ValueError("declaration inputs absent or mixed revisions")
        # The caller cannot hide a current-C conflicting declaration by passing
        # only headers. Identical saved-source duplicates are not extra evidence.
        declarations, seen = [], {}
        for item in (src, *supplied):
            key = (item.saved_path, item.revision)
            if key in seen:
                previous = seen[key]
                if item.raw != previous.raw or item.path != previous.path or item.blob != previous.blob:
                    raise ValueError("conflicting duplicate saved declaration source")
                continue
            seen[key] = item
            declarations.append(item)
        f = old.function(src, function_name)
        consumers = _consumers(src, f)
        result["consumer_sites"] = consumers
        body = src.clean[f["body"]:f["end"]]
        pattern = rf"(?<![\w.>])(?P<name>{ID})\s*(?P<op>=(?!=)|\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>=)\s*(?P<rhs>[^;{{}}]*);"
        writes = []
        for match in re.finditer(pattern, body):
            writes.append(dict(variable=match.group("name"), operator=match.group("op"),
                               rhs=match.group("rhs").strip(), begin=f["body"]+match.start(),
                               end=f["body"]+match.end()))
        result["assignment_syntax_sites"] = [dict(**write, evidence=src.cite(write["begin"], write["end"])) for write in writes]
        for write in writes:
            name = write["variable"]
            associated = [call for call in consumers if call["length_expression"] is not None and _word(name, call["length_expression"])]
            if not associated:
                continue
            record = dict(variable=name, rhs=write["rhs"], operator=write["operator"],
                          status="insufficient", reason="unsupported assignment",
                          evidence=[src.cite(write["begin"], write["end"])], consumers=associated,
                          first_lexical_consumer=associated[0],
                          first_consumer_scope="first visible lexical consumer; no CFG execution-order proof",
                          length_components=[], **limits())
            try:
                declaration = _local_declaration(src, f, name)
                record["local_declaration"] = dict(type=declaration["type"], evidence=src.cite(declaration["begin"], declaration["end"]))
                same_name = [item for item in writes if item["variable"] == name]
                if len(same_name) != 1 or write["operator"] != "=":
                    raise ValueError("local has multiple/compound writes")
                prefix = src.clean[f["body"]:write["begin"]]
                if prefix.count("{") != prefix.count("}"):
                    raise ValueError("conditional/nested-block assignment unsupported")
                if re.search(r"\b(?:goto|switch|case|for|while)\b|\w+\s*:(?!:)", prefix):
                    raise ValueError("preceding jump/loop context unsupported")
                tail = re.split(r"[;{}]", prefix)[-1].strip()
                if declaration["initializer"] is None and tail:
                    raise ValueError("conditional or non-direct assignment prefix")
                if declaration["initializer"] is not None and tail != declaration["type"]:
                    raise ValueError("non-plain declaration initializer")
                reason = _shadow(src, f, [name, declaration["type"], *DECODERS, *APIS])
                if reason:
                    raise ValueError(reason)
                for call in associated:
                    if old.unwrap(call["length_expression"]) != name or not call["supported_argument_count"]:
                        raise ValueError("consumer length is not the direct local value")
                    if call["begin"] < write["end"]:
                        raise ValueError("consumer precedes assignment lexically")
                _preconsumer_uses(src, name, write["end"], associated[0]["begin"])
                source = _source_expression(src, f, declarations, write["rhs"], consumers, write["begin"])
                record.update(source)
                record["status"] = "normal" if source["representation"] == "host" else "candidate"
                record["reason"] = ("matched decode before local host-byte-count shape" if record["status"] == "normal"
                                    else "undecoded encoded field enters local host-byte-count shape")
                record["candidate_condition"] = "actual byte-order-sensitive value, compatible declarations and runtime reachability remain unproved"
                record["check_proposal"] = "normalize representation before the first visible host-byte-count consumer; determine complete length contract separately"
            except (ValueError, SyntaxError) as error:
                record["reason"] = str(error)
            result["assignments"].append(record)
        result["enumerated_assignment_syntax_sites"] = len(writes)
        result["enumerated_length_assignments"] = len(result["assignments"])
        result["enumerated_consumer_sites"] = len(consumers)
    except (ValueError, SyntaxError) as error:
        result.update(execution_status="insufficient", reason=str(error))
    return result
