"""Component development fixtures, never Linux or independent oracle inputs."""
import copy
import hashlib
import unittest

from linux_bug_analyze.consumer_obligations import analyze_consumer, evaluate_consumer


SOURCE = """int examine(int target, int a, int b, int c, int x, int y, int z)
{
 int members[3] = {a, b, c};
 int relation[3] = {x, y, z};
 const int bound = 3;
 int cursor;
 int member;
 int selected = -1;
 if (bound == 1) return 77;
 for (cursor = 0; cursor < bound; cursor++) {
  member = members[cursor];
  if (member == target) continue;
  if (relation[member] == member) {
   selected = member;
   break;
  }
 }
 if (selected < 0) return 11;
 for (cursor = 0; cursor < bound; cursor++) {
  member = members[cursor];
  if (member == target) relation[member] = selected;
  if (relation[member] != selected) return 22;
 }
 return 0;
}
"""


def analyze(text=SOURCE):
    return analyze_consumer({"id": "development", "path": "development.c", "revision": "synthetic", "text": text})


def inputs(**changes):
    values = dict(target=0, a=0, b=1, c=2, x=0, y=1, z=1)
    values.update(changes)
    return values


class ConsumerObligationDevelopmentTests(unittest.TestCase):
    def test_structure_roles_coordinates_and_parameter_order_are_source_derived(self):
        result = analyze()
        self.assertEqual(result["status"], "extracted_bounded_conditions", result)
        self.assertEqual(result["parameters"], ["target", "a", "b", "c", "x", "y", "z"])
        self.assertEqual([x["kind"] for x in result["quantifiers"]],
                         ["exists_visited_search_candidate", "forall_reached_post_update_branch_not_taken"])
        self.assertEqual(result["quantifiers"][0]["coord"]["line"], 13)
        self.assertFalse(result["quantifiers"][0]["sufficiency_proved"])
        self.assertEqual(result["source_sha256"], hashlib.sha256(SOURCE.encode()).hexdigest())
        self.assertFalse(result["memory_legality_proved"])

    def test_alias_and_identifier_renaming_do_not_change_finite_return(self):
        text = SOURCE.replace("cursor", "position").replace("member", "entry").replace("selected", "choice").replace("examine", "another")
        result = evaluate_consumer(analyze(text), inputs())
        self.assertEqual(result["status"], "evaluated_under_explicit_inputs", result)
        self.assertEqual(result["return_value"], 0)

    def test_exists_is_not_all_prior_members_and_post_state_is_not_pre_state(self):
        result = evaluate_consumer(analyze(), inputs(y=2, z=2))
        self.assertEqual(result["return_value"], 0)
        self.assertEqual(result["conditions"]["search_predicates"], [False, True])
        self.assertEqual(result["conditions"]["post_update_branches_not_taken"], [True, True, True])
        self.assertEqual(result["final_state"]["relation"], [2, 2, 2])
        self.assertEqual(result["exit_class"], "tail_return")

    def test_absent_witness_and_empty_domain_keep_search_exit(self):
        for text, params in [(SOURCE, inputs(y=2, z=1)), (SOURCE.replace("bound = 3", "bound = 0"), inputs())]:
            result = evaluate_consumer(analyze(text), params)
            self.assertEqual(result["return_value"], 11)
            self.assertEqual(result["exit_class"], "search_absence_exit")
            self.assertFalse(result["conditions"]["exists_among_reached_search_predicates"])
            self.assertEqual(result["conditions"]["post_check_domain"], "not_reached")

    def test_singleton_shortcut_does_not_require_or_establish_a_witness(self):
        result = evaluate_consumer(analyze(SOURCE.replace("bound = 3", "bound = 1")), inputs())
        self.assertEqual(result["return_value"], 77)
        self.assertEqual(result["exit_class"], "early_bypass")
        self.assertIsNone(result["conditions"]["exists_among_reached_search_predicates"])
        self.assertFalse(result["conditions"]["search_reached"])

    def test_post_update_failure_is_at_a_reached_member_not_an_exists_failure(self):
        result = evaluate_consumer(analyze(), inputs(z=2))
        self.assertEqual(result["return_value"], 22)
        self.assertEqual(result["exit_class"], "member_post_update_check")
        self.assertEqual(result["conditions"]["post_update_branches_not_taken"], [True, True, False])
        self.assertTrue(result["conditions"]["exists_among_reached_search_predicates"])

    def test_first_matching_candidate_may_still_leave_sentinel_guard_true(self):
        text = SOURCE.replace("selected = member;", "selected = -1;")
        result = evaluate_consumer(analyze(text), inputs())
        self.assertEqual(result["return_value"], 11)
        self.assertTrue(result["conditions"]["exists_among_reached_search_predicates"])
        self.assertTrue(result["conditions"]["search_exit_taken"])
        self.assertEqual(result["conditions"]["search_predicates"], [True])

    def test_unvisited_checks_are_explicitly_vacuous_and_not_full_domain_proof(self):
        text = SOURCE.replace("if (member == target) relation", "if (1) continue;\n  if (member == target) relation")
        result = evaluate_consumer(analyze(text), inputs())
        self.assertEqual(result["return_value"], 0)
        self.assertEqual(result["conditions"]["post_check_domain"], "vacuous_no_reached_checks")
        self.assertTrue(result["conditions"]["all_reached_post_update_branches_not_taken"])

    def test_unknown_inputs_oob_or_uninitialized_reads_remain_insufficient(self):
        for text, params in [(SOURCE, inputs(a=3)), (SOURCE, inputs(a=True)),
                             (SOURCE.replace("int selected = -1;", "int selected = -1;\n int unknown;"), inputs())]:
            if "int unknown;" in text:
                text = text.replace("if (relation[member] == member)", "if (relation[member] == unknown)")
            result = evaluate_consumer(analyze(text), params)
            self.assertEqual(result["status"], "insufficient", result)
            self.assertTrue(result["unknown"])
            self.assertNotIn("all_reached_post_update_branches_not_taken", result["conditions"])

    def test_unsupported_control_effect_or_absence_guard_is_not_silently_removed(self):
        changes = [("member = members[cursor];", "member = opaque(cursor);"),
                   ("int member;", "int *member;"),
                   ("selected = member;", "selected = member; bound = 1;"),
                   ("selected = member;", "goto end; selected = member;"),
                   ("if (selected < 0)", "if (target < 0)"),
                   ("int selected = -1;", "int selected = 0;"),
                   ("relation[member] == member", "external[member] == member")]
        for original, changed in changes:
            with self.subTest(changed=changed):
                result = analyze(SOURCE.replace(original, changed))
                self.assertEqual(result["status"], "insufficient", result)
                self.assertFalse(result["quantifiers"])

    def test_extracted_ir_is_not_mutated_by_separate_finite_executions(self):
        analysis = analyze(); original = copy.deepcopy(analysis)
        self.assertEqual(evaluate_consumer(analysis, inputs())["return_value"], 0)
        self.assertEqual(evaluate_consumer(analysis, inputs(y=2, z=1))["return_value"], 11)
        self.assertEqual(analysis, original)

    def test_loop_bound_cannot_be_written_implicitly_by_either_index(self):
        for text in [SOURCE.replace("int cursor;", "int cursor = 3;").replace("cursor < bound", "cursor < cursor"),
                     SOURCE.replace("int cursor;", "int cursor = 3;\n int second;").replace("cursor < bound", "cursor < second").replace("int second;", "int second = 3;")]:
            if "int second" in text:
                start = text.index(" for (cursor", text.index(" if (selected < 0)"))
                text = text[:start] + text[start:].replace("cursor", "second")
            result = analyze(text)
            self.assertEqual(result["status"], "insufficient", result)
            self.assertIn("loop_bound_overlaps_index", result["reasons"])

    def test_qualifiers_and_const_parameter_writes_are_not_silent_integer_semantics(self):
        for text in [SOURCE.replace("int member;", "volatile int member;"),
                     SOURCE.replace("int member;", "_Atomic int member;"),
                     SOURCE.replace("int target", "const int target").replace("member = members[cursor];", "target = members[cursor];")]:
            with self.subTest(source=text):
                self.assertEqual(analyze(text)["status"], "insufficient")

    def test_first_bad_assignment_is_not_replaced_by_later_satisfactory_candidate(self):
        text = SOURCE.replace("int selected = -1;", "int selected = 0;").replace("selected = member;", "selected = member - 1;").replace("if (selected < 0)", "if (!selected)")
        result = evaluate_consumer(analyze(text), inputs(z=2))
        self.assertEqual(result["return_value"], 11)
        self.assertEqual(result["conditions"]["search_predicates"], [True])
        self.assertTrue(result["conditions"]["search_exit_taken"])

    def test_update_then_continue_limits_actual_check_domain_and_return_code_is_neutral(self):
        text = SOURCE.replace("if (relation[member] != selected) return 22;", "if (member == target) continue;\n  if (relation[member] != selected) return 0;")
        result = evaluate_consumer(analyze(text), inputs(z=2))
        self.assertEqual(result["return_value"], 0)
        self.assertEqual(result["exit_class"], "member_post_update_check")
        self.assertEqual(result["conditions"]["post_update_branches_not_taken"], [True, False])
        self.assertFalse(result["conditions"]["all_reached_post_update_branches_not_taken"])


if __name__ == "__main__":
    unittest.main()
