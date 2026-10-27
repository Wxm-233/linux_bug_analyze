"""Offline value/type boundaries for frozen producer v4; not holdout accuracy."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import representation_producer_v4 as producer


class IntegerExpressionTests(unittest.TestCase):
    def proof(self, expression, definitions="", scalars=None):
        macros, refused = producer.macro_definitions({"driver.c": definitions})
        return producer.prove_expression(expression, macros, refused, scalars)

    def values(self, proof):
        self.assertEqual(proof["status"], "proven", proof)
        return [item["exact_value"] for item in proof["models"]]

    def test_hisi_shape_offset_mask_and_evidence(self):
        proof = self.proof("MASK", "#define OFF 17\n#define MASK (0x1U << OFF)\n")
        self.assertEqual(self.values(proof), [131072, 131072])
        self.assertEqual(set(proof["macro_evidence"]), {"MASK", "OFF"})
        self.assertTrue(all(item["unsigned"] and item["bits"] == 32 for item in proof["models"]))

    def test_c_literal_types_and_promotions(self):
        self.assertEqual(self.values(self.proof("0x80000000")), [2147483648] * 2)
        proof = self.proof("0xffffffff + 0ULL")
        self.assertEqual(self.values(proof), [4294967295] * 2)
        self.assertEqual([item["bits"] for item in proof["models"]], [64, 64])
        self.assertEqual(self.values(self.proof("077U + 1")), [64, 64])
        self.assertEqual(self.values(self.proof("((u16) 7) << 3")), [56, 56])

    def test_precedence_and_exact_unsigned_wrap(self):
        self.assertEqual(self.values(self.proof("1U << 3 + 1")), [16, 16])
        self.assertEqual(self.values(self.proof("(1U << 4) | 3U")), [19, 19])
        self.assertEqual(self.values(self.proof("~0U")), [4294967295] * 2)
        self.assertEqual(self.values(self.proof("0xffffffffU + 1U")), [0, 0])

    def test_shift_rejects_invalid_count_and_loss(self):
        for expression in ("1U << 32", "1U << -1", "1U << 65", "3U << 31", "(-1) >> 1"):
            with self.subTest(expression=expression):
                self.assertEqual(self.proof(expression)["status"], "insufficient")

    def test_signed_overflow_is_not_unsigned_normal(self):
        for expression in ("1 << 31", "2147483647 + 1", "(-2147483647 - 1) / -1", "(-2147483647 - 1) % -1"):
            with self.subTest(expression=expression):
                self.assertEqual(self.proof(expression)["status"], "insufficient")
        self.assertEqual(self.values(self.proof("1U << 31")), [2147483648] * 2)

    def test_bit_word_size_and_maximum_width(self):
        proof = self.proof("BIT(31)")
        self.assertEqual(self.values(proof), [2147483648] * 2)
        self.assertEqual([item["bits"] for item in proof["models"]], [32, 64])
        self.assertEqual(self.proof("BIT(33)")["status"], "insufficient")
        self.assertEqual(self.values(self.proof("BIT_ULL(63)")), [9223372036854775808] * 2)

    def test_host_range_is_bounded_not_invented_exact_value(self):
        proof = self.proof("value & 0xffU", scalars={"value": "u32"})
        self.assertEqual(proof["status"], "proven")
        self.assertTrue(all(item["minimum"] == 0 and item["maximum"] == 255 and item["exact_value"] is None for item in proof["models"]))
        self.assertEqual(self.proof("value << 1", scalars={"value": "u32"})["status"], "insufficient")

    def test_conflicts_conditional_undef_and_function_macros(self):
        examples = ("#define X 1U\n#define X 2U\n",
                    "#if CONFIG_BIG\n#define X 1U\n#else\n#define X 2U\n#endif\n",
                    "#define X 1U\n#undef X\n",
                    "#define BIT(n) (7U << (n))\n")
        for definitions in examples:
            expr = "BIT(2)" if "BIT(" in definitions else "X"
            with self.subTest(definitions=definitions):
                self.assertEqual(self.proof(expr, definitions)["status"], "insufficient")

    def test_macro_cycles_expansion_budget_and_unsafe_substitution(self):
        self.assertEqual(self.proof("A", "#define A B\n#define B A\n")["status"], "insufficient")
        self.assertEqual(self.proof("X * 2", "#define X 1 + 1\n")["status"], "insufficient")
        chain = "\n".join(f"#define X{i} X{i + 1}" for i in range(20)) + "\n#define X20 1\n"
        self.assertEqual(self.proof("X0", chain)["status"], "insufficient")
        self.assertEqual(self.proof(" + ".join(["1"] * 100))["status"], "insufficient")
        branching = "\n".join(f"#define X{i} (X{i + 1} + X{i + 1})" for i in range(10)) + "\n#define X10 1U\n"
        proof = self.proof("X0", branching)
        self.assertEqual(proof["status"], "insufficient")
        self.assertIn("budget", proof["models"][0]["reason"])

    def test_narrow_cast_and_unknown_calls_refused(self):
        for expression in ("(u8) 256", "mystery(1U)", "sizeof(int)", "1 ? 2 : 3", "09", "0x1UU"):
            with self.subTest(expression=expression):
                self.assertEqual(self.proof(expression)["status"], "insufficient")


class EndianWriteTests(unittest.TestCase):
    def test_typed_macro_missing_and_explicit_conversion(self):
        source = """
