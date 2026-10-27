"""Conditional-symbolic method tests, not Linux defect or model scores."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("conditional_matcher", Path(__file__).with_name("conditional_matcher.py"))
matcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(matcher)


def fixture(kind="target_membership", post=None):
    context = {"profile": "opaque_profile", "revision": "a" * 40, "config_sha256": "b" * 64, "basis": "noninstrumented_static"}
    review = {"status": "supported", "origin": "researcher_review", "references": [{"artifact": "synthetic_development_review", "pointer": "/approved_scope"}]}
    requirement = {"id": "property", "kind": kind, "context": copy.deepcopy(context), "review": copy.deepcopy(review),
                   "consumer_purpose_review": copy.deepcopy(review), "target_symbol": "target", "mask_role": "consumer_group"}
    effect = {"context": copy.deepcopy(context), "status": "conditional_postcondition", "path_status": "structural_terminal",
              "postcondition_complete": True, "postcondition": ["target"] if post is None else post,
              "assumed_premises": list(matcher.REQUIRED_PREMISES), "target_symbol": "target", "mask_role": "consumer_group",
              "role_review": copy.deepcopy(review), "condition_guards": [{"expression": "!eligible(subject)", "taken": False, "line": 10, "column": 2}],
              "actual_branch_selected": "unknown"}
    if kind == "search_witness": requirement["search_summary"] = {
        "review": copy.deepcopy(review), "weight": "set_cardinality", "iteration": "complete_postcondition", "singleton": "bypass_search",
        "continuation_goal": "obtain_witness_before_update", "continuation_review": copy.deepcopy(review),
        "domain_condition": "no_set_bits_outside_iteration_domain", "stability_condition": "mask_and_nr_cpu_ids_stable"}
    return requirement, effect, context


class ConditionalMatcherTests(unittest.TestCase):
    def test_positive_membership_is_conditional_and_never_actual(self):
        req, effect, context = fixture()
        effect["actual_branch_selected"] = True  # an input label cannot establish runtime truth
        result = matcher.compare_guarantee(req, effect, context)
        self.assertEqual(result["status"], "conditional_compatible")
        self.assertEqual(result["actual_verdict"], "insufficient")
        self.assertEqual(result["whole_contract"], "insufficient")
        self.assertIn("actual_provider_path_selected", result["unproved_premises"])
        self.assertFalse(result["runtime_effects_proved"])

    def test_empty_denied_provider_is_conflict_not_consumer_inapplicability(self):
        req, effect, context = fixture(post=[])
        effect["condition_guards"][0]["taken"] = True
        result = matcher.compare_guarantee(req, effect, context)
        self.assertEqual(result["status"], "conditional_conflict")
        self.assertEqual(result["consumer_applicability"], "not_decided")
        self.assertEqual(result["qualification_status"], "not_evaluated")
        self.assertTrue(result["condition_guards"][0]["taken"])

    def test_singleton_bypass_is_only_search_route_even_when_target_absent(self):
        req, effect, context = fixture("search_witness", ["other"])
        result = matcher.compare_guarantee(req, effect, context)
        self.assertEqual((result["status"], result["applicability_scope"]), ("not_applicable", "search_route_only"))
        self.assertEqual(result["consumer_applicability"], "not_decided")
        req["kind"] = "target_membership"
        self.assertEqual(matcher.compare_guarantee(req, effect, context)["status"], "conditional_conflict")

    def test_empty_search_domain_conflicts_only_under_reviewed_summary(self):
        req, effect, context = fixture("search_witness", [])
        self.assertEqual(matcher.compare_guarantee(req, effect, context)["status"], "conditional_conflict")
        req.pop("search_summary")
        self.assertEqual(matcher.compare_guarantee(req, effect, context)["status"], "insufficient")

    def test_nonempty_multiple_members_are_not_a_search_witness(self):
        req, effect, context = fixture("search_witness", ["target", "other"])
        result = matcher.compare_guarantee(req, effect, context)
        self.assertEqual(result["status"], "insufficient")
        self.assertIn("core_relation_or_witness", result["reasons"][-1])

    def test_empty_domain_without_reviewed_continuation_goal_is_insufficient(self):
        for missing in ["continuation_goal", "continuation_review"]:
            with self.subTest(missing=missing):
                req, effect, context = fixture("search_witness", [])
                req["search_summary"].pop(missing)
                result = matcher.compare_guarantee(req, effect, context)
                self.assertEqual(result["status"], "insufficient")
                self.assertEqual(result["actual_verdict"], "insufficient")
        req, effect, context = fixture("search_witness", [])
        result = matcher.compare_guarantee(req, effect, context)
        self.assertIn("reviewed_continuation_goal_applies_to_this_consumer_invocation", result["unproved_premises"])
        self.assertEqual(result["whole_contract"], "insufficient")

    def test_search_domain_and_weight_summaries_cannot_be_guessed(self):
        for key, value in [("weight", "unknown"), ("iteration", "subset"), ("singleton", "normal_search")]:
            with self.subTest(key=key):
                req, effect, context = fixture("search_witness", ["target"])
                req["search_summary"][key] = value
                self.assertEqual(matcher.compare_guarantee(req, effect, context)["status"], "insufficient")

    def test_provider_domain_premise_does_not_prove_consumer_domain_or_stability(self):
        for missing in ["domain_condition", "stability_condition"]:
            with self.subTest(missing=missing):
                req, effect, context = fixture("search_witness", [])
                self.assertIn("equal_logical_domains", effect["assumed_premises"])
                req["search_summary"].pop(missing)
                self.assertEqual(matcher.compare_guarantee(req, effect, context)["status"], "insufficient")
        req, effect, context = fixture("search_witness", [])
        result = matcher.compare_guarantee(req, effect, context)
        self.assertIn("no_set_bits_outside_iteration_domain", result["unproved_premises"])
        self.assertIn("mask_and_nr_cpu_ids_stable", result["unproved_premises"])

    def test_reviews_require_supported_researcher_and_nonempty_references(self):
        for owner, key in [("req", "review"), ("req", "consumer_purpose_review"), ("effect", "role_review")]:
            for replacement in [None, {"status": "supported", "origin": "model", "references": ["x"]},
                                {"status": "candidate", "origin": "researcher_review", "references": ["x"]},
                                {"status": "supported", "origin": "researcher_review", "references": []}]:
                with self.subTest(owner=owner, key=key, replacement=replacement):
                    req, effect, context = fixture()
                    (req if owner == "req" else effect)[key] = replacement
                    self.assertEqual(matcher.compare_guarantee(req, effect, context)["status"], "insufficient")

    def test_context_mixing_or_instrumented_basis_is_not_static_compatibility(self):
        for key, value in [("profile", "other_profile"), ("revision", "c" * 40), ("config_sha256", "d" * 64), ("basis", "instrumented_runtime")]:
            for source in ["req", "effect"]:
                with self.subTest(key=key, source=source):
                    req, effect, context = fixture()
                    (req if source == "req" else effect)["context"][key] = value
                    self.assertEqual(matcher.compare_guarantee(req, effect, context)["status"], "insufficient")
        req, effect, context = fixture()
        for ctx in [req["context"], effect["context"], context]: ctx["basis"] = "instrumented_runtime"
        self.assertEqual(matcher.compare_guarantee(req, effect, context)["status"], "insufficient")
        req, effect, context = fixture()
        for ctx in [req["context"], effect["context"], context]: ctx["extra_identity"] = "not_allowed"
        self.assertEqual(matcher.compare_guarantee(req, effect, context)["status"], "insufficient")

    def test_symbol_roles_cannot_be_borrowed_from_another_subject(self):
        for key in ["target_symbol", "mask_role"]:
            with self.subTest(key=key):
                req, effect, context = fixture()
                effect[key] = "different_subject"
                self.assertEqual(matcher.compare_guarantee(req, effect, context)["status"], "insufficient")

    def test_postcondition_must_be_complete_finite_unique_symbols(self):
        for post in [None, "target", ["target", "target"], [""], [None], ["unknown"], [{"symbol": "target"}]]:
            with self.subTest(post=post):
                req, effect, context = fixture()
                effect["postcondition"] = post
                self.assertEqual(matcher.compare_guarantee(req, effect, context)["status"], "insufficient")
        req, effect, context = fixture()
        effect["postcondition_complete"] = False
        self.assertEqual(matcher.compare_guarantee(req, effect, context)["status"], "insufficient")

    def test_missing_premise_hw_frontier_or_unknown_effect_cannot_be_promoted(self):
        for change in ["missing_premise", "hw_frontier", "unknown_effect", "bad_guard", "empty_guard_list"]:
            with self.subTest(change=change):
                req, effect, context = fixture()
                if change == "missing_premise": effect["assumed_premises"].pop()
                if change == "hw_frontier": effect["path_status"] = "unsupported_frontier"
                if change == "unknown_effect": effect["status"] = "insufficient"
                if change == "bad_guard": effect["condition_guards"][0]["taken"] = "unknown"
                if change == "empty_guard_list": effect["condition_guards"] = []
                result = matcher.compare_guarantee(req, effect, context)
                self.assertEqual(result["status"], "insufficient")
                self.assertEqual(result["actual_verdict"], "insufficient")

    def test_target_membership_does_not_establish_all_member_field_consistency(self):
        req, effect, context = fixture("post_update_consistency", ["target", "other"])
        original = copy.deepcopy((req, effect, context))
        result = matcher.compare_guarantee(req, effect, context)
        self.assertEqual(result["status"], "insufficient")
        self.assertIn("field_core_state", result["reasons"][-1])
        self.assertEqual((req, effect, context), original)
        req["kind"] = "target_membership"
        result = matcher.compare_guarantee(req, effect, context)
        result["condition_guards"][0]["expression"] = "changed_output"
        self.assertNotEqual(effect["condition_guards"][0]["expression"], "changed_output")


if __name__ == "__main__": unittest.main()
