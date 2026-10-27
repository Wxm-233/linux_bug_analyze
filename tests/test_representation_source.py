"""Constructed syntax/semantic boundary tests; not independent defect samples."""

import unittest
from unittest.mock import patch

from linux_bug_analyze.representation_source import c_parser, extract_representation_predicate


REGISTRY = {
    "decode_word": {"direction": "to_host", "width": 32, "storage_endian": "little"},
    "encode_word": {"direction": "to_storage", "width": 32, "storage_endian": "little"},
    "le32_to_cpu": {"direction": "to_host", "width": 32, "storage_endian": "little"},
    "cpu_to_le32": {"direction": "to_storage", "width": 32, "storage_endian": "little"},
}


def extract(expression, **overrides):
    options = {"field_ref": "record->flags", "declaration": "__le32 flags;",
               "constants": {"FIRST": 1, "SECOND": 0x20}, "conversion_registry": REGISTRY}
    options.update(overrides)
    return extract_representation_predicate(expression, **options)


class RepresentationSourceDependencyTests(unittest.TestCase):
    def test_missing_parser_never_falls_back_to_regex(self):
        with patch("linux_bug_analyze.representation_source.c_parser", None):
            result = extract("record->flags & FIRST")
        self.assertEqual(result["status"], "insufficient")
        self.assertEqual(result["reason"], "pycparser_unavailable")
        self.assertIsNone(result["spec_partial"])


