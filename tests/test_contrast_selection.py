import copy
import unittest

from linux_bug_analyze.contrast_selection import (
    SCHEMA, contract_binding, metadata_sha256, profile_binding, select_contrasts,
)


def review(binding):
    return {"status": "reviewed", "origin": "researcher_review", "binding_sha256": binding,
            "references": ["synthetic-method-test:external-review"]}


def contract():
    c = {"schema": SCHEMA, "id": "C", "purpose": "initialize_common_consumer",
         "consumer": {"interface": "shared_api", "operation": "first_read",
                      "stage": "stage-S", "object_role": "target_state"},
         "execution": {"cpus": 2, "mode": "initialization"},
         "required_config": {"CONFIG_COMMON": "y", "CONFIG_LIMIT": "4"},
         "contrast_features": ["qualification_domain", "preparation_phase"]}
    c["review"] = review(contract_binding(c))
    return c


def profile(name="P1", arch="arch-A", *, revision="version-X", qualification="ready", phase="before"):
    c = contract()
    values = {"CONFIG_COMMON": "y", "CONFIG_LIMIT": "4"}
    p = {"id": name, "revision": revision, "architecture": arch, "purpose": c["purpose"],
         "consumer": copy.deepcopy(c["consumer"]), "execution": copy.deepcopy(c["execution"]),
         "configuration": {"sha256": "a" * 64, "autoconf_sha256": "b" * 64, "values": values,
                           "facts_sha256": metadata_sha256(values), "verification": "config_and_autoconf_verified"},
         "availability": {"build_status": "archived_built", "build_record_sha256": "c" * 64,
                          "image_sha256": "d" * 64, "adapter": "adapter-A", "adapter_stage": "stage-S",
                          "references": ["synthetic-build-and-adapter-evidence"]},
         "legality": "legal",
         "provider": {"signature": "provider-" + name,
                      "features": {"qualification_domain": qualification, "preparation_phase": phase},
                      "references": ["synthetic-provider-semantic-review"]}, "cost": 1}
    p["review"] = review(profile_binding(p))
    return p


def renew(p):
    p["review"] = review(profile_binding(p))
    return p


