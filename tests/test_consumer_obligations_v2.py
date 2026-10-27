"""V2 development only; no new hidden oracle sources or expected records."""
import copy
import hashlib
import unittest

from linux_bug_analyze.consumer_obligations_v2 import analyze_consumer, evaluate_consumer, parsing_view
from linux_bug_analyze.consumer_obligations import Unsupported


SOURCE = """/* Commented component fixture; not Linux. */
int consume(int target, int a, int b, int c, int x, int y, int z)
{
 int members[3] = {a,b,c};
 int state[3] = {x,y,z};
 const int limit = 3;
 int chosen = -1;
 int marked = 0;
 int pos;
 if (limit == 1) return 77;
 for (pos=0; pos<limit; pos++) {
  int member = members[pos];
  if (member == target) continue;
  if (state[member] == member) {
   chosen=member;
   break;
  }
 }
 if (chosen < 0) return 11;
 for (pos=0; pos<limit; pos++) {
  int member = members[pos];
  if (member == target) state[member]=chosen;
  if (state[member] != chosen) marked=1;
 }
 if (marked) return 22;
 return 0;
}
"""


def analyze(source=SOURCE):
    return analyze_consumer({"id": "v2_dev", "path": "v2_dev.c", "revision": "development", "text": source})


def parameters(**changes):
    result = dict(target=0, a=0, b=1, c=2, x=0, y=1, z=1)
    result.update(changes)
    return result


