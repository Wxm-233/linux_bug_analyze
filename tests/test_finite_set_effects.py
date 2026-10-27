import copy
import unittest

from linux_bug_analyze.finite_set_effects import PREMISES, interpret_set_trace


class FiniteSetEffectsTests(unittest.TestCase):
    def setUp(self):
        self.context = {"revision": "rev-A", "profile": "profile-A", "logical_bits": 4}
        self.registry = {op: {"operation": op, "context": self.context, "definition_sha256": "a" * 64,
                              "review_origin": "researcher_review", "review_id": "review-A",
                              "references": ["unit-api-review"]} for op in ("clear", "add", "copy", "test")}

    def event(self, name, *args):
        return {"summary": name, "args": list(args), "definition_sha256": "a" * 64}

    def run_trace(self, events, **kwargs):
        args = {"objects": ["tmp", "dst"], "members": ["target", "other"],
                "output": "dst", "target": "target", "assumptions": PREMISES}
        args.update(kwargs)
        return interpret_set_trace({"status": "structural_terminal", "events": events},
                                   self.registry, self.context, **args)

    def test_clear_discards_preexisting_members_before_copy(self):
        r = self.run_trace([self.event("clear", "tmp"), self.event("copy", "dst", "tmp")], initial={"tmp": ["target", "other"]})
        self.assertEqual(r["postcondition"], [])
        self.assertFalse(r["target_membership"])

    def test_singleton_is_conditional_not_runtime_or_deadline_proof(self):
        r = self.run_trace([self.event("clear", "tmp"), self.event("add", "target", "tmp"), self.event("copy", "dst", "tmp")])
        self.assertEqual(r["postcondition"], ["target"])
        self.assertTrue(r["target_membership"])
        self.assertFalse(r["premises_proved"])
        self.assertFalse(r["runtime_effects_proved"])
        self.assertEqual(r["whole_contract"], "insufficient")
        self.assertEqual(r["deadline_content"], "unknown")

    def test_setting_other_member_does_not_establish_target(self):
        r = self.run_trace([self.event("clear", "tmp"), self.event("add", "other", "tmp"), self.event("copy", "dst", "tmp")])
        self.assertEqual(r["postcondition"], ["other"])
        self.assertFalse(r["target_membership"])

    def test_unknown_initial_contents_not_assumed_empty(self):
        r = self.run_trace([self.event("add", "target", "tmp"), self.event("copy", "dst", "tmp")])
        self.assertEqual(r["status"], "insufficient")

    def test_missing_each_required_premise_rejects(self):
        for premise in PREMISES:
            with self.subTest(premise=premise):
                r = self.run_trace([self.event("clear", "dst")], assumptions=PREMISES - {premise})
                self.assertEqual(r["status"], "insufficient")
                self.assertIsNone(r["postcondition"])

    def test_hw_frontier_never_uses_prefix_as_exit_effect(self):
        r = interpret_set_trace({"status": "unsupported_frontier", "events": [self.event("clear", "dst")]},
                                self.registry, self.context, objects=["dst"], members=["target"],
                                output="dst", target="target", assumptions=PREMISES)
        self.assertEqual(r["status"], "insufficient")
        self.assertIsNone(r["postcondition"])

    def test_return_without_writing_output_does_not_borrow_initial_dst(self):
        r = self.run_trace([self.event("clear", "tmp")], initial={"dst": ["target"]})
        self.assertEqual(r["status"], "insufficient")

    def test_unknown_write_rejects(self):
        r = self.run_trace([self.event("clear", "tmp"), self.event("unreviewed", "tmp"), self.event("copy", "dst", "tmp")])
        self.assertEqual(r["status"], "insufficient")

    def test_wrong_definition_version_or_review_rejects(self):
        for change in ("hash", "context", "review"):
            with self.subTest(change=change):
                registry = copy.deepcopy(self.registry)
                if change == "hash": registry["clear"]["definition_sha256"] = "b" * 64
                elif change == "context": registry["clear"]["context"]["revision"] = "rev-B"
                else: registry["clear"]["review_origin"] = "model_proposal"
                r = interpret_set_trace({"status": "structural_terminal", "events": [self.event("clear", "dst")]},
                                        registry, self.context, objects=["dst"], members=["target"],
                                        output="dst", target="target", assumptions=PREMISES)
                self.assertEqual(r["status"], "insufficient")

    def test_self_alias_copy_outside_summary_rejects(self):
        r = self.run_trace([self.event("clear", "dst"), self.event("copy", "dst", "dst")])
        self.assertEqual(r["status"], "insufficient")

    def test_test_bit_truth_does_not_modify_the_set(self):
        r = self.run_trace([self.event("clear", "tmp"), self.event("test", "target", "tmp"),
                            self.event("add", "target", "tmp"), self.event("test", "target", "tmp"),
                            self.event("copy", "dst", "tmp")])
        self.assertEqual([x["truth"] for x in r["test_results"]], [False, True])
        self.assertEqual(r["postcondition"], ["target"])


if __name__ == "__main__":
    unittest.main()
