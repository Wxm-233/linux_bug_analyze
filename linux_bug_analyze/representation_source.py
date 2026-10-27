"""Extract a bounded scalar representation predicate from unpreprocessed C.

The caller selects one local expression, its unique simple ``ptr->field`` and
one externally reviewed scalar member declaration. This module does not bind
that declaration to the object, expand macros or establish effective compiler
types. Integer macro values and conversion semantics are external inputs.
Unsupported syntax remains insufficient; pycparser has no regex fallback.
"""

from __future__ import annotations

import re
from typing import Any

try:
    from pycparser import c_ast, c_parser
except ImportError:  # Optional research dependency, never substitute a parser.
    c_ast = c_parser = None


_IDENTIFIER = r"[A-Za-z_][A-Za-z0-9_]*"
_FIELD = re.compile(rf"\s*({_IDENTIFIER})\s*->\s*({_IDENTIFIER})\s*\Z")
_INTEGER = re.compile(
    r"(0[xX][0-9a-fA-F]+|0[0-7]*|[1-9][0-9]*)"
    r"((?:[uU](?:(?:ll|LL)|[lL])?|(?:(?:ll|LL)|[lL])[uU]?)?)\Z"
)
_TYPE_STUBS = "\n".join(
    f"typedef unsigned int __{endian}{width};"
    for endian in ("le", "be") for width in (16, 32, 64)
)


class _Unsupported(ValueError):
    def __init__(self, reason: str, detail: str):
        super().__init__(detail)
        self.reason = reason


def _reject(reason: str, detail: str) -> None:
    raise _Unsupported(reason, detail)


