"""Conservative evidence and counterexample tests; no C/API/kernel execution."""
import copy
import json
from pathlib import Path
import unittest

from check_contract import evaluate, mock_observation, replay_recorded_vectors, validate_card


STAGE = Path(__file__).resolve().parent


class ContractGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.card = json.loads((STAGE / "contract_card.json").read_text(encoding="utf-8-sig"))
        probe = json.loads((STAGE.parent / "claude_contract_resume_20261015/probe_results.json").read_text(encoding="utf-8-sig"))
        cls.cases = {row["id"]: row for row in probe["cases"]}

    def observation(self, case="normal_two_members_with_leader"):
        return mock_observation(self.cases[case])

    def test_reviewed_card_references_are_in_recorded_source_ranges(self):
        self.assertEqual(validate_card(self.card), [])

    def test_source_range_cannot_be_relabelled_as_evidence(self):
        card = copy.deepcopy(self.card)
        card["source_references"]["interface_identity"][0]["end_line"] = 99999
        self.assertTrue(validate_card(card))

    def test_source_path_mismatch_is_rejected(self):
        card = copy.deepcopy(self.card)
        card["source_references"]["interface_identity"][0]["path"] = "different.c"
        self.assertTrue(validate_card(card))

    def test_source_position_outside_excerpt_is_rejected(self):
        card = copy.deepcopy(self.card)
        card["positions"][0]["line"] = 1
        self.assertTrue(validate_card(card))

    def test_revision_cannot_silently_change(self):
        card = copy.deepcopy(self.card)
        card["revision"] = "a052096bdd6809eeab809202726634d1ac975aa1"
        self.assertTrue(validate_card(card))

    def test_model_origin_cannot_replace_researcher_review(self):
        card = copy.deepcopy(self.card)
        card["origin"] = "external_model_output"
        result = evaluate(card, self.observation())
        self.assertEqual(result["relation"], "insufficient")

    def test_necessary_relation_cannot_be_promoted_to_sufficient(self):
        card = copy.deepcopy(self.card)
        card["authority"]["sufficient_for_correctness"] = True
        self.assertEqual(evaluate(card, self.observation())["relation"], "insufficient")

    def test_required_reference_groups_cannot_be_removed_with_declaration(self):
        card = copy.deepcopy(self.card)
        card["required_reference_groups"] = []
        del card["source_references"]["s390_provider_and_eligibility"]
        self.assertTrue(validate_card(card))

    def test_configuration_prerequisites_cannot_be_dropped(self):
        card = copy.deepcopy(self.card)
        card["required_configuration"]["common"] = []
        self.assertTrue(validate_card(card))

    def test_five_recorded_vectors_are_not_five_new_cases_or_executions(self):
        report = replay_recorded_vectors(self.card)
        self.assertEqual(report["counts"], {"recorded_logical_inputs": 5, "new_c_executions": 0, "new_kernel_runs": 0, "new_cases": 0})
        rows = {row["id"]: row for row in report["results"]}
        self.assertEqual([rows[name]["relation"] for name in self.cases], ["violated_narrow", "satisfied_narrow", "violated_narrow", "satisfied_narrow", "satisfied_narrow"])
        self.assertTrue(all(row["whole_path"] == "insufficient" for row in rows.values()))

    def test_no_warning_does_not_certify_membership(self):
        observed = self.observation("singleton_other")
        self.assertEqual(observed["warning_lines"], [])
        result = evaluate(self.card, observed)
        self.assertEqual(result["relation"], "violated_narrow")
        observed["warning_lines"] = [5779]
        self.assertEqual(evaluate(self.card, observed)["relation"], "violated_narrow")

    def test_self_does_not_certify_other_leader(self):
        result = evaluate(self.card, self.observation("self_and_other_without_leader"))
        self.assertEqual(result["relation"], "satisfied_narrow")
        self.assertEqual(result["companion_conditions"]["other_self_leader"], "violated")
        self.assertEqual(result["whole_path"], "insufficient")

    def test_singleton_other_early_exit_is_not_a_valid_self_certificate(self):
        result = evaluate(self.card, self.observation("singleton_other"))
        self.assertEqual(result["companion_conditions"]["other_self_leader"], "not_required_by_singleton_branch")
        self.assertEqual(result["relation"], "violated_narrow")

    def test_initial_target_rq_is_a_separate_condition(self):
        observed = self.observation()
        observed["initial_core_by_cpu"][1] = 0
        result = evaluate(self.card, observed)
        self.assertEqual(result["relation"], "satisfied_narrow")
        self.assertEqual(result["companion_conditions"]["target_initially_self"], "violated")

    def test_missing_initial_values_do_not_invent_a_leader(self):
        observed = self.observation()
        del observed["premises"]["initial_rq_values"]
        result = evaluate(self.card, observed)
        self.assertEqual(result["relation"], "satisfied_narrow")
        self.assertEqual(result["companion_conditions"]["other_self_leader"], "insufficient")

    def test_each_missing_interface_or_path_premise_causes_insufficient(self):
        for name in ["interface_identity", "target_argument_binding", "provider_binding", "common_consumer_deadline", "effective_path", "observation_object_binding"]:
            with self.subTest(premise=name):
                observed = self.observation()
                del observed["premises"][name]
                self.assertEqual(evaluate(self.card, observed)["relation"], "insufficient")

    def test_unreviewed_model_assertion_is_not_premise_evidence(self):
        observed = self.observation()
        observed["premises"]["provider_binding"]["origin"] = "model_candidate"
        self.assertEqual(evaluate(self.card, observed)["relation"], "insufficient")

    def test_unknown_configuration_is_insufficient_not_disabled(self):
        observed = self.observation()
        del observed["configuration"]["SCHED_TOPOLOGY"]
        self.assertEqual(evaluate(self.card, observed)["scope"], "insufficient")

    def test_explicit_disabled_selected_path_is_not_applicable(self):
        observed = self.observation()
        observed["configuration"]["SCHED_CORE"].update(value=False, raw="# CONFIG_SCHED_CORE is not set")
        result = evaluate(self.card, observed)
        self.assertEqual(result["scope"], "not_applicable")
        self.assertEqual(result["relation"], "not_applicable")

    def test_mismatched_projection_is_not_a_disabled_configuration(self):
        observed = self.observation()
        observed["configuration"]["SCHED_CORE"]["value"] = False
        self.assertEqual(evaluate(self.card, observed)["scope"], "insufficient")

    def test_unreviewed_architecture_is_unknown_not_not_applicable(self):
        observed = self.observation()
        observed["architecture"] = "arm64"
        self.assertEqual(evaluate(self.card, observed)["scope"], "insufficient")

    def test_pointer_and_claimed_exact_position_cannot_reuse_sample(self):
        for position in ["outer_pointer", "callee_pointer", "lock_iteration", "exact_consumption"]:
            with self.subTest(position=position):
                observed = self.observation()
                observed["position"] = position
                result = evaluate(self.card, observed)
                self.assertEqual(result["relation"], "insufficient")
                self.assertEqual(result["observation_tier"], "none")

    def test_extra_unreviewed_stability_assertion_cannot_promote_sample(self):
        observed = self.observation()
        observed["stable_until_iteration"] = True
        result = evaluate(self.card, observed)
        self.assertEqual(result["relation"], "satisfied_narrow")
        self.assertEqual(result["observation_tier"], "observed_sample")
        self.assertEqual(result["at_exact_consumption"], "insufficient")
        self.assertEqual(result["whole_path"], "insufficient")

    def test_invalid_mask_and_bool_cpu_do_not_become_observations(self):
        for name, value in [("target_cpu", True), ("mask_bits", -1), ("mask_bits", 1 << 4), ("cpu_bound", 0), ("target_cpu", 4)]:
            with self.subTest(field=name, value=value):
                observed = self.observation()
                observed[name] = value
                self.assertEqual(evaluate(self.card, observed)["relation"], "insufficient")

    def test_sample_normal_result_remains_limited_even_with_leader(self):
        result = evaluate(self.card, self.observation())
        self.assertEqual(result["companion_conditions"]["other_self_leader"], "satisfied")
        self.assertEqual(result["observation_tier"], "observed_sample")
        self.assertEqual(result["whole_path"], "insufficient")
        self.assertFalse(result["provenance"]["independent_case"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