#define OFF 17
#define MASK (0x1U << OFF)
struct wire { __le32 value; };
void old(struct wire *message) { message->value |= MASK; }
void fixed(struct wire *message) { message->value |= cpu_to_le32(MASK); }
"""
        report = producer.analyze_text(source)
        self.assertEqual([(item["function"], item["status"]) for item in report["findings"]], [("old", "candidate"), ("fixed", "normal")])
        self.assertIsNotNone(report["findings"][0]["proposed_check"])
        self.assertEqual(report["findings"][0]["expression_proof"]["models"][0]["exact_value"], 131072)

    def test_dw_modes_are_distinguished_by_explicit_types(self):
        source = """
#define MASK BIT(3)
struct desc32 { __le32 des0; };
struct desc64 { u32 des0; };
void prepare32(struct desc32 *desc) { desc->des0 |= cpu_to_le32(MASK); }
void prepare64(struct desc64 *desc) { desc->des0 |= MASK; }
void true_missing32(struct desc32 *desc) { desc->des0 |= MASK; }
"""
        report = producer.analyze_text(source)
        self.assertEqual([(item["function"], item["status"]) for item in report["findings"]], [("prepare32", "normal"), ("true_missing32", "insufficient")])
        self.assertFalse(any(item["function"] == "prepare64" for item in report["findings"]))

    def test_byte_swap_invariant_constants_are_local_normal(self):
        source = """
struct wire { __be32 value; };
void fill(struct wire *message) {
    message->value = 0;
    message->value = ~0U;
    message->value = 0x12222212U;
    message->value = 1U;
}
"""
        statuses = [item["status"] for item in producer.analyze_text(source)["findings"]]
        self.assertEqual(statuses, ["normal", "normal", "normal", "candidate"])

    def test_wrong_endian_conversion_and_big_value_refused(self):
        source = """
struct wire { __be32 value; };
void fill(struct wire *message) {
    message->value = cpu_to_le32(1U);
    message->value = BIT_ULL(40);
    message->value = cpu_to_be32(BIT_ULL(40));
}
"""
        self.assertEqual([item["status"] for item in producer.analyze_text(source)["findings"]], ["insufficient"] * 3)

    def test_no_destination_contract_no_candidate(self):
        source = """
struct wire { u32 value; };
void fill(struct wire *message) { message->value |= (1U << 17); }
"""
        self.assertEqual(producer.analyze_text(source)["counts"]["candidate"], 0)

    def test_scope_shrink_alias_contract_is_not_inferred(self):
        source = """
