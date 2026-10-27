"""Bounded declaration-depth tests; development coverage, not accuracy."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import representation_producer_v5 as producer


class PointerDepthTests(unittest.TestCase):
    def report(self, declaration, statement):
        source = f"""struct box {{ {declaration} }};
void f(struct box *ioc, u32 value, unsigned int i)
{{
    {statement}
}}
"""
        return producer.analyze_text(source)

    def test_pointer_object_assignments_are_separate(self):
        for rhs in ("NULL", "dma_pool_alloc(pool, flags, &dma)", "0", "value"):
            with self.subTest(rhs=rhs):
                report = self.report("__le32 *reply_free;", f"ioc->reply_free = {rhs};")
                self.assertEqual(report["counts"], {"candidate": 0, "normal": 0, "insufficient": 0})
                self.assertEqual(report["filtered_pointer_count"], 1)
                item = report["filtered_pointer_sites"][0]
                self.assertEqual(item["lvalue_shape_proof"]["target_kind"], "pointer_object")
                self.assertIn(rhs, item["original_source_line"])
                self.assertEqual(item["lvalue_shape_proof"]["declarations"][0]["declaration_text"], "__le32 *reply_free;")

    def test_pointer_element_still_has_endian_contract(self):
        report = self.report("__le32 *reply_free;", "ioc->reply_free[i] = cpu_to_le32(value);")
        self.assertEqual(report["counts"]["normal"], 1)
        self.assertEqual(report["filtered_pointer_count"], 0)
        self.assertEqual(report["findings"][0]["lvalue_shape_proof"]["remaining_layers"], [])

    def test_direct_and_parenthesized_explicit_dereference(self):
        for lhs in ("*ioc->reply_free", "*(ioc->reply_free)"):
            with self.subTest(lhs=lhs):
                report = self.report("__le32 *reply_free;", f"{lhs} = cpu_to_le32(value);")
                self.assertEqual(report["counts"]["normal"], 1, report)
                self.assertEqual(report["filtered_pointer_count"], 0)
                self.assertEqual(report["findings"][0]["original_lvalue"], lhs)

    def test_fixed_array_whole_write_is_not_normal(self):
        report = self.report("__le32 foo[2];", "ioc->foo = 0;")
        self.assertEqual(report["counts"]["normal"], 0)
        self.assertEqual(report["counts"]["insufficient"], 1)
        self.assertEqual(report["findings"][0]["lvalue_shape_proof"]["target_kind"], "array_object")

    def test_fixed_array_element_is_preserved(self):
        report = self.report("__le32 foo[2];", "ioc->foo[i] = cpu_to_le32(value);")
        self.assertEqual(report["counts"]["normal"], 1)
        self.assertEqual(report["filtered_pointer_count"], 0)

    def test_scalar_candidate_and_normal_are_preserved(self):
        for statement, wanted in (("ioc->foo = value;", "candidate"),
                                   ("ioc->foo = cpu_to_le32(value);", "normal"),
                                   ("ioc->foo = 0;", "normal")):
            with self.subTest(statement=statement):
                report = self.report("__le32 foo;", statement)
                self.assertEqual(report["counts"][wanted], 1, report)

    def test_remaining_pointer_layer_is_filtered_not_scalar(self):
        report = self.report("__le32 **foo;", "ioc->foo[i] = NULL;")
        self.assertEqual(report["filtered_pointer_count"], 1, report)
        self.assertEqual(report["filtered_pointer_sites"][0]["lvalue_shape_proof"]["remaining_layers"], ["pointer"])

    def test_unknown_parenthesized_declarator_is_insufficient(self):
        report = self.report("__le32 (*foo)[2];", "ioc->foo[i] = 0;")
        self.assertEqual(report["counts"]["insufficient"], 1, report)
        self.assertEqual(report["filtered_pointer_count"], 0)

    def test_pointer_array_element_still_pointer_object(self):
        report = self.report("__le32 *foo[2];", "ioc->foo[i] = NULL;")
        self.assertEqual(report["filtered_pointer_count"], 1)
        self.assertEqual(report["filtered_pointer_sites"][0]["lvalue_shape_proof"]["remaining_layers"], ["pointer"])

    def test_multidimensional_array_never_promoted_by_base_grammar(self):
        report = self.report("__le32 foo[2][3];", "ioc->foo[i][0] = cpu_to_le32(value);")
        self.assertEqual(report["counts"]["insufficient"], 1, report)
        self.assertEqual(report["counts"]["normal"], 0)

    def test_invalid_scalar_subscript_is_insufficient(self):
        report = self.report("__le32 foo;", "ioc->foo[i] = 0;")
        self.assertEqual(report["counts"]["insufficient"], 1)
        self.assertEqual(report["counts"]["normal"], 0)

    def test_nested_pointer_aggregate_layer(self):
        source = """struct child { __le32 value; };
struct box { struct child *child; };
void f(struct box *ioc, u32 value)
{
    ioc->child->value = cpu_to_le32(value);
}
"""
        report = producer.analyze_text(source)
        self.assertEqual(report["counts"]["normal"], 1, report)
        self.assertEqual(len(report["findings"][0]["lvalue_shape_proof"]["declarations"]), 2)

    def test_single_conditional_member_is_not_filtered_as_proven(self):
        source = """struct box {
#ifdef CONFIG_MODE
    __le32 *foo;
#endif
};
void f(struct box *ioc) {
    ioc->foo = 0;
}
"""
        report = producer.analyze_text(source)
        self.assertEqual(report["counts"]["insufficient"], 1, report)
        self.assertEqual(report["filtered_pointer_count"], 0)
        self.assertIn("preprocessing", report["findings"][0]["reason"])

    def test_outer_conditional_struct_is_not_a_proven_shape(self):
        source = """#ifdef CONFIG_MODE
struct box { __le32 *foo; };
#endif
void f(struct box *ioc) {
    ioc->foo = 0;
}
"""
        report = producer.analyze_text(source)
        self.assertEqual(report["counts"]["insufficient"], 1)
        self.assertEqual(report["filtered_pointer_count"], 0)

    def test_header_guard_inventory_assumption_is_explicit(self):
        source = "void f(struct box *ioc) {\n ioc->foo = 0;\n}\n"
        header = "#ifndef BOX_H\n#define BOX_H\nstruct box { __le32 *foo; };\n#endif\n"
        report = producer.analyze_text(source, "driver.c", {"driver.c": source, "box.h": header})
        self.assertEqual(report["filtered_pointer_count"], 1)
        self.assertIn("inventory assumptions", report["scope"])

    def test_later_same_name_different_mode_never_supplies_endian_authority(self):
        source = """struct native_box { u32 foo; };
struct wire_box { __le32 foo; };
void f(unsigned int mode, u32 value)
{
    if (mode) {
        struct native_box *p;
        p->foo = 0;
    } else {
        struct wire_box *p;
        p->foo = cpu_to_le32(value);
    }
}
"""
        report = producer.analyze_text(source)
        first = next(item for item in report["findings"] if item["line"] == 7)
        self.assertEqual(first["status"], "insufficient", report)
        self.assertEqual(first["lvalue_shape_proof"]["element_type"], "u32")
        self.assertIsNone(first["proposed_check"])


if __name__ == "__main__":
    unittest.main()
