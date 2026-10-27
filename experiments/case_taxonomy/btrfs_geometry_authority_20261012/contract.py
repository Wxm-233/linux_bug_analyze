"""Finite lexical derivation and a conditional Python geometry model.

This is neither a C parser nor execution of a Btrfs function.  It recognizes
only the visible forms needed by the frozen candidate and declines ambiguity.
Expectations and case identifiers are deliberately absent from these APIs.
"""

import re


MACRO = "BTRFS_SETGET_STACK_FUNCS"
IDENTIFIER = r"[A-Za-z_]\w*"
UNKNOWN = {
    "actual_asm_unaligned_header_binding": "unknown",
    "actual_asm_byteorder_header_binding": "unknown",
    "underlying_le_to_cpu_definition_and_semantics": "unknown",
    "complete_CFG_and_dominance": "unknown",
    "external_call_side_effects_and_rewrites": "unknown",
    "all_path_initialization_and_object_identity": "unknown",
    "sget_actual_execution_chain": "unknown",
    "real_arch_preprocessing_and_compilation": "unknown",
    "actual_C_kernel_mount_execution": "not_performed",
}


class LimitedParseError(ValueError):
    """A source form is missing, ambiguous, or outside this finite recognizer."""


def _mask(source):
    """Mask comments/quoted literals while preserving offsets and newlines."""
    if not isinstance(source, str):
        raise LimitedParseError("source_must_be_text")
    output = list(source)
    i = 0
    while i < len(source):
        start = i
        if source.startswith("/*", i):
            stop = source.find("*/", i + 2)
            if stop < 0:
                raise LimitedParseError("unterminated_block_comment")
            i = stop + 2
        elif source.startswith("//", i):
            i = source.find("\n", i + 2)
            if i < 0:
                i = len(source)
        elif source[i] in ('"', "'"):
            quote = source[i]
            i += 1
            while i < len(source):
                if source[i] == "\\":
                    i += 2
                elif source[i] == quote:
                    i += 1
                    break
                elif source[i] in "\r\n":
                    raise LimitedParseError("newline_in_quoted_literal")
                else:
                    i += 1
            else:
                raise LimitedParseError("unterminated_quoted_literal")
        else:
            i += 1
            continue
        for position in range(start, min(i, len(source))):
            if source[position] not in "\r\n":
                output[position] = " "
    return "".join(output)


def _line(source, offset):
    return source.count("\n", 0, offset) + 1


def _balanced_end(source, opening):
    """Match a finite (), [], {} nest; malformed nests are insufficient."""
    pairs = {"(": ")", "[": "]", "{": "}"}
    if opening >= len(source) or source[opening] not in pairs:
        raise LimitedParseError("missing_opening_delimiter")
    stack = [pairs[source[opening]]]
    for position in range(opening + 1, len(source)):
        char = source[position]
        if char in pairs:
            stack.append(pairs[char])
        elif char in ")]}" and (not stack or char != stack.pop()):
            raise LimitedParseError("mismatched_delimiter")
        elif char in ")]}" and not stack:
            return position
    raise LimitedParseError("unterminated_delimiter")


def _one(items, reason):
    if len(items) != 1:
        raise LimitedParseError(reason)
    return items[0]


def _macro_definition(masked, name):
    starts = list(re.finditer(r"^[ \t]*#[ \t]*define[ \t]+" +
                              re.escape(name) + r"\b", masked, re.M))
    start = _one(starts, "macro_definition_not_unique").start()
    end = start
    while True:
        newline = masked.find("\n", end)
        if newline < 0:
            return start, masked[start:]
        physical_line = masked[end:newline].rstrip("\r \t")
        end = newline + 1
        if not physical_line.endswith("\\"):
            return start, masked[start:end]