struct wire { u8 command; u8 rest[3]; __le16 tag; };
void fill(struct wire *message, u32 value) {
    *(u32 *)&message->command = value;
}
"""
        report = producer.analyze_text(source)
        self.assertEqual(report["counts"], {"candidate": 0, "normal": 0, "insufficient": 1})
        self.assertEqual(report["findings"][0]["v3_local_status"], "candidate")

    def test_unknown_macro_reasons_saved_for_both_models(self):
        source = """
struct wire { __le32 value; };
void fill(struct wire *message) { message->value |= UNKNOWN; }
"""
        report = producer.analyze_text(source)
        self.assertEqual(report["findings"][0]["status"], "insufficient")
        self.assertTrue(all("reason" in item for item in report["findings"][0]["expression_proof"]["models"]))

    def test_signed_full_range_source_not_treated_as_nonnegative(self):
        source = """
struct wire { __le32 value; };
void fill(struct wire *message, s32 signed_value, u32 host_value) {
    message->value = signed_value;
    message->value = host_value;
    message->value = cpu_to_le32(host_value);
}
"""
        self.assertEqual([item["status"] for item in producer.analyze_text(source)["findings"]], ["insufficient", "candidate", "normal"])

    def test_macro_defined_after_write_is_not_visible(self):
        source = """
struct wire { __le32 value; };
void fill(struct wire *message) { message->value |= LATE; }
#define LATE (1U << 17)
"""
        item = producer.analyze_text(source)["findings"][0]
        self.assertEqual(item["status"], "insufficient")
        self.assertIn("before the write", item["expression_proof"]["models"][0]["reason"])

    def test_same_named_scalar_scope_ambiguity_refused(self):
        source = """
struct wire { __le32 value; };
void fill(struct wire *message, u32 value) {
    { s32 value = 0; }
    message->value = value;
}
"""
        self.assertEqual(producer.analyze_text(source)["findings"][0]["status"], "insufficient")

    def test_same_named_object_scope_ambiguity_refused(self):
        source = """
struct wire { __le32 value; };
struct other { __be32 value; };
void fill(struct wire *message) {
    { struct other *message; }
    message->value = 1U;
}
"""
        self.assertEqual(producer.analyze_text(source)["findings"][0]["status"], "insufficient")

    def test_header_macros_are_not_proved_by_late_include_inventory(self):
        source = """
struct wire { __le32 value; };
void fill(struct wire *message) { message->value |= FLAG; }
#include "late.h"
"""
        report = producer.analyze_text(source, "driver.c", {"driver.c": source, "late.h": "#define FLAG (1U << 17)\n"})
        self.assertEqual(report["findings"][0]["status"], "insufficient")
        enum_source = """
enum { FLAG = 1 };
struct wire { __le32 value; };
void fill(struct wire *message) { message->value |= FLAG; }
#include "late.h"
"""
        report = producer.analyze_text(enum_source, "driver.c", {"driver.c": enum_source, "late.h": "#define FLAG 0\n"})
        self.assertEqual(report["findings"][0]["status"], "insufficient")

    def test_endian_parameter_shadow_not_hidden_by_v3_normal_fallback(self):
        source = """
struct wire { __le32 value; };
void fill(struct wire *message, __le32 encoded) {
    { u32 encoded = 1; }
    message->value = encoded;
}
"""
        report = producer.analyze_text(source)
        self.assertEqual(report["findings"][0]["v3_local_status"], "normal")
        self.assertEqual(report["findings"][0]["status"], "insufficient")

    def test_plain_bit_model_cannot_generate_new_candidate(self):
        source = """
struct wire { __le32 value; };
void fill(struct wire *message) { message->value |= BIT(17); }
"""
        item = producer.analyze_text(source)["findings"][0]
        self.assertEqual(item["status"], "insufficient")
        self.assertTrue(item["expression_proof"]["bit_model_assumption"])

    def test_undef_zero_then_enum_not_inherited_as_v3_normal(self):
        source = """
#define FLAG 0
#undef FLAG
enum { FLAG = 1 };
struct wire { __le32 value; };
void fill(struct wire *message) { message->value |= FLAG; }
"""
        self.assertEqual(producer.analyze_text(source)["findings"][0]["status"], "insufficient")


if __name__ == "__main__":
    unittest.main()
