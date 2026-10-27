"""Boundary tests of the evaluator, not independent defect-detection results."""

import copy
import unittest

from linux_bug_analyze.contract_protocol import CLAIM_ROLES, SCHEMA, evaluate_contract


def fixture():
    contract = {
        "schema": SCHEMA, "id": "test.contract", "revision": "test-revision",
        "authority_kind": "consumer_inferred", "sufficient_for_correctness": False,
        "field_origins": {k: "researcher_authored" for k in
                          ("scope", "relation", "symbols", "required_claims", "authority_kind")},
        "required_claims": {role: "review." + role for role in CLAIM_ROLES},
        "symbols": {"enabled": {"type": "bool", "role": "configuration"},
                    "members": {"type": "int_set", "role": "observation"},
                    "target": {"type": "int", "role": "observation"}},
        "scope": {"symbol": "enabled"},
        "relation": {"op": "contains", "args": [{"symbol": "members"}, {"symbol": "target"}]},
    }
    refs = [{"document": "fixture", "start_line": 1, "end_line": 1}]
    ledger = {
        "revision": "test-revision", "basis": "synthetic", "context_id": "fixture-run",
        "contract_id": contract["id"], "field_origins": copy.deepcopy(contract["field_origins"]),
        "documents": {"fixture": {"context_revision": "test-revision", "path": "synthetic-only",
                                  "start_line": 1, "end_line": 1}},
        "claims": {"review." + role: {"role": role, "status": "supported",
                   "origin": "synthetic_assumption", "statement": "Declared test premise, not source proof.",
                   "references": copy.deepcopy(refs)} for role in CLAIM_ROLES},
    }
    ledger["claims"]["review.authority"]["authority_kind"] = "consumer_inferred"
    ledger["claims"]["review.authority"]["supports_requirement"] = "review.consumer_requirement"
    for role, expression in (("applicability", "scope"), ("consumer_requirement", "relation")):
        ledger["claims"]["review." + role].update(expression=copy.deepcopy(contract[expression]),
                                                 symbols=copy.deepcopy(contract["symbols"]))
    ledger["claims"]["review.object_binding"]["object_id"] = "item:7"
    for role in ("consumer_requirement", "provider_binding", "deadline_binding"):
        ledger["claims"]["review." + role]["object_id"] = "item:7"
    ledger["claims"]["review.deadline_binding"]["event_id"] = "consume"
    ledger["claims"]["review.deadline_binding"]["event_kind"] = "content_consumption"
    binding = {"object_id": "item:7", "event_id": "sample", "deadline_id": "consume"}
    ledger["claims"]["review.observation"] = {
        "role": "observation_binding", "status": "supported", "origin": "synthetic_assumption",
        "statement": "Synthetic observation context.", "references": copy.deepcopy(refs),
        "binding": {**binding, "context_id": "fixture-run", "event_kind": "sample"},
    }
    record = {
        "id": "fixture", "revision": "test-revision", "basis": "synthetic", "context_id": "fixture-run",
        "object_id": "item:7", "sample_event": "sample", "deadline_event": "consume",
        "sample_kind": "sample",
        "observation_binding": {**binding, "claim": "review.observation"}, "facts": {},
    }
    for name, value in {"enabled": True, "members": [7, 8], "target": 7}.items():
        spec = contract["symbols"][name]
        projected = {"symbol": name, "value": value, "role": spec["role"], "context_id": "fixture-run"}
        fact = {"value": value, "claim": "fact." + name}
        if spec["role"] == "observation":
            projected.update(object_id="item:7", event_id="sample")
            fact.update(object_id="item:7", event_id="sample")
        ledger["claims"]["fact." + name] = {
            "role": "fact", "status": "supported", "origin": "synthetic_assumption",
            "statement": "Synthetic value.", "references": copy.deepcopy(refs), "fact": projected,
        }
        record["facts"][name] = fact
    for claim in ledger["claims"].values():
        claim["context_id"] = "fixture-run"
    return contract, ledger, record