def _macro_instances(masked, getter):
    instances = []
    pattern = re.compile(r"^[ \t]*" + MACRO + r"[ \t]*\(", re.M)
    for match in pattern.finditer(masked):
        opening = masked.find("(", match.start(), match.end())
        closing = _balanced_end(masked, opening)
        after = masked[closing + 1:]
        if not re.match(r"\s*;", after):
            raise LimitedParseError("unsupported_stack_macro_invocation")
        args = [re.sub(r"\s+", " ", part.strip())
                for part in masked[opening + 1:closing].split(",")]
        if len(args) != 4:
            raise LimitedParseError("unsupported_stack_macro_arguments")
        name, struct_type, member, bits = args
        if "btrfs_" + name != getter:
            continue
        if (not re.fullmatch(IDENTIFIER, name) or
                not re.fullmatch(r"struct " + IDENTIFIER, struct_type) or
                not re.fullmatch(IDENTIFIER, member) or
                bits not in ("16", "32", "64")):
            raise LimitedParseError("unsupported_target_macro_arguments")
        instances.append({"name": name, "type": struct_type,
                          "member": member, "bits": int(bits),
                          "offset": match.start()})
    return _one(instances, "getter_macro_instance_not_unique")


def _struct_field(masked, struct_type, member, expected_type):
    name = re.fullmatch(r"struct (" + IDENTIFIER + r")", struct_type)
    if not name:
        raise LimitedParseError("unsupported_struct_type")
    definitions = list(re.finditer(r"\bstruct\s+" + re.escape(name[1]) +
                                   r"\s*\{", masked))
    definition = _one(definitions, "struct_definition_not_unique")
    opening = masked.find("{", definition.start(), definition.end())
    closing = _balanced_end(masked, opening)
    body = masked[opening + 1:closing]
    # Only direct scalar member declarations are supported.  A target token
    # in any unsupported declaration (array, union, macro, etc.) declines.
    statements = []
    start = 0
    position = 0
    while position < len(body):
        if body[position] in "({[":
            position = _balanced_end(body, position) + 1
            continue
        if body[position] == ";":
            statements.append((start, body[start:position + 1]))
            start = position + 1
        position += 1
    mentions = [(offset, text) for offset, text in statements
                if re.search(r"\b" + re.escape(member) + r"\b", text)]
    offset, declaration = _one(mentions, "target_field_declaration_not_unique")
    match = re.fullmatch(r"\s*(" + re.escape(expected_type) + r")\s+(" +
                         re.escape(member) + r")\s*;\s*", declaration)
    if not match:
        raise LimitedParseError("target_field_type_or_shape_mismatch")
    return {"struct": struct_type, "member": member,
            "type": expected_type,
            "line": _line(masked, opening + 1 + offset + match.start(1)),
            "struct_definition_line": _line(masked, definition.start()),
            "struct_end_line": _line(masked, closing)}


def _function(masked, name):
    # This recognizes selected ordinary definitions, never calls/prototypes.
    definitions = []
    pattern = re.compile(r"^[ \t]*(?:static[ \t]+)?(?:inline[ \t]+)?"
                         r"(?P<return>u(?:16|32|64)|int|struct[ \t]+" +
                         IDENTIFIER + r"[ \t]*\*)[ \t]*" +
                         re.escape(name) + r"[ \t]*\(", re.M)
    for match in pattern.finditer(masked):
        opening = masked.find("(", match.start(), match.end())
        closing = _balanced_end(masked, opening)
        brace_match = re.match(r"\s*\{", masked[closing + 1:])
        if not brace_match:
            continue
        brace = closing + 1 + brace_match.end() - 1
        end = _balanced_end(masked, brace)
        definitions.append({"return_type": re.sub(r"\s+", " ", match["return"]),
                            "parameters": masked[opening + 1:closing],
                            "body": masked[brace + 1:end],
                            "offset": match.start(), "brace": brace,
                            "end": end})
    return _one(definitions, name + "_definition_not_unique")


