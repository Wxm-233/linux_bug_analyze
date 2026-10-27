"""Pure fixed-width representation predicates, independent of source names.

This module evaluates a declared byte-order/operation model.  It does not infer
types, macros, source bindings, legal configurations or reachable disk states.
For masked nonzero predicates, equality of selected semantic-bit sets proves
equivalence over the full unsigned domain; differing sets yield a basis witness.
"""
from __future__ import annotations


WIDTHS = {8, 16, 32, 64}
ENDIANS = {"little", "big"}
OPERATIONS = {"masked_nonzero", "zero", "nonzero"}
BASE_FIELDS = {"width", "storage_endian", "host_endian", "field_transform", "operation"}


def _bit_position(bit, width, reverse_bytes):
    byte, within_byte = divmod(bit, 8)
    return ((width // 8 - 1 - byte) if reverse_bytes else byte) * 8 + within_byte


def _permute(value, width, reverse_bytes):
    result = 0
    for bit in range(width):
        if value & (1 << bit):
            result |= 1 << _bit_position(bit, width, reverse_bytes)
    return result


def analyze_representation(spec: dict) -> dict:
    """Prove a supported declared predicate equivalent, or give a basis witness.

    Exact schema: width in 8/16/32/64; storage_endian and host_endian in
    little/big; field_transform in raw/to_host; operation in masked_nonzero,
    zero, nonzero.  Only masked_nonzero additionally requires mask (unsigned
    width-sized integer, never bool) and mask_transform (host/to_storage).

    A semantic value is the unsigned value defined by the storage format.
    Semantic values are serialized in storage order, loaded in host order,
    optionally converted to host semantics, and then used by the selected
    operation.  The expected predicate always uses the decoded semantic value.
    The proof is about the resulting Boolean predicate, not numeric equality
    of unconverted operands or correctness of an enclosing source function.
    """
    result = {"status": "insufficient", "reason": None, "proof_scope": None,
              "basis": None, "sample": None}

    def reject(reason):
        result["reason"] = reason
        return result

    if not isinstance(spec, dict):
        return reject("spec_must_be_a_dictionary")
    operation = spec.get("operation")
    if not isinstance(operation, str) or operation not in OPERATIONS:
        return reject("unsupported_operation")
    required = BASE_FIELDS | ({"mask", "mask_transform"} if operation == "masked_nonzero" else set())
    if set(spec) != required:
        return reject("missing_or_unexpected_schema_fields")
    width = spec["width"]
    if type(width) is not int or width not in WIDTHS:
        return reject("unsupported_unsigned_width")
    for key in ("storage_endian", "host_endian"):
        if not isinstance(spec[key], str) or spec[key] not in ENDIANS:
            return reject("unsupported_" + key)
    if not isinstance(spec["field_transform"], str) or spec["field_transform"] not in {"raw", "to_host"}:
        return reject("unsupported_field_transform")
    if operation == "masked_nonzero":
        if type(spec["mask"]) is not int or not 0 <= spec["mask"] < (1 << width):
            return reject("mask_must_be_unsigned_width_sized_non_boolean_integer")
        if not isinstance(spec["mask_transform"], str) or spec["mask_transform"] not in {"host", "to_storage"}:
            return reject("unsupported_mask_transform")

    reverse_load = spec["storage_endian"] != spec["host_endian"]
    reverse_field = reverse_load and spec["field_transform"] == "raw"
    mapping = [_bit_position(bit, width, reverse_field) for bit in range(width)]
    result["proof_scope"] = {
        "kind": "declared_fixed_width_unsigned_boolean_predicate",
        "width": width, "domain_cardinality": 1 << width,
        "quantification": "all_unsigned_values_of_declared_width",
        "storage_endian": spec["storage_endian"], "host_endian": spec["host_endian"],
        "premises": ["exact declared width and unsigned bitvector domain",
                     "load interprets the same storage bytes in host order",
                     "conversion is the declared identity or whole-byte permutation",
                     "only the selected Boolean operation is evaluated"],
        "not_proved": ["source types or macro expansion", "actual machine configuration",
                       "memory access validity", "reachable filesystem or device state",
                       "enclosing function or complete execution correctness"],
    }
    rows = []
    for bit in range(width):
        rows.append({"semantic_bit": bit, "loaded_bit": _bit_position(bit, width, reverse_load),
                     "field_bit": mapping[bit]})
    audit = {"field_bit_mapping_is_bijection": sorted(mapping) == list(range(width)),
             "zero_maps_to_zero": True, "rows": rows,
             "basis_rows_are_not_a_random_test_sample": True}
    result["basis"] = audit

    if operation == "masked_nonzero":
        mask_value = _permute(spec["mask"], width, reverse_load and spec["mask_transform"] == "to_storage")
        actual_bits = [bit for bit in range(width) if mask_value & (1 << mapping[bit])]
        expected_bits = [bit for bit in range(width) if spec["mask"] & (1 << bit)]
        for row in rows:
            row.update(actual=bool(mask_value & (1 << row["field_bit"])),
                       expected=bool(spec["mask"] & (1 << row["semantic_bit"])))
        differences = [bit for bit in range(width) if (bit in actual_bits) != (bit in expected_bits)]
        audit.update(method="selected_semantic_bit_sets_for_boolean_or",
                     actual_selected_bits=actual_bits, expected_selected_bits=expected_bits,
                     differing_bits=differences,
                     proof_argument="Each predicate is OR of its selected input bits. Equal sets are equivalent for every input; a differing bit alone is a counterexample.")
        equivalent = not differences
        value = (1 << differences[0]) if differences else (1 << expected_bits[0]) if expected_bits else 0
        result.update(status="equivalent" if equivalent else "counterexample",
                      reason="same_selected_semantic_bits" if equivalent else "different_selected_semantic_bits")
    else:
        mask_value = None
        for row in rows:
            row.update(actual=operation == "nonzero", expected=operation == "nonzero")
        audit.update(method="bijective_bit_permutation_preserves_zero_and_nonzero",
                     proof_argument="A bit permutation maps zero to zero and every nonzero bitvector to a nonzero bitvector; the Boolean zero/nonzero predicate is unchanged.")
        value = 0 if operation == "zero" else 1
        result.update(status="equivalent", reason="bijective_bit_permutation_preserves_zero_and_nonzero")

    loaded = _permute(value, width, reverse_load)
    field = _permute(value, width, reverse_field)
    if operation == "masked_nonzero":
        actual, expected = bool(field & mask_value), bool(value & spec["mask"])
    else:
        actual = field == 0 if operation == "zero" else field != 0
        expected = value == 0 if operation == "zero" else value != 0
    result["sample"] = {"semantic_value": value, "storage_bytes_hex": value.to_bytes(width // 8, spec["storage_endian"]).hex(),
                        "loaded_value": loaded, "field_value": field,
                        "mask_value": mask_value, "actual": actual, "expected": expected}
    return result