@unittest.skipIf(c_parser is None, "optional research dependency pycparser unavailable")
class RepresentationSourceTests(unittest.TestCase):
    def test_raw_bitmask_is_extracted_without_claiming_it_is_wrong(self):
        result = extract("record->flags & (FIRST | SECOND)")
        self.assertEqual(result["status"], "extracted")
        self.assertEqual(result["spec_partial"], {"width": 32, "storage_endian": "little",
                         "field_transform": "raw", "operation": "masked_nonzero",
                         "mask": 0x21, "mask_transform": "host"})
        self.assertEqual(result["syntax_facts"]["declaration_binding"], "external_review_required")
        self.assertEqual(result["syntax_facts"]["host_endian"], "not_inferred")
        self.assertNotIn("candidate", result)

    def test_registered_decode_changes_field_transform(self):
        result = extract("decode_word(record->flags) & FIRST")
        self.assertEqual(result["status"], "extracted")
        self.assertEqual(result["spec_partial"]["field_transform"], "to_host")
        self.assertEqual(result["syntax_facts"]["conversion_calls"][0]["name"], "decode_word")

    def test_registered_mask_encoding_is_distinct_from_host_mask(self):
        result = extract("record->flags & encode_word(FIRST | SECOND)")
        self.assertEqual(result["status"], "extracted")
        self.assertEqual(result["spec_partial"]["mask_transform"], "to_storage")
        self.assertEqual(result["spec_partial"]["mask"], 0x21)

    def test_direct_truth_and_zero_comparisons_share_fixed_operations(self):
        for expression, operation in [("record->flags", "nonzero"), ("record->flags != 0", "nonzero"),
                                      ("0U != record->flags", "nonzero"), ("record->flags == 0", "zero"),
                                      ("0x0 == record->flags", "zero")]:
            with self.subTest(expression=expression):
                result = extract(expression)
                self.assertEqual(result["status"], "extracted")
                self.assertEqual(result["spec_partial"]["operation"], operation)
                self.assertNotIn("mask", result["spec_partial"])

    def test_mask_nonzero_comparison_and_commuted_pure_mask(self):
        for expression in ["(record->flags & FIRST) != 0", "0 != (FIRST & record->flags)"]:
            with self.subTest(expression=expression):
                result = extract(expression)
                self.assertEqual(result["status"], "extracted")
                self.assertEqual(result["spec_partial"]["operation"], "masked_nonzero")

    def test_integer_bases_and_supported_unsigned_suffixes(self):
        for literal, expected in [("0x10U", 16), ("010UL", 8), ("32uLL", 32), ("0ULL", 0)]:
            with self.subTest(literal=literal):
                result = extract("record->flags & " + literal)
                self.assertEqual(result["status"], "extracted")
                self.assertEqual(result["spec_partial"]["mask"], expected)

    def test_big_endian_and_other_width_require_matching_registry(self):
        result = extract("decode_other(record->flags) & 0x80",
                         declaration="__be16 flags;",
                         conversion_registry={"decode_other": {"direction": "to_host", "width": 16,
                                                                 "storage_endian": "big"}})
        self.assertEqual(result["status"], "extracted")
        self.assertEqual(result["spec_partial"]["width"], 16)
        self.assertEqual(result["spec_partial"]["storage_endian"], "big")

    def test_comments_and_const_do_not_create_semantic_certificates(self):
        result = extract("record->flags /* local */ & FIRST", declaration="const __le32 flags; /* reviewed */")
        self.assertEqual(result["status"], "extracted")
        self.assertNotIn("runtime_witness", result)

    def test_wrong_width_endian_or_direction_conversion_is_insufficient(self):
        for entry in [{"direction": "to_host", "width": 16, "storage_endian": "little"},
                      {"direction": "to_host", "width": 32, "storage_endian": "big"},
                      {"direction": "to_storage", "width": 32, "storage_endian": "little"},
                      {"direction": "to_host", "width": True, "storage_endian": "little"}]:
            with self.subTest(entry=entry):
                result = extract("decode_word(record->flags) & FIRST", conversion_registry={"decode_word": entry})
                self.assertEqual(result["status"], "insufficient")
                self.assertEqual(result["reason"], "conversion_domain_mismatch")
                self.assertIsNone(result["spec_partial"])

    def test_conversion_spelling_does_not_register_its_semantics(self):
        result = extract("le32_to_cpu(record->flags) & FIRST", conversion_registry={})
        self.assertEqual(result["status"], "insufficient")
        self.assertEqual(result["reason"], "unregistered_conversion")

    def test_unsupported_operations_are_not_reduced_to_a_convenient_subexpression(self):
        expressions = ["record->flags & FIRST && ready", "S_ISLNK(record->flags)",
                       "record->flags + FIRST", "record->flags << 1", "record->flags & (FIRST << 1)",
                       "record->flags & variable_mask", "record->flags & ~FIRST", "!record->flags",
                       "record->flags == FIRST", "record->flags & other->flags", "record->flags & fetch()",
                       "record->flags & (FIRST + SECOND)", "(record->flags & FIRST) == 0",
                       "cpu_to_le32(record->flags) & FIRST", "record->flags & le32_to_cpu(FIRST)",
                       "(unsigned int)record->flags", "record->flags & -1", "record->flags & 'a'",
                       "(record->flags, 1)", "record->flags & (FIRST = SECOND)",
                       "decode_word(record->flags, FIRST)", "decode_word(decode_word(record->flags))"]
        for expression in expressions:
            with self.subTest(expression=expression):
                result = extract(expression)
                self.assertEqual(result["status"], "insufficient")
                self.assertIsNone(result["spec_partial"])

    def test_duplicate_target_and_hidden_side_effects_are_rejected(self):
        for expression in ["record->flags & record->flags", "record->flags && record->flags",
                           "record->flags & FIRST++", "record->flags++", "record->flags = FIRST"]:
            with self.subTest(expression=expression):
                result = extract(expression)
                self.assertEqual(result["status"], "insufficient")
                self.assertIsNone(result["spec_partial"])

    def test_scalar_declaration_is_required_and_never_invented_from_a_name(self):
        for declaration in ["unsigned int flags;", "__le32 *flags;", "__le32 flags[1];",
                            "__le32 flags; __le32 other;", "__le32 wrong;", "__le32 flags = 0;",
                            "volatile __le32 flags;", "extern __le32 flags;", "__le32 flags:1;",
                            "typedef __le32 flags;"]:
            with self.subTest(declaration=declaration):
                result = extract("record->flags & FIRST", declaration=declaration)
                self.assertEqual(result["status"], "insufficient")
                self.assertIsNone(result["spec_partial"])

    def test_width_overflow_is_not_silently_truncated(self):
        for expression, constants in [("record->flags & 0x100000000ULL", {}),
                                      ("record->flags & TOO_WIDE", {"TOO_WIDE": 1 << 32}),
                                      ("record->flags & (FIRST | TOO_WIDE)", {"FIRST": 1, "TOO_WIDE": 1 << 32})]:
            with self.subTest(expression=expression):
                result = extract(expression, constants=constants)
                self.assertEqual(result["status"], "insufficient")
                self.assertEqual(result["reason"], "constant_out_of_width")

    def test_only_simple_arrow_field_ref_is_supported(self):
        for field_ref in ["record.flags", "record->nested.flags", "get_record()->flags", "*record", "record->flags[0]"]:
            with self.subTest(field_ref=field_ref):
                result = extract("record->flags & FIRST", field_ref=field_ref)
                self.assertEqual(result["status"], "insufficient")
                self.assertEqual(result["reason"], "unsupported_field_ref")

    def test_invalid_constant_values_are_not_python_truthiness(self):
        for constants in [{"FIRST": True}, {"FIRST": -1}, {"FIRST": "1"}]:
            with self.subTest(constants=constants):
                self.assertEqual(extract("record->flags & FIRST", constants=constants)["status"], "insufficient")

    def test_statements_preprocessor_and_translation_splicing_are_not_deleted(self):
        for expression in ["record->flags) ; mutate(); if (1", "#define FIRST 1\nrecord->flags & FIRST",
                           "record->flags & FI\\\nRST"]:
            with self.subTest(expression=expression):
                self.assertEqual(extract(expression)["status"], "insufficient")


if __name__ == "__main__":
    unittest.main()