def _binding_facts(header, setter, cache_type):
    retrieval = _function(header, "btrfs_sb")
    parameter = re.fullmatch(r"\s*struct\s+super_block\s*\*\s*(" +
                             IDENTIFIER + r")\s*", retrieval["parameters"])
    expected_return = cache_type + " *"
    return_type = re.sub(r"\s*\*\s*", " *", retrieval["return_type"])
    if not parameter or return_type != expected_return:
        raise LimitedParseError("unsupported_btrfs_sb_signature")
    read = re.fullmatch(r"\s*return\s+" + re.escape(parameter[1]) +
                        r"\s*->\s*(" + IDENTIFIER + r")\s*;\s*",
                        retrieval["body"])
    if not read:
        raise LimitedParseError("btrfs_sb_not_direct_member_return")
    member = read[1]
    write = _function(setter, "btrfs_set_super")
    parameters = re.fullmatch(r"\s*struct\s+super_block\s*\*\s*(" +
                              IDENTIFIER + r")\s*,\s*void\s*\*\s*(" +
                              IDENTIFIER + r")\s*", write["parameters"])
    if not parameters or write["return_type"] != "int":
        raise LimitedParseError("unsupported_btrfs_set_super_signature")
    sb, data = parameters.groups()
    # Require the complete visible success-conditional body, not just a hit
    # on s_fs_info.  This is still no proof of external callback execution.
    pattern = (r"\s*int\s+(" + IDENTIFIER + r")\s*=\s*set_anon_super\s*\(\s*" +
               re.escape(sb) + r"\s*,\s*" + re.escape(data) + r"\s*\)\s*;"
               r"\s*if\s*\(\s*!\s*\1\s*\)\s*" + re.escape(sb) +
               r"\s*->\s*" + re.escape(member) + r"\s*=\s*" +
               re.escape(data) + r"\s*;\s*return\s+\1\s*;\s*")
    store = re.fullmatch(pattern, write["body"])
    if not store:
        raise LimitedParseError("setter_success_conditional_form_not_matched")
    # Match expression offsets separately so evidence points to the tokens.
    retrieval_token = re.search(r"\breturn\b", retrieval["body"]).start()
    assignment_token = re.search(re.escape(sb) + r"\s*->\s*" +
                                 re.escape(member), write["body"]).start()
    return {
        "status": "visible_local_binding_facts",
        "read": {"function": "btrfs_sb", "member": member,
                 "return_type": expected_return,
                 "definition_line": _line(header, retrieval["offset"]),
                 "line": _line(header, retrieval["brace"] + 1 + retrieval_token),
                 "expression": "return " + parameter[1] + "->" + member + ";"},
        "write": {"function": "btrfs_set_super", "member": member,
                  "definition_line": _line(setter, write["offset"]),
                  "line": _line(setter, write["brace"] + 1 + assignment_token),
                  "expression": sb + "->" + member + " = " + data,
                  "condition": "!" + store[1] + " after set_anon_super(" +
                               sb + ", " + data + ")",
                  "success_conditional_assignment": True,
                  "all_path_identity_proven": False},
        "modeled_object_link_automatically_established": False,
        "sget_actual_execution_chain": "unknown",
    }


