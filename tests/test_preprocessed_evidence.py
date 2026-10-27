import unittest

from linux_bug_analyze.preprocessed_evidence import EvidenceError, extract_definitions


class PreprocessedEvidenceTests(unittest.TestCase):
    def extract(self, text, source="unit.c"):
        return extract_definitions(text, {"consume": source})["consume"]

    def test_line_marker_maps_following_line_and_keeps_flags(self):
        value = self.extract('# 40 "/tree/unit.c" 1 3\nint consume(int x)\n{\n return x;\n}\n')
        self.assertEqual(value["definition_location"]["line"], 40)
        self.assertEqual(value["line_map"][2]["line"], 42)
        self.assertFalse(value["runtime_content_proved"])

    def test_marker_inside_body_is_retained_with_exact_physical_mapping(self):
        raw = '#line 10 "unit.c"\nint consume(void) {\n# 70 "inline.h" 1\n return 1;\n# 12 "unit.c" 2\n}\n'
        value = self.extract(raw)
        self.assertIn('# 70 "inline.h" 1', value["text"])
        ret = value["identifiers"]["return"][0]
        self.assertEqual((ret["path"], ret["line"], ret["physical_line"]), ("inline.h", 70, 4))

    def test_fake_names_braces_and_markers_in_comments_or_literals_are_opaque(self):
        raw = '# 1 "unit.c"\n/*\n# 900 "fake.c"\nconsume(void) { broken\n*/\nint consume(void) { char *s="consume() { # 3 fake }"; return 1; }\n'
        value = self.extract(raw)
        self.assertEqual(value["definition_location"]["line"], 5)
        self.assertEqual(len(value["identifiers"]["consume"]), 1)
        self.assertNotIn("broken", value["identifiers"])

    def test_prototype_and_calls_do_not_supply_definition(self):
        raw = '# 1 "unit.c"\nint consume(int);\nint other(void) { return consume(1); }\nint consume(int x) { return x; }\n'
        self.assertTrue(self.extract(raw)["text"].startswith("int consume(int x)"))

    def test_duplicate_definition_or_wrong_source_is_not_silently_selected(self):
        one = '# 1 "unit.c"\nint consume(void) { return 1; }\n'
        for raw, source in [(one + one, "unit.c"), (one, "other.c"), (one, "nit.c")]:
            with self.subTest(source=source), self.assertRaises(EvidenceError):
                self.extract(raw, source)

    def test_source_selector_disambiguates_different_header_definitions(self):
        raw = '# 1 "other.h"\nint consume(void) { return 2; }\n# 10 "unit.c"\nint consume(void) { return 1; }\n'
        self.assertIn("return 1", self.extract(raw)["text"])

    def test_macro_expansion_gnu_expressions_irq_and_loops_are_not_removed(self):
        raw = '# 240 "unit.c"\nstatic void consume(int cpu) {\n do { irq_save(); } while (0);\n for (int t=0; t<4; t++) lock(({ asm("}"); rq(t); }));\n}\n'
        value = self.extract(raw)
        self.assertIn('asm("}")', value["text"])
        self.assertIn("irq_save", value["identifiers"])
        self.assertIn("for", value["identifiers"])
        self.assertFalse(value["control_flow_proved"])

    def test_unclosed_source_or_literal_or_comment_is_rejected(self):
        for body in ['int consume(void) {', 'int consume(void) { "broken; }', '/* missing']:
            with self.subTest(body=body), self.assertRaises(EvidenceError):
                self.extract('# 1 "unit.c"\n' + body)

    def test_unexpanded_directives_and_splicing_are_rejected(self):
        for extra in ['#if READY\n', '#define READY 1\n', '#error bad\n', '\\\n']:
            with self.subTest(extra=extra), self.assertRaises(EvidenceError):
                self.extract('# 1 "unit.c"\n' + extra + 'int consume(void) { return 0; }\n')

    def test_missing_or_zero_source_location_is_rejected(self):
        for prefix in ["", '# 0 "unit.c"\n']:
            with self.subTest(prefix=prefix), self.assertRaises(EvidenceError):
                self.extract(prefix + 'int consume(void) { return 0; }\n')

    def test_escaped_paths_crlf_and_utf8_byte_offsets(self):
        raw = '/* 中文 */\r\n# 9 "C:\\\\tree\\\\unit.c"\r\nint consume(void) { return 0; }\r\n'
        value = self.extract(raw)
        self.assertEqual(value["definition_location"]["path"], 'C:\\tree\\unit.c')
        self.assertGreater(value["utf8_byte_start"], value["start_offset"])
        self.assertEqual(raw.encode()[value["utf8_byte_start"]:value["utf8_byte_end"]].decode(), value["text"])

    def test_attributes_after_signature_and_pragmas_are_preserved(self):
        raw = '# 1 "unit.c"\nint consume(void) __attribute__((noinline)) {\n#pragma GCC diagnostic push\n return 0;\n}\n'
        value = self.extract(raw)
        self.assertIn("__attribute__", value["text"])
        self.assertIn("#pragma GCC diagnostic push", value["text"])
        self.assertEqual(value["identifiers"]["return"][0]["line"], 3)

    def test_marker_filename_escape_is_decoded_once_or_rejected(self):
        raw = '# 1 "odd\\\"name/unit.c"\nint consume(void) { return 0; }\n'
        self.assertEqual(self.extract(raw)["definition_location"]["path"], 'odd"name/unit.c')
        with self.assertRaises(EvidenceError):
            self.extract('# 1 "odd\\q/unit.c"\nint consume(void) { return 0; }\n')

    def test_inline_aggregate_return_type_is_retained(self):
        raw = '# 1 "unit.c"\nstruct S { int member; } consume(void) { struct S x; return x; }\n'
        self.assertTrue(self.extract(raw)["text"].startswith("struct S { int member; } consume"))

    def test_absolute_selector_cannot_borrow_runtime_suffix(self):
        raw = '# 1 "/runtime/tree/unit.c"\nint consume(void) { return 0; }\n'
        with self.assertRaises(EvidenceError):
            self.extract(raw, "/tree/unit.c")

    def test_name_location_alone_does_not_claim_whole_body_source(self):
        raw = '# 1 "/tree/unit.c"\nint consume(void) {\n# 1 "/runtime/other.c"\n return 0; }\n'
        value = self.extract(raw, "/tree/unit.c")
        self.assertFalse(value["all_token_paths_match_name_location"])
        self.assertEqual(value["mapped_token_sources"], ["/runtime/other.c", "/tree/unit.c"])

    def test_external_declaration_never_supplies_a_definition_by_default(self):
        raw = '# 200 "unit.c"\nunsigned int __attribute__((__pure__)) consume(int n);\n'
        with self.assertRaises(EvidenceError):
            self.extract(raw)
        value = extract_definitions(raw, {"consume": "unit.c"}, allow_declarations=("consume",))["consume"]
        self.assertEqual(value["region_kind"], "declaration_only")
        self.assertNotIn("definition_location", value)
        self.assertFalse(value["control_flow_proved"])

    def test_allowed_declaration_does_not_replace_or_hide_duplicate_definitions(self):
        raw = '# 1 "unit.c"\nint consume(int);\nint consume(int n) { return n; }\n'
        value = extract_definitions(raw, {"consume": "unit.c"}, allow_declarations=("consume",))["consume"]
        self.assertEqual(value["region_kind"], "definition")
        with self.assertRaises(EvidenceError):
            extract_definitions(raw + raw, {"consume": "unit.c"}, allow_declarations=("consume",))


if __name__ == "__main__":
    unittest.main()