class ConsumerV2DevelopmentTests(unittest.TestCase):
    def test_comment_scanner_preserves_offsets_crlf_tabs_unicode_and_digests(self):
        raw = '/*中\r\n文*/\tint item; //尾\r\n'
        view = parsing_view(raw)
        self.assertEqual(len(view["text"]), len(raw))
        self.assertEqual([i for i, c in enumerate(view["text"]) if c in "\r\n"], [i for i, c in enumerate(raw) if c in "\r\n"])
        self.assertEqual(view["text"].index("int item"), raw.index("int item"))
        self.assertEqual(view["source_sha256"], hashlib.sha256(raw.encode()).hexdigest())
        self.assertEqual(view["parsing_view_sha256"], hashlib.sha256(view["text"].encode()).hexdigest())

    def test_string_char_and_escapes_do_not_create_comment_spans(self):
        raw = r'''char *s="/* // \\\" */"; char c='\''; char q='"'; /* real */'''
        view = parsing_view(raw)
        self.assertEqual(len(view["comment_spans"]), 1)
        self.assertEqual(view["text"][:raw.index("/* real")], raw[:raw.index("/* real")])

    def test_illegal_lexical_translation_inputs_reject_instead_of_being_deleted(self):
        for raw in ['/* open', '"open', "'open", '"line\nnext"', "#define A 1\n", "a\\\nb", "a\\\r\nb", "??/\n", "\x00", "a\rb"]:
            with self.subTest(raw=raw), self.assertRaises(Unsupported): parsing_view(raw)
        self.assertEqual(parsing_view('"#not_a_directive" /* # */')["comment_spans"], [{"start": 19, "end": 26}])

    def test_complete_comment_and_crlf_source_keeps_raw_coordinate_identity(self):
        raw = SOURCE.replace("\n", "\r\n")
        analysis = analyze(raw)
        self.assertEqual(analysis["status"], "extracted_bounded_conditions", analysis)
        self.assertEqual(analysis["parameters"], ["target", "a", "b", "c", "x", "y", "z"])
        self.assertEqual(analysis["source_sha256"], hashlib.sha256(raw.encode()).hexdigest())
        self.assertEqual(analysis["structure"]["candidate"]["coord"]["line"], 14)
        self.assertNotEqual(analysis["parsing_view_sha256"], analysis["source_sha256"])

    def test_flag_checks_after_actual_update_have_per_iteration_write_counts(self):
        analysis = analyze(); result = evaluate_consumer(analysis, parameters())
        self.assertEqual(result["status"], "evaluated_under_explicit_inputs", result)
        self.assertEqual(result["return_value"], 0)
        self.assertEqual(result["check_observations"], [dict(iteration=0, predicate_value=False, writes_before=1),
                                                        dict(iteration=1, predicate_value=False, writes_before=0),
                                                        dict(iteration=2, predicate_value=False, writes_before=0)])
        self.assertEqual(analysis["structure"]["check_order"], "after_potential_array_write")
        self.assertNotIn("member", result["final_state"])

    def test_check_before_write_preserves_flag_even_if_later_array_becomes_consistent(self):
        before = SOURCE.replace("  if (member == target) state[member]=chosen;\n  if (state[member] != chosen) marked=1;",
                                "  if (state[member] != chosen) marked=1;\n  if (member == target) state[member]=chosen;")
        analysis = analyze(before); result = evaluate_consumer(analysis, parameters())
        self.assertEqual(result["return_value"], 22)
        self.assertEqual(result["final_state"]["state"], [1,1,1])
        self.assertEqual(result["check_observations"][0], dict(iteration=0, predicate_value=True, writes_before=0))
        self.assertEqual(analysis["structure"]["check_order"], "before_potential_array_write")

    def test_direct_return_and_arbitrary_zero_code_are_neutral_source_exits(self):
        direct = SOURCE.replace("if (state[member] != chosen) marked=1;", "if (state[member] != chosen) return 0;").replace(" if (marked) return 22;\n", "")
        result = evaluate_consumer(analyze(direct), parameters(z=2))
        self.assertEqual(result["return_value"], 0)
        self.assertEqual(result["exit_class"], "member_direct_return")
        self.assertEqual(len(result["check_observations"]), 3)
        self.assertTrue(result["check_observations"][-1]["predicate_value"])

    def test_continue_after_write_does_not_leak_write_count_to_next_iteration(self):
        text = SOURCE.replace("  if (state[member] != chosen)", "  if (member == target) continue;\n  if (state[member] != chosen)")
        result = evaluate_consumer(analyze(text), parameters())
        self.assertEqual(result["return_value"], 0)
        self.assertEqual(result["check_observations"], [dict(iteration=1, predicate_value=False, writes_before=0),
                                                        dict(iteration=2, predicate_value=False, writes_before=0)])

    def test_no_witness_empty_and_singleton_are_distinct_from_vacuous_checks(self):
        empty = evaluate_consumer(analyze(SOURCE.replace("limit = 3", "limit = 0")), parameters())
        self.assertEqual(empty["return_value"], 11)
        self.assertEqual(empty["conditions"]["check_domain"], "not_reached")
        singleton = evaluate_consumer(analyze(SOURCE.replace("limit = 3", "limit = 1")), parameters())
        self.assertEqual(singleton["return_value"], 77)
        self.assertFalse(singleton["conditions"]["search_reached"])
        skip = SOURCE.replace("  if (state[member] != chosen)", "  if (1) continue;\n  if (state[member] != chosen)")
        vacuous = evaluate_consumer(analyze(skip), parameters())
        self.assertEqual(vacuous["conditions"]["check_domain"], "vacuous_no_reached_checks")
        self.assertEqual(vacuous["check_observations"], [])

    def test_first_matching_assignment_can_still_trigger_absence_guard(self):
        text = SOURCE.replace("chosen = -1", "chosen = 0").replace("chosen=member;", "chosen=member-1;").replace("if (chosen < 0)", "if (!chosen)")
        result = evaluate_consumer(analyze(text), parameters(z=2))
        self.assertEqual(result["return_value"], 11)
        self.assertEqual(result["conditions"]["search_predicates"], [True])
        self.assertTrue(result["conditions"]["search_exit_taken"])

    def test_local_alias_reentry_sibling_scope_and_invalid_shadow_or_leak(self):
        self.assertEqual(evaluate_consumer(analyze(), parameters())["status"], "evaluated_under_explicit_inputs")
        for text in [SOURCE.replace("int pos;", "int pos; int member;"),
                     SOURCE.replace("if (chosen < 0)", "if (member < 0)"),
                     SOURCE.replace("int member = members[pos];", "int member;")]:
            with self.subTest(text=text): self.assertEqual(analyze(text)["status"], "insufficient")

    def test_flag_reset_unknown_effect_dynamic_bound_or_qualifier_remain_insufficient(self):
        changes = [("marked=1;", "marked=0;"), ("marked=1;", "marked=marked+1;"),
                   ("chosen=member;", "chosen=opaque(member);"),
                   ("int member = members[pos];", "int member = members[pos]; limit=2;"),
                   ("int pos;", "volatile int pos;"), ("const int limit = 3;", "int pos = 3;")]
        for a,b in changes:
            with self.subTest(change=b): self.assertEqual(analyze(SOURCE.replace(a,b))["status"], "insufficient")

    def test_dynamic_oob_and_unknowns_stop_without_filtering_partial_trace(self):
        for params in [parameters(a=3), parameters(a=True), {"target":0}]:
            result = evaluate_consumer(analyze(), params)
            self.assertEqual(result["status"], "insufficient")
            self.assertTrue(result["unknown"])
            self.assertNotIn("all_reached_member_branches_not_taken", result["conditions"])

    def test_no_check_does_not_invent_a_universal_candidate_and_ir_is_unchanged(self):
        text = SOURCE.replace("  if (state[member] != chosen) marked=1;\n", "").replace(" if (marked) return 22;\n", "")
        analysis = analyze(text); original = copy.deepcopy(analysis)
        self.assertEqual(len(analysis["quantifiers"]), 1)
        result = evaluate_consumer(analysis, parameters())
        self.assertEqual(result["conditions"]["check_domain"], "no_check_in_source")
        self.assertEqual(analysis, original)

    def test_const_spellings_parameter_writes_and_noninteger_literal_semantics_reject(self):
        for source in [SOURCE.replace("const int limit", "int const limit").replace("int member = members[pos];", "int member = members[pos]; limit=2;"),
                       SOURCE.replace("int chosen = -1", "const int chosen = -1"),
                       SOURCE.replace("int target", "const int target").replace("int member = members[pos];", "int member = members[pos]; target=1;"),
                       SOURCE.replace("{x,y,z}", "{'a',y,z}"), SOURCE.replace("{x,y,z}", '{"/* literal */",y,z}'),
                       "int f(void) { return 0; }"]:
            with self.subTest(source=source): self.assertEqual(analyze(source)["status"], "insufficient")


if __name__ == "__main__":
    unittest.main()