def derive_template(header, generic, setter_source, candidate):
    """Associate the saved candidate with visible types and reference helper.

    The generated equality is a conditional model property.  Actual asm header
    selection, byteorder expansion, C compilation and complete object identity
    remain unknown even when this finite recognizer returns a template.
    """
    result = {"status": "insufficient", "template": None, "facts": {},
              "unknown": dict(UNKNOWN),
              "interpretation": "Finite visible-source association; conditional Python model only."}
    try:
        if not isinstance(candidate, dict):
            raise LimitedParseError("candidate_must_be_a_saved_record")
        field = candidate.get("field")
        call = candidate.get("source_call")
        getter = call.get("name") if isinstance(call, dict) else None
        pointer = candidate.get("struct_pointer_type")
        if (not isinstance(field, str) or not re.fullmatch(IDENTIFIER, field) or
                not isinstance(getter, str) or not re.fullmatch(IDENTIFIER, getter) or
                not isinstance(pointer, str)):
            raise LimitedParseError("candidate_missing_field_getter_or_pointer_type")
        pointer_match = re.fullmatch(r"\s*(struct\s+" + IDENTIFIER + r")\s*\*\s*", pointer)
        if not pointer_match:
            raise LimitedParseError("unsupported_candidate_pointer_type")
        cache_type = re.sub(r"\s+", " ", pointer_match[1])
        header_masked, generic_masked, setter_masked = map(_mask, (header, generic, setter_source))
        instance = _macro_instances(header_masked, getter)
        bits = instance["bits"]
        if instance["member"] != field:
            raise LimitedParseError("getter_member_and_cache_field_not_same_name")
        macro_offset, macro_definition = _macro_definition(header_masked, MACRO)
        compact_macro = re.sub(r"\\\r?\n", " ", macro_definition)
        macro_form = (r"\s*#\s*define\s+" + MACRO +
                      r"\(\s*name\s*,\s*type\s*,\s*member\s*,\s*bits\s*\)"
                      r"\s*static\s+inline\s+u\s*##\s*bits\s+btrfs_\s*##\s*name"
                      r"\s*\(\s*const\s+type\s*\*\s*s\s*\)\s*\{"
                      r"\s*return\s+get_unaligned_le\s*##\s*bits\s*\(\s*&\s*s\s*->\s*member\s*\)\s*;\s*\}"
                      r"\s*static\s+inline\s+void\s+btrfs_set_\s*##\s*name"
                      r"\s*\(\s*type\s*\*\s*s\s*,\s*u\s*##\s*bits\s+val\s*\)\s*\{"
                      r"\s*put_unaligned_le\s*##\s*bits\s*\(\s*val\s*,\s*&\s*s\s*->\s*member\s*\)\s*;\s*\}\s*")
        if not re.fullmatch(macro_form, compact_macro):
            raise LimitedParseError("stack_getter_macro_visible_form_not_matched")
        wire_type, cached_type = "__le" + str(bits), "u" + str(bits)
        wire_field = _struct_field(header_masked, instance["type"], field, wire_type)
        cache_field = _struct_field(header_masked, cache_type, field, cached_type)
        helper_name = "get_unaligned_le" + str(bits)
        helper = _function(generic_masked, helper_name)
        parameter = re.fullmatch(r"\s*const\s+void\s*\*\s*(" +
                                 IDENTIFIER + r")\s*", helper["parameters"])
        if not parameter or helper["return_type"] != cached_type:
            raise LimitedParseError("reference_helper_signature_mismatch")
        conversion = "le" + str(bits) + "_to_cpu"
        helper_form = (r"\s*return\s+" + conversion +
                       r"\s*\(\s*__get_unaligned_t\s*\(\s*" + wire_type +
                       r"\s*,\s*" + re.escape(parameter[1]) + r"\s*\)\s*\)\s*;\s*")
        if not re.fullmatch(helper_form, helper["body"]):
            raise LimitedParseError("reference_helper_visible_conversion_mismatch")
        packed_offset, packed_macro = _macro_definition(generic_masked, "__get_unaligned_t")
        packed_compact = re.sub(r"\\\r?\n", " ", packed_macro)
        packed_form = (r"\s*#\s*define\s+__get_unaligned_t\(\s*type\s*,\s*ptr\s*\)"
                       r"\s*\(\s*\{\s*const\s+struct\s*\{\s*type\s+x\s*;\s*\}"
                       r"\s*__packed\s*\*\s*__pptr\s*=\s*\(\s*typeof\s*\(\s*__pptr\s*\)\s*\)"
                       r"\s*\(\s*ptr\s*\)\s*;\s*__pptr\s*->\s*x\s*;\s*\}\s*\)\s*")
        if not re.fullmatch(packed_form, packed_compact):
            raise LimitedParseError("packed_reference_load_visible_form_not_matched")
        bindings = _binding_facts(header_masked, setter_masked, cache_type)
        include_unaligned = re.search(r"^[ \t]*#[ \t]*include[ \t]*<asm/unaligned\.h>", header_masked, re.M)
        include_byteorder = re.search(r"^[ \t]*#[ \t]*include[ \t]*<asm/byteorder\.h>", generic_masked, re.M)
        result["facts"] = {
            "candidate_origin": "saved previous-stage record; no C caller re-extraction",
            "candidate": candidate,
            "wire_field": wire_field, "cache_field": cache_field,
            "getter_instance": {key: value for key, value in instance.items() if key != "offset"},
            "getter_instance_line": _line(header_masked, instance["offset"]),
            "getter_macro": {"name": MACRO, "definition_line": _line(header_masked, macro_offset),
                             "visible_return": "get_unaligned_le##bits(&s->member)"},
            "reference_helper": {"name": helper_name,
                                 "definition_line": _line(generic_masked, helper["offset"]),
                                 "visible_return": conversion + "(__get_unaligned_t(" + wire_type + ", " + parameter[1] + "))",
                                 "actual_arch_binding": "unknown"},
            "reference_packed_load": {"macro": "__get_unaligned_t",
                                      "definition_line": _line(generic_masked, packed_offset),
                                      "visible_packed_member_access": "const struct { type x; } __packed *__pptr; __pptr->x",
                                      "native_load_or_arch_semantics_proven": False},
            "visible_include_directives": {
                "asm/unaligned.h": _line(header_masked, include_unaligned.start()) if include_unaligned else None,
                "asm/byteorder.h": _line(generic_masked, include_byteorder.start()) if include_byteorder else None},
            "object_binding": bindings,
        }
        result["status"] = "conditional_template"
        result["template"] = {
            "kind": "conditional_geometry_equality", "bits": bits,
            "wire_type": wire_type, "cached_type": cached_type,
            "wire_field": instance["type"] + "." + field,
            "cache_field": cache_type + "." + field,
            "getter": getter, "reference_helper": helper_name,
            "expression": "cache_field == decode_le" + str(bits) + "(wire_field_bytes)",
            "enabled_only_if": ["target_consumed", "validated_geometry_available", "modeled_object_link"],
            "object_link_source": "manual model input, not inferred from local binding facts",
            "behavior_projection": ["min(requested, cached)", "min(requested, decoded)"],
            "real_kernel_assertion": False,
        }
    except LimitedParseError as exc:
        result["reason"] = str(exc)
    return result


