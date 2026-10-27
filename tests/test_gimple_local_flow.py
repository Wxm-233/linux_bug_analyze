"""Bounded scanner/local-fact development tests; no reference oracle."""
import hashlib
from pathlib import Path
import unittest

from linux_bug_analyze.gimple_local_flow import analyze_gimple


def analyze(body):
    return analyze_gimple({"id": "component", "path": "component.gimple", "revision": "development",
                           "text": "void component ()\n{\n" + body + "\n}\n"})


def kinds(result, kind):
    return [event for event in result["events"] if event["kind"] == kind]


def unresolved(result, variable, event):
    return any(row["variable"] == variable and row["use_event"] == event["id"] for row in result["unresolved_uses"])


class GimpleLocalFlowTests(unittest.TestCase):
    def test_whole_gimple_identifiers_redefinition_and_cast_dependency(self):
        result = analyze("D.123 = cpu.358_1;\na = D.123;\nD.123 = 7;\nb = (long int) D.123;")
        assignments = kinds(result, "scalar_assign")
        self.assertEqual(len(assignments), 4)
        self.assertEqual(assignments[0]["uses"], ["cpu.358_1"])
        edges = {row["use_event"]: row for row in result["dependencies"]}
        self.assertEqual(edges[assignments[1]["id"]]["definition_version"], 1)
        self.assertEqual(edges[assignments[3]["id"]]["definition_version"], 2)
        self.assertEqual(assignments[3]["assignment_kind"], "cast")
        self.assertIs(assignments[3]["cast_value_equivalence_proved"], False)
        self.assertFalse(kinds(result, "load"))

    def test_source_path_comment_and_literal_do_not_create_fields(self):
        result = analyze('[path/obj->fake.c:12:4] x = "p->bad; goto hidden;";\n'
                         '/* z = obj->ghost; */ a = p->member; // q->junk\n')
        self.assertEqual([(x["field"]["base"], x["field"]["field"]) for x in kinds(result, "load")], [("p", "member")])
        self.assertTrue(kinds(result, "opaque"))
        self.assertFalse(kinds(result, "goto"))

    def test_exact_annotation_no_inherited_comment_or_label_location(self):
        result = analyze('[alpha.c:10:2] a = p->member;\n'
                         '[alpha.c:11:2] // predicted; q->fake\n'
                         'goto done;\ndone:\n[beta.c:14:7] b = a;')
        load = kinds(result, "load")[0]
        self.assertEqual(load["source_locations"], [{"path": "alpha.c", "line": 10, "column": 2}])
        self.assertEqual(kinds(result, "goto")[0]["source_locations"], [])
        self.assertEqual(kinds(result, "label")[0]["source_locations"], [])
        self.assertEqual(kinds(result, "scalar_assign")[0]["source_locations"][0]["path"], "beta.c")

    def test_real_raw_multiline_asm_is_one_opaque_barrier(self):
        source = Path(__file__).resolve().parents[1] / "experiments/case_taxonomy/compiler_consumer_frontend_20261018/old_s390.consumer.gimple.txt"
        raw = source.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), "63b4a4ee0e0c4b9b2021fbeeae0d10f459fc42b3d6f7ce487a02a896fbff09e9")
        text = raw.decode("utf-8")
        start = text.index('__asm__ __volatile__ __inline__')
        terminal = '" :  : "i" 5762, "i" 2307, "i" 12);'
        end = text.index(terminal, start) + len(terminal)
        result = analyze('[asm.c:3:5] ' + text[start:end] + '\nx = p->member;')
        self.assertEqual(result["status"], "partial_local_facts")
        self.assertEqual(len(kinds(result, "asm")), 1)
        self.assertEqual(len(kinds(result, "load")), 1)
        self.assertFalse(kinds(result, "label"))
        self.assertEqual(kinds(result, "asm")[0]["source_locations"], [{"path": "asm.c", "line": 3, "column": 5}])
        self.assertIn('.section .rodata.str,"aMS"', kinds(result, "asm")[0]["raw"])

    def test_asm_quoted_terminator_and_unclosed_asm(self):
        result = analyze('asm("literal ); and p->fake" : : "r" (x));\ny = p->member;')
        self.assertEqual(len(kinds(result, "asm")), 1)
        self.assertEqual(len(kinds(result, "load")), 1)
        bad = analyze('asm("unterminated\nx = p->member;')
        self.assertEqual(bad["status"], "insufficient_lexical_input")
        self.assertFalse(bad["events"])

    def test_load_compare_cast_chain_and_versions_are_same_region(self):
        result = analyze('p = origin;\nx = p->member;\ny = p != x;\nz = (int) y;')
        events = result["events"]
        load = kinds(result, "load")[0]
        compare = next(x for x in events if x["defines"] == ["y"])
        cast = next(x for x in events if x["defines"] == ["z"])
        self.assertTrue(any(d["definition_event"] == load["id"] and d["use_event"] == compare["id"] for d in result["dependencies"]))
        self.assertTrue(any(d["definition_event"] == compare["id"] and d["use_event"] == cast["id"] for d in result["dependencies"]))
        self.assertEqual(load["region"], cast["region"])
        self.assertIs(result["contract_or_alias_proved"], False)

    def test_branch_label_join_and_explicit_targets_do_not_propagate(self):
        result = analyze('a = p;\nif (a != 0B) goto <D.1>; else goto <D.2>;\n'
                         '<D.1>:\nb = a;\ngoto done;\n<D.2>:\na = q;\ndone:\nc = a;')
        assigns = kinds(result, "scalar_assign")
        self.assertTrue(unresolved(result, "a", next(x for x in assigns if x["defines"] == ["b"])))
        self.assertTrue(unresolved(result, "a", next(x for x in assigns if x["defines"] == ["c"])))
        self.assertEqual(len(result["control_edges"]), 3)
        self.assertTrue(all(x["resolution"] == "unique_displayed_label" for x in result["control_edges"]))
        self.assertTrue(all(x["reachability_proved"] is False for x in result["control_edges"]))

    def test_call_arguments_bind_but_result_remains_unknown(self):
        result = analyze('a = p;\nx = helper (a, &flags);\ny = x;\nz = a;')
        call = kinds(result, "call")[0]
        self.assertEqual(call["call"]["callee"], "helper")
        self.assertTrue(any(d["use_event"] == call["id"] and d["variable"] == "a" for d in result["dependencies"]))
        self.assertTrue(unresolved(result, "x", next(x for x in result["events"] if x["defines"] == ["y"])))
        self.assertTrue(unresolved(result, "a", next(x for x in result["events"] if x["defines"] == ["z"])))
        self.assertIs(call["result_unknown"], True)

    def test_address_argument_does_not_read_the_addressed_scalar_value(self):
        result = analyze('flags = 1;\na = origin;\nhelper (&flags, a);\nx = flags;')
        call = kinds(result, "call")[0]
        self.assertEqual(call["address_operands"], ["flags"])
        self.assertEqual(call["uses"], ["a"])
        self.assertFalse(any(d["use_event"] == call["id"] and d["variable"] == "flags" for d in result["dependencies"]))
        self.assertTrue(unresolved(result, "flags", next(e for e in result["events"] if e["defines"] == ["x"])))

    def test_memory_store_asm_and_scope_kill_previous_scalar_bindings(self):
        for boundary in ['p->member = a;', 'asm("none");', '{\nint inner;\n}', 'mystery ? a : b;']:
            with self.subTest(boundary=boundary):
                result = analyze('a = x;\n' + boundary + '\nb = a;')
                b = next(x for x in result["events"] if x["defines"] == ["b"])
                self.assertTrue(unresolved(result, "a", b))

    def test_multiple_object_bindings_and_store_are_not_same_object_proof(self):
        result = analyze('p = first;\nx = p->member;\np = second;\np->member = x;\ny = p->member;')
        loads = kinds(result, "load")
        self.assertEqual(len(loads), 2)
        store = kinds(result, "store")[0]
        self.assertEqual(store["field"], {"base": "p", "field": "member", "access": "write"})
        self.assertTrue(unresolved(result, "p", loads[1]))
        self.assertIs(result["contract_or_alias_proved"], False)

    def test_diagnostic_identifiers_clobber_try_finally_are_not_return(self):
        result = analyze('try {\n__ret_warn_on = p != q;\n}\nfinally {\nflags = {CLOBBER(eol)};\n}')
        self.assertFalse(kinds(result, "return"))
        self.assertEqual(len(kinds(result, "clobber")), 1)
        self.assertEqual(len(kinds(result, "try")), 1)
        self.assertEqual(len(kinds(result, "finally")), 1)

    def test_unsupported_effect_expressions_and_literals_remain_opaque(self):
        for expression in ['', '"text"', "'c'", 'x++', '--x', '*p', '(fn)(x)', 'outer(inner(x))']:
            with self.subTest(expression=expression):
                result = analyze('a = origin;\nx = ' + expression + ';\ny = a;')
                x = [e for e in result["events"] if e["defines"] == ["x"]]
                self.assertFalse(x)
                self.assertTrue(kinds(result, "opaque"))
                self.assertTrue(unresolved(result, "a", next(e for e in result["events"] if e["defines"] == ["y"])))

    def test_missing_and_duplicate_labels_preserve_unresolved_targets(self):
        result = analyze('goto missing;\ngoto again;\nagain:\na = 0;\nagain:\nb = 1;')
        self.assertEqual(len(result["control_edges"]), 2)
        self.assertTrue(all(e["target_event"] is None for e in result["control_edges"]))

    def test_crlf_unicode_offsets_and_malformed_input(self):
        source = 'void f ()\r\n{\r\n[目录/a.c:9:2] a = p->member;\r\n}\r\n'
        result = analyze_gimple({"id": "coords", "path": "coords", "revision": "dev", "text": source})
        load = kinds(result, "load")[0]
        self.assertEqual(source[load["start_offset"]:load["end_offset"]], load["raw"])
        self.assertEqual(load["source_locations"][0]["path"], "目录/a.c")
        for bad in ['void f(){ x = (a; }', 'void f(){ x = "unterminated; }', 'void f(){ /* unclosed }']:
            with self.subTest(bad=bad):
                result = analyze_gimple({"text": bad})
                self.assertEqual(result["status"], "insufficient_lexical_input")
                self.assertFalse(result["events"])


if __name__ == "__main__":
    unittest.main()