class ContractProtocolTests(unittest.TestCase):
    def setUp(self):
        self.contract, self.ledger, self.record = fixture()

    def evaluate(self):
        return evaluate_contract(self.contract, self.ledger, self.record, allow_synthetic=True)

    def set_value(self, name, value):
        self.record["facts"][name]["value"] = value
        self.ledger["claims"]["fact." + name]["fact"]["value"] = value

    def review_changed_relation(self):
        """Only for declared synthetic premises, never a source-semantic verifier."""
        for role, expression in (("applicability", "scope"), ("consumer_requirement", "relation")):
            self.ledger["claims"]["review." + role].update(expression=copy.deepcopy(self.contract[expression]),
                                                         symbols=copy.deepcopy(self.contract["symbols"]))

    def test_synthetic_requires_opt_in(self):
        self.assertEqual(evaluate_contract(self.contract, self.ledger, self.record)["relation_at_observation"], "insufficient")

    def test_sample_does_not_certify_deadline_or_whole_path(self):
        result = self.evaluate()
        self.assertEqual(result["relation_at_observation"], "satisfied")
        self.assertEqual(result["relation_at_deadline"], "insufficient")
        self.assertEqual(result["whole_path"], "insufficient")

    def test_non_self_member_is_evaluated_without_rewriting_predicate(self):
        self.set_value("target", 8)
        self.assertEqual(self.evaluate()["relation_at_observation"], "satisfied")
        self.set_value("target", 9)
        self.assertEqual(self.evaluate()["relation_at_observation"], "violated")

    def test_nonempty_is_not_strengthened_to_membership(self):
        self.contract["relation"] = {"op": "nonempty", "args": [{"symbol": "members"}]}
        del self.contract["symbols"]["target"]
        self.review_changed_relation()
        self.set_value("members", [99])
        self.assertEqual(self.evaluate()["relation_at_observation"], "satisfied")

    def test_set_equality_ignores_enumeration_order(self):
        self.contract["relation"] = {"op": "eq", "args": [{"symbol": "members"}, {"literal": [8, 7]}]}
        del self.contract["symbols"]["target"]
        self.review_changed_relation()
        self.assertEqual(self.evaluate()["relation_at_observation"], "satisfied")

    def test_scalar_contract_uses_same_core(self):
        self.contract["symbols"]["members"]["type"] = "int"
        self.contract["relation"] = {"op": "le", "args": [{"symbol": "target"}, {"symbol": "members"}]}
        self.review_changed_relation()
        self.set_value("members", 10)
        self.set_value("target", 11)
        self.assertEqual(self.evaluate()["relation_at_observation"], "violated")

    def test_missing_or_unknown_config_is_not_disabled(self):
        del self.record["facts"]["enabled"]
        self.assertEqual(self.evaluate()["applicability"], "insufficient")

    def test_explicit_scope_false_only_excludes_selected_contract(self):
        self.set_value("enabled", False)
        del self.record["facts"]["members"]
        self.assertEqual(self.evaluate()["relation_at_observation"], "not_applicable")
        self.assertEqual(self.evaluate()["whole_path"], "insufficient")

    def test_unrelated_config_does_not_change_applicability(self):
        self.record["facts"]["unrelated_disabled"] = {"value": False}
        self.assertEqual(self.evaluate()["relation_at_observation"], "satisfied")

    def test_missing_leaf_cannot_hide_behind_true_or(self):
        self.contract["relation"] = {"op": "or", "args": [{"literal": True}, self.contract["relation"]]}
        self.review_changed_relation()
        del self.record["facts"]["members"]
        self.assertEqual(self.evaluate()["relation_at_observation"], "insufficient")

    def test_conflict_and_model_self_approval_are_insufficient(self):
        for field, value in [("status", "conflicting"), ("status", "unknown"), ("origin", "model_proposal"),
                             ("origin", "program_projection")]:
            with self.subTest(field=field, value=value):
                old = copy.deepcopy(self.ledger["claims"]["review.authority"])
                self.ledger["claims"]["review.authority"][field] = value
                self.assertEqual(self.evaluate()["relation_at_observation"], "insufficient")
                self.ledger["claims"]["review.authority"] = old

    def test_each_required_semantic_role_is_needed(self):
        for role in CLAIM_ROLES:
            with self.subTest(role=role):
                old = self.ledger["claims"].pop("review." + role)
                self.assertEqual(self.evaluate()["relation_at_observation"], "insufficient")
                self.ledger["claims"]["review." + role] = old

    def test_same_name_different_object_or_event_is_not_bound(self):
        for key, value in [("object_id", "item:8"), ("event_id", "later")]:
            with self.subTest(key=key):
                old = self.record["facts"]["members"][key]
                self.record["facts"]["members"][key] = value
                self.assertEqual(self.evaluate()["relation_at_observation"], "insufficient")
                self.record["facts"]["members"][key] = old

    def test_unreviewed_relabeling_cannot_promote_sample_to_consumption(self):
        self.record["sample_event"] = "consume"
        self.record["observation_binding"]["event_id"] = "consume"
        for name in ("members", "target"):
            self.record["facts"][name]["event_id"] = "consume"
        self.assertEqual(self.evaluate()["relation_at_deadline"], "insufficient")

    def test_reviewed_exact_event_only_certifies_declared_relation(self):
        self.record["sample_event"] = "consume"
        self.record["sample_kind"] = "content_consumption"
        self.record["observation_binding"]["event_id"] = "consume"
        self.ledger["claims"]["review.observation"]["binding"]["event_id"] = "consume"
        self.ledger["claims"]["review.observation"]["binding"]["event_kind"] = "content_consumption"
        for name in ("members", "target"):
            self.record["facts"][name]["event_id"] = "consume"
            self.ledger["claims"]["fact." + name]["fact"]["event_id"] = "consume"
        result = self.evaluate()
        self.assertEqual(result["relation_at_deadline"], "satisfied")
        self.assertEqual(result["whole_path"], "insufficient")

    def test_pointer_event_is_not_content_consumption(self):
        self.record["sample_kind"] = "pointer_acquisition"
        self.ledger["claims"]["review.observation"]["binding"]["event_kind"] = "pointer_acquisition"
        self.assertEqual(self.evaluate()["relation_at_deadline"], "insufficient")
        self.ledger["claims"]["review.deadline_binding"]["event_kind"] = "pointer_acquisition"
        self.assertEqual(self.evaluate()["relation_at_observation"], "insufficient")

    def test_configuration_and_values_from_different_runs_cannot_mix(self):
        self.record["context_id"] = "different-run"
        self.assertEqual(self.evaluate()["relation_at_observation"], "insufficient")
        self.record["context_id"] = "fixture-run"
        self.ledger["claims"]["fact.enabled"]["fact"]["context_id"] = "different-run"
        self.assertEqual(self.evaluate()["relation_at_observation"], "insufficient")

    def test_authority_cannot_be_relabelled_as_documented(self):
        self.contract["authority_kind"] = "documented"
        self.assertEqual(self.evaluate()["relation_at_observation"], "insufficient")

    def test_reviewed_scope_and_relation_cannot_be_borrowed_for_new_expressions(self):
        original = copy.deepcopy(self.contract["relation"])
        self.contract["relation"] = {"op": "not", "args": [original]}
        self.assertEqual(self.evaluate()["relation_at_observation"], "insufficient")
        self.contract["relation"] = original
        self.contract["scope"] = {"op": "not", "args": [self.contract["scope"]]}
        self.assertEqual(self.evaluate()["applicability"], "insufficient")

    def test_contract_identity_and_field_origins_cannot_borrow_old_review(self):
        self.contract["id"] = "another.contract"
        self.assertEqual(self.evaluate()["relation_at_observation"], "insufficient")
        self.contract["id"] = "test.contract"
        self.contract["field_origins"]["relation"] = "model_proposal"
        self.assertEqual(self.evaluate()["relation_at_observation"], "insufficient")

    def test_synthetic_cannot_be_relabelled_as_runtime(self):
        self.record["basis"] = "archived_runtime"
        self.assertEqual(self.evaluate()["relation_at_observation"], "insufficient")
        self.ledger["basis"] = "archived_runtime"
        self.assertEqual(self.evaluate()["relation_at_observation"], "insufficient")

    def test_reference_or_revision_mismatch_is_insufficient(self):
        for change in ("range", "revision", "record"):
            with self.subTest(change=change):
                contract, ledger, record = fixture()
                if change == "range":
                    ledger["claims"]["review.interface"]["references"][0]["end_line"] = 2
                elif change == "revision":
                    ledger["documents"]["fixture"]["context_revision"] = "another"
                else:
                    record["revision"] = "another"
                self.assertEqual(evaluate_contract(contract, ledger, record, allow_synthetic=True)["relation_at_observation"], "insufficient")

    def test_bad_values_and_unreviewed_values_are_rejected(self):
        for value in (True, 1.5, None):
            with self.subTest(value=value):
                self.set_value("target", value)
                self.assertEqual(self.evaluate()["relation_at_observation"], "insufficient")
        self.set_value("target", 7)
        self.record["facts"]["target"]["value"] = 8
        self.assertEqual(self.evaluate()["relation_at_observation"], "insufficient")

    def test_bool_int_equivalence_cannot_forge_reviewed_fact_or_ast(self):
        for name, actual, reviewed in (("target", 1, True), ("members", [1, 8], [True, 8])):
            with self.subTest(name=name):
                contract, ledger, record = fixture()
                record["facts"][name]["value"] = actual
                ledger["claims"]["fact." + name]["fact"]["value"] = reviewed
                self.assertEqual(evaluate_contract(contract, ledger, record, allow_synthetic=True)["relation_at_observation"], "insufficient")
        self.contract["scope"] = {"op": "eq", "args": [{"symbol": "enabled"}, {"literal": True}]}
        self.review_changed_relation()
        self.ledger["claims"]["review.applicability"]["expression"]["args"][1]["literal"] = 1
        self.assertEqual(self.evaluate()["applicability"], "insufficient")

    def test_semantic_claims_must_bind_same_object_and_context(self):
        for role in ("consumer_requirement", "provider_binding", "object_binding", "deadline_binding"):
            for field, value in (("object_id", "item:8"), ("context_id", "different-run")):
                with self.subTest(role=role, field=field):
                    claim = self.ledger["claims"]["review." + role]
                    original = claim[field]
                    claim[field] = value
                    self.assertEqual(self.evaluate()["relation_at_observation"], "insufficient")
                    claim[field] = original

    def test_unsupported_temporal_operator_is_not_guessed(self):
        self.contract["relation"]["op"] = "precedes"
        self.assertEqual(self.evaluate()["relation_at_observation"], "insufficient")

    def test_labels_do_not_decide_relation(self):
        for architecture, version in (("architecture-A", "old"), ("architecture-B", "fixed")):
            with self.subTest(architecture=architecture):
                self.record.update(architecture=architecture, version_label=version)
                self.assertEqual(self.evaluate()["relation_at_observation"], "satisfied")

    def test_malformed_envelopes_return_insufficient(self):
        for malformed in (None, [], {}, {"schema": SCHEMA}):
            with self.subTest(value=malformed):
                result = evaluate_contract(malformed, self.ledger, self.record)
                self.assertEqual(result["relation_at_observation"], "insufficient")


if __name__ == "__main__":
    unittest.main()