def evaluate_model(template, inputs):
    """Evaluate only template and model inputs, never expected values or ids.

    Non-consumption takes precedence over missing preparation or malformed
    bytes.  A cache property mismatch can coexist with equal clamp outputs.
    """
    empty = {"decoded": None, "observed_clamp": None, "expected_clamp": None,
             "cache_mismatch": None, "behavior_difference": None}
    if not isinstance(inputs, dict):
        return {"status": "insufficient", **empty}
    if inputs.get("target_consumed") is False:
        return {"status": "not_consumed", **empty}
    if (inputs.get("target_consumed") is not True or
            inputs.get("validated_geometry_available") is not True or
            inputs.get("modeled_object_link") is not True or
            not isinstance(template, dict) or
            template.get("kind") != "conditional_geometry_equality" or
            type(template.get("bits")) is not int or
            template.get("bits") not in (16, 32, 64)):
        return {"status": "insufficient", **empty}
    bits = template["bits"]
    if (template.get("wire_type") != "__le" + str(bits) or
            template.get("cached_type") != "u" + str(bits) or
            not template.get("wire_field") or not template.get("cache_field")):
        return {"status": "insufficient", **empty}
    wire = inputs.get("wire_hex")
    cached, requested = inputs.get("cached"), inputs.get("requested")
    if (not isinstance(wire, str) or
            not re.fullmatch(r"[0-9a-fA-F]{" + str(bits // 4) + r"}", wire) or
            type(cached) is not int or not 0 <= cached < (1 << bits) or
            type(requested) is not int or requested < 0):
        return {"status": "insufficient", **empty}
    field_bytes = bytes.fromhex(wire)
    if len(field_bytes) != bits // 8:
        return {"status": "insufficient", **empty}
    decoded = int.from_bytes(field_bytes, "little", signed=False)
    observed_clamp, expected_clamp = min(requested, cached), min(requested, decoded)
    mismatch = cached != decoded
    return {"status": "model_mismatch" if mismatch else "model_match",
            "decoded": decoded, "observed_clamp": observed_clamp,
            "expected_clamp": expected_clamp, "cache_mismatch": mismatch,
            "behavior_difference": observed_clamp != expected_clamp}
