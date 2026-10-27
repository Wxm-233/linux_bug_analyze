"""Semantic boundary tests for the limited source-fact grammar."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import interface_fact_extractor as e


def src(text):
    return e.Source("synthetic.c", "synthetic", "synthetic.c", "synthetic", text.encode())


API_HELPER = """
void put_utf16(wchar_t *s, unsigned c, enum utf16_endian endian) {
    switch (endian) {
    default: *s = (wchar_t) c; break;
    case UTF16_LITTLE_ENDIAN: *s = __cpu_to_le16(c); break;
    case UTF16_BIG_ENDIAN: *s = __cpu_to_be16(c); break;
    }
}
int utf8s_to_utf16s(const u8 *s, int n, enum utf16_endian endian, wchar_t *out, int cap) {
    put_utf16(out, 1, endian); return 1;
}
"""


class FactsTest(unittest.TestCase):
    def reads(self, expression, kind="__le32", prefix=""):
        s = src(f"struct disk {{ {kind} flags; }};\nvoid f(struct disk *p) {{ {prefix} if ({expression}) {{ }} }}")
        return e.scalar_reads(s, s, "f", "p", "disk", "flags")

    def test_atomic_conversion_does_not_certify_second_read(self):
        self.assertEqual([x["status"] for x in self.reads("le32_to_cpu(p->flags) == 1 && (p->flags & MASK)")], ["normal", "candidate"])

    def test_repeated_read_same_atom_refused(self):
        self.assertEqual([x["status"] for x in self.reads("le32_to_cpu(p->flags) | p->flags")], ["insufficient", "insufficient"])

    def test_mask_same_domain(self):
        self.assertEqual(self.reads("p->flags & cpu_to_le32(MASK)")[0]["status"], "normal")

    def test_partial_mask_conversion_not_normal(self):
        self.assertNotEqual(self.reads("p->flags & cpu_to_le32(MASK) | opaque()")[0]["status"], "normal")

    def test_wrong_width_conversion(self):
        self.assertNotEqual(self.reads("le16_to_cpu(p->flags) & MASK")[0]["status"], "normal")

    def test_zero_tests_are_local(self):
        for expr in ("p->flags == 0", "0 == p->flags", "p->flags != 0", "p->flags", "!p->flags"):
            with self.subTest(expr=expr):
                self.assertEqual(self.reads(expr)[0]["status"], "normal")

    def test_arithmetic_is_not_zero_test(self):
        for expr in ("(p->flags + 1) == 0", "(p->flags & MASK) == 0"):
            with self.subTest(expr=expr):
                self.assertNotEqual(self.reads(expr)[0]["status"], "normal")

    def test_unknown_external_format_is_not_host_contract(self):
        self.assertEqual(self.reads("p->flags & MASK", "u32")[0]["status"], "insufficient")

    def test_shadow_refused(self):
        with self.assertRaises(ValueError):
            self.reads("p->flags & MASK", prefix="struct disk *p;")

    def test_opaque_typedef_shadow_refused(self):
        with self.assertRaises(ValueError):
            self.reads("p->flags & MASK", prefix="opaque_t *p;")

    def test_opaque_array_shadow_refused(self):
        with self.assertRaises(ValueError):
            self.reads("p->flags & MASK", prefix="opaque_t p[2];")

    def test_multi_declarator_shadow_refused(self):
        with self.assertRaises(ValueError):
            self.reads("p->flags & MASK", prefix="struct host *q, *p;")

    def test_switch_case_call_is_not_multi_declaration(self):
        s = src("void f(void) { struct packet *p; tag = le64_get_bits(p->tl, MASK); switch (tag) { case KIND: consumer(a, p, out); break; } }")
        h = src("struct packet { __le64 tl; };")
        self.assertEqual(e.bitfield_read(s, h, "f", "p", "packet", "tl", src(""))["status"], "normal")

    def test_multiline_mask_supported(self):
        self.assertEqual(self.reads("p->flags & (A |\n B)")[0]["status"], "candidate")

    def test_converted_zero_test(self):
        self.assertEqual(self.reads("le32_to_cpu(p->flags)")[0]["status"], "normal")

    def test_cross_revision_declaration_refused(self):
        s = src("struct disk { __le32 flags; };\nvoid f(struct disk *p) { if (p->flags == 0) {} }")
        other = e.Source(s.path, "different", s.saved_path, s.blob, s.raw)
        with self.assertRaises(ValueError):
            e.scalar_reads(s, other, "f", "p", "disk", "flags")

    def test_comments_not_references(self):
        self.assertEqual(len(self.reads("p->flags == 0 /* p->flags & MASK */")), 1)

    def test_scalar_sizeof_does_not_read_field(self):
        s = src("struct disk { __le32 flags; };\nvoid f(struct disk *p) { if (n < sizeof(p->flags)) {} }")
        result = e.sizeof_references(s, s, "f", "p", "disk", "flags")
        self.assertEqual(result[0]["status"], "not_value_read")
        self.assertEqual(result[0]["runtime_operation"], "operand_not_evaluated")

    def test_array_or_vla_not_certified_fixed_scalar(self):
        for decl in ("__le32 flags[4];", "u32 flags[n];", "opaque_t flags;"):
            with self.subTest(decl=decl), self.assertRaises(ValueError):
                e.field(src("struct disk { " + decl + " };"), "disk", "flags")

    def test_nested_field_not_direct(self):
        with self.assertRaises(ValueError):
            e.field(src("struct disk { struct { __le32 flags; } nested; };"), "disk", "flags")

    def test_duplicate_declarations_refused(self):
        with self.assertRaises(ValueError):
            e.field(src("struct disk { __le32 flags; }; struct disk { u32 flags; };"), "disk", "flags")

    def test_literal_mask(self):
        s = src("#define A 0x20\n#define B 0x40\n")
        self.assertEqual(e.constant(s, "A | B")["value"], 0x60)

    def test_expression_macro_not_executed(self):
        with self.assertRaises(ValueError):
            e.constant(src("#define A side_effect()\n"), "A")

    def test_duplicate_macro_refused(self):
        with self.assertRaises(ValueError):
            e.constant(src("#define A 0\n#define A 1\n"), "A")

    def domain(self, tail, head="", static="static "):
        return e.visible_call_domain(src(head + f"\n{static}int getter(u32 value) {{ return value; }}\n" + tail), "getter", 0)

    def test_visible_zero_domain(self):
        r = self.domain("void caller(void) { getter(REG); }", "#define REG 0x0\n")
        self.assertEqual(r["values"], [0])
        self.assertEqual(r["runtime_reachability"], "unknown")

    def test_nonzero_domain_kept(self):
        self.assertEqual(self.domain("void caller(void) { getter(0); getter(1); }")["values"], [0, 1])

    def test_address_escape_refuses_closed_domain(self):
        self.assertEqual(self.domain("void caller(void) { fp = getter; getter(0); }")["status"], "insufficient")

    def test_nonstatic_domain_refused(self):
        self.assertEqual(self.domain("void caller(void) { getter(0); }", static="")["status"], "insufficient")

    def test_unknown_argument_refused(self):
        self.assertEqual(self.domain("void caller(u32 v) { getter(v); }")["status"], "insufficient")

    def test_conditional_macro_domain_refused(self):
        self.assertEqual(self.domain("void caller(void) { getter(REG); }", "#if A\n#define REG 0\n#else\n#define REG 1\n#endif\n")["status"], "insufficient")

    def test_ifdef_domain_refused(self):
        self.assertEqual(self.domain("void caller(void) { getter(0); }", "#ifdef A\n#define REG 0\n#endif\n")["status"], "insufficient")

    def test_recursion_domain_refused(self):
        s = src("static int getter(u32 v) { return getter(0); }")
        self.assertEqual(e.visible_call_domain(s, "getter", 0)["status"], "insufficient")

    def test_argument_split_respects_nested_expression(self):
        s = src("void f(void) { encode(a, fn(b, c), LE, out, 4); }")
        f = e.function(s, "f")
        self.assertEqual(len(e.calls(s, f["body"], f["end"], "encode")[0]["args"]), 5)

    def test_api_selector_separate_from_cast(self):
        helper = src(API_HELPER)
        for pointer in ("out", "(wchar_t *)out"):
            s = src(f"void f(void) {{ utf8s_to_utf16s(s, n, UTF16_LITTLE_ENDIAN, {pointer}, cap); }}")
            self.assertEqual(e.api_format(s, helper, "f")["status"], "normal")

    def test_api_unknown_selector_not_normal(self):
        helper = src(API_HELPER)
        s = src("void f(void) { utf8s_to_utf16s(s, n, endian, (wchar_t *)out, cap); }")
        self.assertEqual(e.api_format(s, helper, "f")["status"], "insufficient")

    def test_api_selector_shadow_refused(self):
        helper = src(API_HELPER)
        s = src("void f(int UTF16_LITTLE_ENDIAN) { utf8s_to_utf16s(s, n, UTF16_LITTLE_ENDIAN, out, cap); }")
        self.assertEqual(e.api_format(s, helper, "f")["status"], "insufficient")

    def test_api_macro_override_refused(self):
        helper = src(API_HELPER)
        s = src("#define UTF16_LITTLE_ENDIAN other_mode\nvoid f(void) { utf8s_to_utf16s(s, n, UTF16_LITTLE_ENDIAN, out, cap); }")
        self.assertEqual(e.api_format(s, helper, "f")["status"], "insufficient")

    def test_directive_inside_target_function_refused(self):
        with self.assertRaises(ValueError):
            e.function(src("void f(void) {\n#if A\nwork();\n#endif\n}"), "f")

    def test_mutating_parameter_does_not_inherit_caller_value(self):
        s = src("struct packet { __le32 reg; };\nstatic int get(u32 reg) { reg = 1; struct packet msg = { .reg = reg }; return 0; }")
        self.assertEqual(e.initializer_write(s, "get", "packet", "msg", "reg", "reg")["status"], "insufficient")

    def test_parenthesized_mutation_refused(self):
        for modification in ("(reg) = 1;", "++(reg);", "modify(&(reg));"):
            with self.subTest(modification=modification):
                s = src("struct packet { __le32 reg; };\nstatic int get(u32 reg) { " + modification + " struct packet msg = { .reg = reg }; return 0; }")
                self.assertEqual(e.initializer_write(s, "get", "packet", "msg", "reg", "reg")["status"], "insufficient")

    def test_encoded_or_wrong_width_source_not_cpu_conversion(self):
        for kind in ("__le32", "__be32", "u64"):
            with self.subTest(kind=kind):
                s = src(f"struct packet {{ __le32 reg; }};\nstatic int get({kind} reg) {{ struct packet msg = {{ .reg = cpu_to_le32(reg) }}; return 0; }}")
                self.assertEqual(e.initializer_write(s, "get", "packet", "msg", "reg", "reg")["status"], "insufficient")

    def test_statement_expression_evaluation_refused(self):
        with self.assertRaises(ValueError):
            self.reads("p->flags & MASK", prefix="sizeof(({ if (p->flags & MASK) {} 0; }));")

    def test_scalar_helper_macro_override_refused(self):
        s = src("#define le32_to_cpu(x) (x)\nstruct disk { __le32 flags; };\nvoid f(struct disk *p) { if (le32_to_cpu(p->flags) == 1) {} }")
        with self.assertRaises(ValueError):
            e.scalar_reads(s, s, "f", "p", "disk", "flags")

    def test_api_helper_overwrite_refused(self):
        helper = src(API_HELPER.replace("*s = __cpu_to_le16(c); break;", "*s = __cpu_to_le16(c); *s = __cpu_to_be16(c); break;"))
        s = src("void f(void) { utf8s_to_utf16s(s, n, UTF16_LITTLE_ENDIAN, out, cap); }")
        self.assertEqual(e.api_format(s, helper, "f")["status"], "insufficient")

    def test_api_helper_wrong_dispatcher_refused(self):
        helper = src(API_HELPER.replace("switch (endian)", "switch (UTF16_BIG_ENDIAN)"))
        s = src("void f(void) { utf8s_to_utf16s(s, n, UTF16_LITTLE_ENDIAN, out, cap); }")
        self.assertEqual(e.api_format(s, helper, "f")["status"], "insufficient")

    def test_bitfield_width_mismatch_not_normal(self):
        s = src("void f(void) { struct packet *p; tag = le64_get_bits(p->tl, MASK); switch (tag) {} }")
        h = src("struct packet { __le32 tl; };")
        self.assertEqual(e.bitfield_read(s, h, "f", "p", "packet", "tl", src(""))["status"], "insufficient")

    def test_target_shadow_not_bound_to_first_initializer(self):
        s = src("struct packet { __le32 reg; };\nstatic int get(u32 reg) { struct packet msg = { .reg = reg }; { struct packet msg; } return 0; }")
        self.assertEqual(e.initializer_write(s, "get", "packet", "msg", "reg", "reg")["status"], "insufficient")


if __name__ == "__main__":
    unittest.main()