def _clean(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        _reject("invalid_text", "nonempty source text is required")
    if "\x00" in text or "??" in text or "\\\n" in text or "\\\r\n" in text:
        _reject("unsupported_translation_syntax", "NUL, trigraphs and line splicing are unsupported")
    tokens = r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''

    def replace(match):
        token = match[0]
        if token.startswith(("/*", "//")):
            return "".join("\n" if char == "\n" else " " for char in token)
        return token

    clean = re.sub(tokens, replace, text, flags=re.S)
    if "#" in clean:
        _reject("unsupported_preprocessor", "preprocessor directives are not expanded")
    return clean


def _declaration(text: str, expected_name: str) -> tuple[str, int, str]:
    ast = c_parser.CParser().parse(_TYPE_STUBS + "\n" + _clean(text))
    if len(ast.ext) != 7 or not isinstance(ast.ext[-1], c_ast.Decl):
        _reject("unsupported_declaration", "exactly one complete scalar member declaration is required")
    decl = ast.ext[-1]
    if (not isinstance(decl.type, c_ast.TypeDecl) or decl.init is not None
            or decl.bitsize is not None or decl.storage or decl.funcspec):
        _reject("unsupported_declaration", "arrays, pointers, bitfields, storage and initializers are unsupported")
    if not (set(decl.quals or []) | set(decl.type.quals or [])) <= {"const"}:
        _reject("unsupported_declaration_qualifier", "only the optional const qualifier is supported")
    if decl.name != expected_name:
        _reject("declaration_name_mismatch", "reviewed declaration name does not match field_ref")
    base = decl.type.type
    if not isinstance(base, c_ast.IdentifierType) or len(base.names) != 1:
        _reject("unsupported_scalar_type", "an explicit encoded scalar type is required")
    match = re.fullmatch(r"__(le|be)(16|32|64)", base.names[0])
    if not match:
        _reject("unsupported_scalar_type", "only __le/__be16/32/64 declarations are supported")
    return base.names[0], int(match[2]), {"le": "little", "be": "big"}[match[1]]


def _expression(text: str):
    ast = c_parser.CParser().parse("void __representation_probe(void) { if (" + _clean(text) + ") ; }")
    if len(ast.ext) != 1 or not isinstance(ast.ext[0], c_ast.FuncDef):
        _reject("unsupported_expression", "exactly one expression is required")
    items = ast.ext[0].body.block_items or []
    if (len(items) != 1 or not isinstance(items[0], c_ast.If)
            or not isinstance(items[0].iftrue, c_ast.EmptyStatement)
            or items[0].iffalse is not None):
        _reject("unsupported_expression", "additional statements are unsupported")
    return items[0].cond


def _literal(node) -> int:
    if not isinstance(node, c_ast.Constant) or node.type not in {
        "int", "unsigned int", "long int", "unsigned long int", "long long int", "unsigned long long int"
    }:
        _reject("unsupported_integer", "a plain nonnegative C integer literal is required")
    match = _INTEGER.fullmatch(node.value)
    if not match:
        _reject("unsupported_integer", "unsupported integer spelling or suffix")
    digits = match[1]
    return int(digits, 16 if digits.lower().startswith("0x") else 8 if digits.startswith("0") else 10)


def extract_representation_predicate(
    expression: str, *, field_ref: str, declaration: str,
    constants: dict[str, int], conversion_registry: dict,
) -> dict[str, Any]:
    """Extract a pure local predicate; never certify declaration/config binding.

    Supported operations are direct truth/``!= 0``/``== 0`` and a direct masked
    nonzero test. Field conversions must be registered ``to_host``; mask
    conversions must be registered ``to_storage``. Mask expressions contain only
    integer literals, externally supplied integer constant names and bitwise OR.
    No host endian or defect/normal label is accepted or inferred.
    """
    facts: dict[str, Any] = {
        "expression": expression, "field_ref": field_ref, "declaration": declaration,
        "declaration_binding": "external_review_required",
        "effective_typedef_and_conversion_semantics": "external_inputs_not_proved",
        "host_endian": "not_inferred", "conversion_calls": [], "constant_terms": [],
    }
    result = {"status": "insufficient", "reason": None, "syntax_facts": facts, "spec_partial": None}
    try:
        if c_parser is None:
            _reject("pycparser_unavailable", "install the optional research dependency; no fallback is used")
        if not isinstance(field_ref, str) or not (match := _FIELD.fullmatch(field_ref)):
            _reject("unsupported_field_ref", "only a simple identifier->identifier field_ref is supported")
        object_name, field_name = match.groups()
        if not isinstance(constants, dict) or any(
            not isinstance(name, str) or not re.fullmatch(_IDENTIFIER, name)
            or type(value) is not int or value < 0 for name, value in constants.items()
        ):
            _reject("invalid_constants", "constant names require external nonnegative integer values, not bools")
        if not isinstance(conversion_registry, dict):
            _reject("invalid_conversion_registry", "an explicit conversion registry is required")
        declared_type, width, storage_endian = _declaration(declaration, field_name)
        facts.update(declared_type=declared_type, width=width, storage_endian=storage_endian,
                     normalized_field_ref=object_name + "->" + field_name)
        node = _expression(expression)

        def is_target(value):
            return (isinstance(value, c_ast.StructRef) and value.type == "->"
                    and isinstance(value.name, c_ast.ID) and value.name.name == object_name
                    and isinstance(value.field, c_ast.ID) and value.field.name == field_name)

        def target_count(value):
            return int(is_target(value)) + sum(target_count(child) for _, child in value.children())

        count = target_count(node)
        facts["target_occurrences"] = count
        if count != 1:
            _reject("target_not_unique", "the complete selected expression must contain exactly one target field")

        def conversion(value, direction):
            if not isinstance(value, c_ast.FuncCall) or not isinstance(value.name, c_ast.ID):
                _reject("unsupported_conversion", "only a directly registered function-shaped conversion is supported")
            name = value.name.name
            entry = conversion_registry.get(name)
            if not isinstance(entry, dict):
                _reject("unregistered_conversion", "conversion semantics cannot be inferred from its spelling")
            if (entry.get("direction") != direction or type(entry.get("width")) is not int
                    or entry.get("width") != width or entry.get("storage_endian") != storage_endian):
                _reject("conversion_domain_mismatch", "registered direction, width and storage endian must match")
            if not isinstance(value.args, c_ast.ExprList) or len(value.args.exprs) != 1:
                _reject("unsupported_conversion_arguments", "exactly one pure conversion argument is required")
            facts["conversion_calls"].append({"name": name, "direction": direction,
                                             "width": width, "storage_endian": storage_endian})
            return value.args.exprs[0]

        def field(value):
            if is_target(value):
                return "raw"
            if isinstance(value, c_ast.FuncCall) and is_target(conversion(value, "to_host")):
                return "to_host"
            _reject("unsupported_field_expression", "field must be direct or one registered to_host conversion")

        def integer(value):
            if isinstance(value, c_ast.Constant):
                number = _literal(value)
                facts["constant_terms"].append({"kind": "literal", "token": value.value, "value": number})
            elif isinstance(value, c_ast.ID) and value.name in constants:
                number = constants[value.name]
                facts["constant_terms"].append({"kind": "external_constant", "name": value.name, "value": number})
            elif isinstance(value, c_ast.BinaryOp) and value.op == "|":
                number = integer(value.left) | integer(value.right)
            else:
                _reject("unsupported_mask_expression", "mask requires known integer constants and pure bitwise OR")
            if not 0 <= number < (1 << width):
                _reject("constant_out_of_width", "a mask term or result exceeds the encoded field width")
            return number

        def mask(value):
            if isinstance(value, c_ast.FuncCall):
                return integer(conversion(value, "to_storage")), "to_storage"
            return integer(value), "host"

        operation = "nonzero"
        if isinstance(node, c_ast.BinaryOp) and node.op in {"==", "!="}:
            comparison = node.op
            # Only an explicit literal zero is admitted, on either side.
            if isinstance(node.right, c_ast.Constant) and _literal(node.right) == 0:
                node = node.left
            elif isinstance(node.left, c_ast.Constant) and _literal(node.left) == 0:
                node = node.right
            else:
                _reject("unsupported_comparison", "only a direct comparison with literal zero is supported")
            operation = "zero" if comparison == "==" else "nonzero"

        spec: dict[str, Any] = {"width": width, "storage_endian": storage_endian}
        if isinstance(node, c_ast.BinaryOp) and node.op == "&":
            if operation == "zero":
                _reject("unsupported_mask_polarity", "masked equality to zero is outside this fixed operation set")
            if target_count(node.left) == 1 and target_count(node.right) == 0:
                target, constant = node.left, node.right
            elif target_count(node.right) == 1 and target_count(node.left) == 0:
                target, constant = node.right, node.left
            else:
                _reject("unsupported_mask_expression", "one target and one pure mask are required")
            mask_value, mask_transform = mask(constant)
            spec.update(field_transform=field(target), operation="masked_nonzero",
                        mask=mask_value, mask_transform=mask_transform)
        else:
            spec.update(field_transform=field(node), operation=operation)
        result.update(status="extracted", reason="supported_local_representation_predicate", spec_partial=spec)
    except _Unsupported as exc:
        result["reason"] = exc.reason
        facts["detail"] = str(exc)
    except (c_parser.ParseError if c_parser is not None else ValueError) as exc:
        result["reason"] = "c_parse_error"
        facts["detail"] = str(exc)
    return result