class ContrastSelectionTests(unittest.TestCase):
    def setUp(self):
        self.contract = contract()
        self.a = profile()
        self.b = profile("P2", "arch-B", qualification="online", phase="after")

    def select(self, pool=None, **kwargs):
        options = {"max_pairs": 1, "max_cost": 2, "seed": "test-seed"}
        options.update(kwargs)
        return select_contrasts(self.contract, [self.a, self.b] if pool is None else pool, **options)

    def excluded(self, result, reason):
        return any(reason in d["reasons"] for d in result["profiles"] + result["pair_decisions"])

    def test_selects_same_purpose_version_and_stage_with_reviewed_semantic_difference(self):
        r = self.select()
        self.assertEqual(r["status"], "selected")
        self.assertEqual(r["pairs"][0]["different_features"], ["qualification_domain", "preparation_phase"])
        self.assertEqual(r["runtime_truth"], "not_evaluated")
        self.assertEqual(r["spent_cost"], 2)

    def test_unknown_illegal_and_inactive_are_not_normal(self):
        for status in ["unknown", "illegal", "inactive", None]:
            with self.subTest(status=status):
                p = copy.deepcopy(self.b)
                p["legality"] = status
                r = self.select([self.a, renew(p)])
                self.assertFalse(r["pairs"])
                self.assertTrue(self.excluded(r, "legality_not_established"))

    def test_different_purpose_rejected_even_with_shared_api(self):
        self.b["purpose"] = "different_use"
        r = self.select([self.a, renew(self.b)])
        self.assertTrue(self.excluded(r, "different_purpose"))

    def test_each_consumer_dimension_must_match(self):
        for key in self.b["consumer"]:
            with self.subTest(key=key):
                p = copy.deepcopy(self.b)
                p["consumer"][key] += "-other"
                self.assertTrue(self.excluded(self.select([self.a, renew(p)]), "different_consumer_or_stage"))

    def test_execution_context_must_match_including_types(self):
        for value in [1, True, "2"]:
            p = copy.deepcopy(self.b)
            p["execution"]["cpus"] = value
            self.assertTrue(self.excluded(self.select([self.a, renew(p)]), "different_execution_context"))

    def test_different_revision_never_compares_old_with_fixed(self):
        self.b["revision"] = "version-Y"
        self.assertTrue(self.excluded(self.select([self.a, renew(self.b)]), "different_revision"))

    def test_same_architecture_rejected(self):
        self.b["architecture"] = self.a["architecture"]
        self.assertTrue(self.excluded(self.select([self.a, renew(self.b)]), "same_architecture"))

    def test_arch_name_and_provider_signature_alone_do_not_make_contrast(self):
        self.b["provider"]["features"] = copy.deepcopy(self.a["provider"]["features"])
        self.assertNotEqual(self.a["provider"]["signature"], self.b["provider"]["signature"])
        self.assertTrue(self.excluded(self.select([self.a, renew(self.b)]), "no_reviewed_semantic_contrast"))

    def test_missing_contrast_feature_cannot_be_inferred_from_other_arch(self):
        del self.b["provider"]["features"]["preparation_phase"]
        self.assertTrue(self.excluded(self.select([self.a, renew(self.b)]), "provider_semantics_incomplete"))

    def test_effective_config_not_requested_config(self):
        self.b["configuration"]["values"]["CONFIG_COMMON"] = "n"
        self.b["configuration"]["facts_sha256"] = metadata_sha256(self.b["configuration"]["values"])
        self.assertTrue(self.excluded(self.select([self.a, renew(self.b)]), "required_configuration_not_satisfied"))

    def test_unverified_missing_or_tampered_config_excluded(self):
        for modification in ["verification", "missing", "digest", "facts"]:
            with self.subTest(modification=modification):
                p = copy.deepcopy(self.b)
                if modification == "verification": p["configuration"]["verification"] = "requested"
                if modification == "missing": del p["configuration"]["autoconf_sha256"]
                if modification == "digest": p["configuration"]["sha256"] = "not-a-digest"
                if modification == "facts": p["configuration"]["values"]["CONFIG_LIMIT"] = "8"
                self.assertTrue(self.excluded(self.select([self.a, renew(p)]), "actual_configuration_not_verified"))

    def test_missing_or_wrong_adapter_stage_excluded(self):
        for key, value in [("build_status", "requested"), ("adapter", ""), ("adapter_stage", "later")]:
            p = copy.deepcopy(self.b)
            p["availability"][key] = value
            self.assertTrue(self.excluded(self.select([self.a, renew(p)]), "build_or_adapter_not_established"))

    def test_semantic_change_requires_new_bound_external_review(self):
        self.b["provider"]["features"]["preparation_phase"] = "other"
        self.assertTrue(self.excluded(self.select(), "profile_review_missing_or_mismatched"))

    def test_borrowed_review_from_another_profile_is_rejected(self):
        self.b["review"] = copy.deepcopy(self.a["review"])
        self.assertTrue(self.excluded(self.select(), "profile_review_missing_or_mismatched"))

    def test_model_only_review_not_accepted_as_external_semantic_review(self):
        self.b["review"]["origin"] = "model_proposal"
        self.assertTrue(self.excluded(self.select(), "profile_review_missing_or_mismatched"))

    def test_contract_change_requires_new_review(self):
        self.contract["contrast_features"].reverse()
        self.assertEqual(self.select()["error"], "contract_review_missing_or_mismatched")

    def test_feature_order_is_explicit_not_number_of_differences(self):
        a = profile("A", "a")
        b = profile("B", "b", qualification="other", phase="before")
        c = profile("C", "c", qualification="ready", phase="after")
        r = self.select([a, b, c])
        self.assertIn("qualification_domain", r["pairs"][0]["different_features"])
        self.assertEqual(r["pairs"][0]["priority_bits"][0], 1)

    def test_count_and_cost_budgets_record_each_exclusion(self):
        c = profile("P3", "arch-C", qualification="different", phase="middle")
        r = self.select([self.a, self.b, c])
        self.assertEqual(len(r["pairs"]), 1)
        self.assertEqual(sum("pair_count_budget" in p["reasons"] for p in r["pair_decisions"]), 2)
        r = self.select(max_cost=1)
        self.assertFalse(r["pairs"])
        self.assertTrue(self.excluded(r, "cost_budget"))

    def test_cost_rejection_does_not_prevent_a_later_affordable_pair(self):
        a = profile("A", "a", qualification="q1", phase="p1")
        b = profile("B", "b", qualification="q2", phase="p2")
        c = profile("C", "c", qualification="q1", phase="p3")
        b["cost"] = 3
        renew(b)
        r = self.select([a, b, c], max_cost=2)
        self.assertEqual({r["pairs"][0]["left"], r["pairs"][0]["right"]}, {"A", "C"})

    def test_bool_zero_negative_and_noninteger_budgets_costs_rejected(self):
        for value in [True, 0, -1, 1.5]:
            self.assertEqual(self.select(max_pairs=value)["status"], "invalid_input")
            self.assertEqual(self.select(max_cost=value)["status"], "invalid_input")
            p = copy.deepcopy(self.b)
            p["cost"] = value
            self.assertTrue(self.excluded(self.select([self.a, p]), "invalid_cost"))

    def test_profile_order_does_not_change_selection_or_budget(self):
        c = profile("P3", "arch-C", qualification="third", phase="after")
        forward = self.select([self.a, self.b, c])
        backward = self.select([c, self.b, self.a])
        self.assertEqual(forward, backward)

    def test_outcome_fields_and_outcome_features_are_rejected(self):
        for key in ["expected_violation", "WARN", "failure_label", "old_fixed"]:
            p = copy.deepcopy(self.b)
            p[key] = True
            self.assertTrue(self.excluded(self.select([self.a, p]), "profile_schema_mismatch"))
        self.contract["contrast_features"] = ["expected_violation"]
        self.contract["review"] = review(contract_binding(self.contract))
        self.assertEqual(self.select()["error"], "invalid_contrast_features")

    def test_duplicate_ids_and_oversized_pool_rejected(self):
        self.assertEqual(self.select([self.a, copy.deepcopy(self.a)])["error"], "missing_or_duplicate_profile_id")
        self.assertEqual(self.select([self.a] * 129)["error"], "invalid_pool_size")

    def test_inputs_are_not_mutated(self):
        before = copy.deepcopy([self.contract, self.a, self.b])
        self.select()
        self.assertEqual(before, [self.contract, self.a, self.b])

    def test_cost_or_id_change_requires_new_review(self):
        for field, value in [("cost", 2), ("id", "different-identity")]:
            p = copy.deepcopy(self.b)
            p[field] = value
            self.assertTrue(self.excluded(self.select([self.a, p]), "profile_review_missing_or_mismatched"))

    def test_identity_paths_and_signatures_cannot_be_named_semantic_features(self):
        for key in ["architecture", "arch", "source_path", "provider_signature", "revision"]:
            self.contract["contrast_features"] = [key]
            self.contract["review"] = review(contract_binding(self.contract))
            self.assertEqual(self.select()["error"], "invalid_contrast_features")

    def test_pure_whitespace_scope_or_identity_does_not_count_as_evidence(self):
        for field in ["purpose", "architecture"]:
            p = copy.deepcopy(self.b)
            p[field] = " "
            self.assertFalse(self.select([self.a, renew(p)])["pairs"])
        for key in self.contract["consumer"]:
            c = contract()
            c["consumer"][key] = " "
            c["review"] = review(contract_binding(c))
            r = select_contrasts(c, [self.a, self.b], max_pairs=1, max_cost=2, seed="S")
            self.assertEqual(r["error"], "invalid_contract_scope")

    def test_known_architecture_aliases_do_not_make_cross_architecture_pair(self):
        for first, second in [("s390", "s390x"), ("x86_64", "amd64"), ("arm64", "aarch64")]:
            a, b = copy.deepcopy(self.a), copy.deepcopy(self.b)
            a["architecture"], b["architecture"] = first, second
            self.assertTrue(self.excluded(self.select([renew(a), renew(b)]), "same_architecture"))


if __name__ == "__main__":
    unittest.main()
