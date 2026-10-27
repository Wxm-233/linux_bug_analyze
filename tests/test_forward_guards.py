import unittest

from linux_bug_analyze.forward_guards import extract_forward_paths, indexed_field_candidates
from linux_bug_analyze.source_conditions import c_parser


@unittest.skipIf(c_parser is None, "optional pycparser unavailable")
class ForwardGuardsTests(unittest.TestCase):
    def analyze(self, text, **kwargs):
        return extract_forward_paths({"id": "unit", "revision": "revision-A", "path": "unit.c",
                                      "start_line": 100, "end_line": 99 + len(text.splitlines()), "text": text}, **kwargs)

    def calls(self, path):
        return [e for e in path["events"] if e["kind"] == "call"]

    def test_denial_skips_set_but_preserves_copy_and_guard(self):
        value = self.analyze('void f(int deny, int *dst) { int mask; clear(&mask); if (deny) goto out; set(&mask); out: copy(dst, &mask); }')
        self.assertEqual(value["status"], "supported_forward_structure")
        denied = next(p for p in value["paths"] if p["guards"][0]["taken"])
        self.assertEqual([e["callee"] for e in self.calls(denied)], ["clear", "copy"])
        self.assertEqual(denied["status"], "structural_terminal")
        self.assertEqual(denied["events"][1]["kind"], "forward_goto")

    def test_two_terminal_paths_and_one_loop_frontier(self):
        value = self.analyze('void f(int deny, int mode, int *dst) { int mask; clear(&mask); if (deny) goto out; set(&mask); if (mode) goto out; for (;;) change(&mask); out: copy(dst, &mask); }')
        self.assertEqual(value["status"], "partial_forward_structure")
        done = [p for p in value["paths"] if p["status"] == "structural_terminal"]
        stopped = [p for p in value["paths"] if p["status"] == "unsupported_frontier"]
        self.assertEqual((len(done), len(stopped)), (2, 1))
        self.assertEqual([e["callee"] for e in self.calls(stopped[0])], ["clear", "set"])
        self.assertIn("For", stopped[0]["endpoint"]["reason"])

    def test_early_return_does_not_reach_copy(self):
        value = self.analyze('void f(int deny) { if (deny) return; copy(); }')
        denied = next(p for p in value["paths"] if p["guards"][0]["taken"])
        self.assertEqual(self.calls(denied), [])
        self.assertEqual(denied["endpoint"]["kind"], "return")

    def test_loop_is_not_removed_even_if_it_looks_zero_iteration(self):
        value = self.analyze('void f(void) { for (int i=0; i<0; i++) prepare(); copy(); }')
        self.assertEqual(value["paths"][0]["status"], "unsupported_frontier")
        self.assertEqual(self.calls(value["paths"][0]), [])

    def test_forward_then_backward_goto_stops(self):
        value = self.analyze('void f(void) { earlier: a(); goto later; later: b(); goto earlier; }')
        path = value["paths"][0]
        self.assertEqual([e["callee"] for e in self.calls(path)], ["a", "b"])
        self.assertEqual(path["status"], "unsupported_frontier")
        self.assertIn("backward", path["endpoint"]["reason"])

    def test_reassigned_destination_is_a_different_source_version(self):
        value = self.analyze('void f(int deny, int *dst, int *other) { before(dst); if (deny) { dst=other; goto out; } out: copy(dst); }')
        path = next(p for p in value["paths"] if p["guards"][0]["taken"])
        first, last = [e["arguments"][0] for e in self.calls(path)]
        self.assertEqual(first["declaration"], last["declaration"])
        self.assertNotEqual(first["version"], last["version"])

    def test_named_static_address_does_not_claim_contents(self):
        value = self.analyze('void f(void) { static int mask; clear(&mask); copy(&mask); }')
        a, b = [e["arguments"][0] for e in self.calls(value["paths"][0])]
        self.assertEqual(a["binding"], "named_declaration_address_only")
        self.assertEqual(a["declaration"], b["declaration"])
        self.assertEqual(a["declaration"]["storage"], ["static"])
        self.assertFalse(value["call_effects_proved"])
        self.assertEqual(value["whole_contract"], "insufficient")

    def test_shadowed_or_escaped_scalar_binding_is_not_inferred(self):
        for text in ['void f(int cpu) { before(cpu); { int cpu; copy(cpu); } }',
                     'void f(int cpu) { mutate(&cpu); copy(cpu); }']:
            with self.subTest(text=text):
                value = self.analyze(text)
                self.assertEqual(self.calls(value["paths"][0])[-1]["arguments"][0]["binding"], "unproved")

    def test_nested_label_and_unresolved_label_are_frontiers(self):
        for text in ['void f(void) { goto out; { out: copy(); } }', 'void f(void) { goto missing; copy(); }']:
            with self.subTest(text=text):
                value = self.analyze(text)
                self.assertEqual(value["paths"][0]["status"], "unsupported_frontier")
                self.assertEqual(self.calls(value["paths"][0]), [])

    def test_repeated_conditions_are_not_assumed_equal(self):
        value = self.analyze('void f(int p) { if (p) a(); opaque(); if (p) b(); }')
        self.assertEqual(len(value["paths"]), 4)
        self.assertTrue(any([g["taken"] for g in p["guards"]] == [True, False] for p in value["paths"]))

    def test_nested_calls_writes_and_indirect_calls_do_not_get_call_sequence_proof(self):
        for body in ['outer(inner());', 'outer(cpu, cpu++);', 'int x=other();', 'return other();', 'cb(cpu);', 'if(cb(cpu)) copy();', 'if(outer(inner(cpu))) copy();']:
            with self.subTest(body=body):
                value = self.analyze('void f(int cpu, void cb(int)) { ' + body + ' copy(); }')
                self.assertEqual(value["paths"][0]["status"], "unsupported_frontier")

    def test_side_effecting_branch_and_switch_are_frontiers(self):
        for body in ['if (cpu++) copy();', 'switch(cpu) { case 1: copy(); }']:
            with self.subTest(body=body):
                value = self.analyze('void f(int cpu) { ' + body + ' }')
                self.assertEqual(value["paths"][0]["status"], "unsupported_frontier")

    def test_fake_labels_and_calls_in_comments_or_strings_are_not_paths(self):
        value = self.analyze('void f(void) { /* fake: goto other; */ char *s="set(); out:"; copy(); }')
        self.assertEqual([e["callee"] for e in self.calls(value["paths"][0])], ["copy"])

    def test_path_bound_does_not_drop_unvisited_alternatives(self):
        value = self.analyze('void f(int p) { if(p) a(); else b(); }', max_paths=1)
        self.assertEqual(value["status"], "insufficient")
        self.assertEqual(value["paths"], [])

    def test_incomplete_or_preprocessed_source_is_not_silently_repaired(self):
        for text in ['void f(void) {', '#if MODE\nvoid f(void) {}\n#endif']:
            with self.subTest(text=text):
                self.assertEqual(self.analyze(text)["status"], "insufficient")

    def candidates(self, text):
        return indexed_field_candidates({"id": "binding", "revision": "A", "path": "unit.c", "text": text,
                                         "start_line": 10, "end_line": 9 + len(text.splitlines())})

    def test_indexed_member_candidate_keeps_iteration_unknown(self):
        value = self.candidates('void f(void) { each_item(i) { p=&objects[i]; fill(&p->members,i); } }')[0]
        self.assertEqual(value["enclosing_header"]["text"], "each_item(i)")
        self.assertEqual(value["member_spelling"], "members")
        self.assertFalse(value["object_identity_proved"])
        self.assertEqual(value["iteration_reaches_target"], "unknown")

    def test_index_or_alias_change_or_intervening_write_does_not_match(self):
        for body in ['p=&objects[i]; fill(&p->members,j);', 'p=&objects[i]; fill(&q->members,i);',
                     'p=&objects[i]; p=q; fill(&p->members,i);']:
            with self.subTest(body=body):
                self.assertEqual(self.candidates('void f(void) { ' + body + ' }'), [])

    def test_binding_candidate_does_not_read_comment_or_string_code(self):
        self.assertEqual(self.candidates('void f(void) { char *s="p=&objects[i]; fill(&p->members,i);"; }'), [])

    def test_struct_or_indirect_write_cannot_reuse_value_version(self):
        for write in ['x.field=1;', 'x.field++;', '*p=1;']:
            with self.subTest(write=write):
                value = self.analyze('void f(int *p) { struct S { int field; } x; before(x); ' + write + ' after(x); }')
                path = value["paths"][0]
                self.assertEqual(path["status"], "unsupported_frontier")
                self.assertEqual([e["callee"] for e in self.calls(path)], ["before"])


if __name__ == "__main__":
    unittest.main()
