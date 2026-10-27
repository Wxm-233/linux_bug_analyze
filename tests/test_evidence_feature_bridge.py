import copy
import hashlib
import json
import unittest

from linux_bug_analyze.evidence_feature_bridge import SCHEMA, project_provider_features, rules_binding


def encoded(value):
    return json.dumps(value, sort_keys=True).encode()


class EvidenceFeatureBridgeTests(unittest.TestCase):
    def setUp(self):
        self.profile = {"id": "P", "revision": "rA", "architecture": "demo", "configuration": {"sha256": "a" * 64},
                        "provider": {"signature": "original-provider", "features": {"qualification_domain": "manual-answer",
                                     "preparation_phase": "manual-answer"}, "references": ["old-handwritten-card"]},
                        "review": {"status": "reviewed", "origin": "researcher_review", "binding_sha256": "old-review"}}
        prep = {"callee": "prepare", "line": 20, "column": 2}
        notify = {"callee": "notify", "line": 30, "column": 2}
        self.entry = {"document": "E", "revision": "rA", "path": "arch/demo/start.c", "function": "start",
                      "source_sha256": "b" * 64, "status": "bounded_local_flow",
                      "calls": [{**prep, "direct": True}, {**notify, "direct": True}],
                      "paths": [{"events": [prep, notify], "guards": [], "exit": {"kind": "function_end"}}],
                      "assumptions": ["Synthetic local facts only; opaque calls return normally"]}
        declaration = {"parameter": 1, "line": 10, "column": 10}
        self.guard = {"document": "G", "revision": "rA", "path": "arch/demo/provider.c", "function": "map",
                      "source_sha256": "c" * 64, "status": "partial_forward_structure", "shadowed_names": [],
                      "parameters": [{"name": "dst", "line": 10, "column": 2}, {"name": "cpu", "line": 10, "column": 10}],
                      "paths": [{"status": "structural_terminal", "events": [{"callee": "set_member", "line": 40, "column": 2,
                        "arguments": [{"text": "cpu", "binding": "source_local_value_version", "version": "parameter", "declaration": declaration}],
                        "guards_at_event": [{"expression": "!is_prepared(cpu)", "taken": False, "line": 35, "column": 2}]}]}]}
        self.sources = [{"id": "E", "revision": "rA", "path": self.entry["path"], "function": "start",
                         "function_sha256": self.entry["source_sha256"], "full_file_sha256": "d" * 64},
                        {"id": "G", "revision": "rA", "path": self.guard["path"], "function": "map",
                         "function_sha256": self.guard["source_sha256"], "full_file_sha256": "e" * 64}]
        for source, fact in [(self.sources[0], self.entry), (self.sources[1], self.guard)]:
            source["text"] = "SYNTHETIC method fixture: " + source["function"] + "\n"
            source["function_sha256"] = hashlib.sha256(source["text"].encode()).hexdigest()
            fact["source_sha256"] = source["function_sha256"]
        self.configured = {"revision": "rA", "arch": "demo", "selected_artifacts": [{"path": "/build/.config", "sha256": "a" * 64}],
                           "original_sources": [{"revision": "rA", "path": x["path"], "sha256": x["full_file_sha256"]} for x in self.sources],
                           "helper_effects_proved": False}

    def inputs(self):
        artifacts = {"entry.json": encoded(self.entry), "guard.json": encoded(self.guard),
                     "sources.json": encoded(self.sources), "configured.json": encoded(self.configured)}
        def selector(path, pointer=""):
            return {"artifact": path, "sha256": hashlib.sha256(artifacts[path]).hexdigest(), "pointer": pointer}
        rules = {"schema": SCHEMA, "selectors": {"entry": selector("entry.json"), "entry_source": selector("sources.json", "/0"),
                 "guard": selector("guard.json"), "guard_source": selector("sources.json", "/1"), "configured": selector("configured.json")},
                 "roles": {"preparation_call": "prepare", "notification_call": "notify", "guard_parameter": "cpu",
                           "guard_effect_call": "set_member", "guard_effect_argument": 0},
                 "guard_domains": [{"predicate": "is_prepared", "trailing_arguments": [], "domain": "reviewed_prepared_domain"}]}
        rules["review"] = {"status": "reviewed", "origin": "researcher_review", "binding_sha256": rules_binding(rules),
                           "references": ["SYNTHETIC external role/normalization review; not an effect proof"]}
        return artifacts, rules

    def project(self):
        return project_provider_features(self.profile, *self.inputs())

    def test_positive_structural_projection_has_sources_but_no_effective_feature_or_auto_review(self):
        r = self.project()
        self.assertEqual(r["diagnostics"]["call_order"]["value"], "preparation_call_before_notification")
        self.assertEqual(r["diagnostics"]["eligibility_guard"]["value"], "reviewed_prepared_domain")
        self.assertEqual(r["diagnostics"]["configured_context"]["status"], "identity_bound_only")
        self.assertEqual(r["profile_candidate"]["provider"]["features"], {})
        self.assertEqual(r["profile_candidate"]["review"]["status"], "unreviewed")
        self.assertTrue(all(x["value"] is None for x in r["fields"].values()))
        self.assertTrue(all(x["evidence"] for x in r["fields"].values()))

    def test_reordered_event_array_cannot_override_unchanged_source_coordinates(self):
        self.entry["paths"][0]["events"].reverse()
        self.assertEqual(self.project()["diagnostics"]["call_order"]["reasons"], ["entry_events_not_in_source_order"])

    def test_disagreeing_branch_order_is_insufficient(self):
        other = copy.deepcopy(self.entry["paths"][0]); other["events"].reverse()
        other["events"][0]["line"], other["events"][1]["line"] = 50, 60
        self.entry["calls"].extend({**e, "direct": True} for e in other["events"])
        self.entry["paths"].append(other)
        r = self.project()["diagnostics"]["call_order"]
        self.assertEqual(r["reasons"], ["conflicting_call_order_across_paths"])
        self.assertTrue(r["evidence"])

    def test_a_path_without_preparation_call_cannot_borrow_other_branch(self):
        other = copy.deepcopy(self.entry["paths"][0]); other["events"] = other["events"][1:]
        self.entry["paths"].append(other)
        self.assertIn("missing_or_multiple_role_calls", self.project()["diagnostics"]["call_order"]["reasons"][0])

    def test_multiple_preparation_calls_do_not_choose_favorable_occurrence(self):
        duplicate = copy.deepcopy(self.entry["paths"][0]["events"][0]); duplicate["line"] = 40
        self.entry["paths"][0]["events"].append(duplicate)
        self.entry["calls"].append({**duplicate, "direct": True})
        self.assertIn("missing_or_multiple_role_calls", self.project()["diagnostics"]["call_order"]["reasons"][0])

    def test_partial_entry_or_indirect_role_call_not_complete_local_order(self):
        for mode in ["frontier", "indirect"]:
            with self.subTest(mode=mode):
                saved = copy.deepcopy(self.entry)
                if mode == "frontier": self.entry["paths"][0]["exit"]["kind"] = "frontier"
                else: self.entry["calls"][0]["direct"] = False
                self.assertEqual(self.project()["diagnostics"]["call_order"]["status"], "insufficient")
                self.entry = saved

    def test_wrong_object_parameter_version_or_shadowing_is_not_eligibility_binding(self):
        for mode in ["object", "parameter", "version", "shadow"]:
            with self.subTest(mode=mode):
                saved = copy.deepcopy(self.guard)
                arg = self.guard["paths"][0]["events"][0]["arguments"][0]
                if mode == "object": arg["text"] = "other_cpu"
                if mode == "parameter": arg["declaration"]["parameter"] = 0
                if mode == "version": arg["version"] = "write:32:1"
                if mode == "shadow": self.guard["shadowed_names"] = ["cpu"]
                self.assertEqual(self.project()["diagnostics"]["eligibility_guard"]["status"], "insufficient")
                self.guard = saved

    def test_guard_wrong_branch_polarity_does_not_invent_domain(self):
        self.guard["paths"][0]["events"][0]["guards_at_event"][0]["taken"] = True
        self.assertEqual(self.project()["diagnostics"]["eligibility_guard"]["status"], "insufficient")

    def test_unsupported_frontier_never_becomes_preparation_effect(self):
        self.guard["paths"][0]["status"] = "unsupported_frontier"
        r = self.project()
        self.assertTrue(r["diagnostics"]["eligibility_guard"]["unsupported_frontier_present"])
        self.assertEqual(r["profile_candidate"]["provider"]["features"], {})
        self.assertFalse(r["diagnostics"]["configured_context"]["helper_effects_proved"])

    def test_revision_mismatch_preserves_evidence_and_excludes_projection(self):
        self.profile["revision"] = "rB"
        r = self.project()
        self.assertEqual(r["diagnostics"]["call_order"]["reasons"], ["profile_revision_mismatch"])
        self.assertTrue(r["fields"]["preparation_phase"]["evidence"])

    def test_same_common_switches_do_not_authorize_different_config_digest(self):
        self.configured["selected_artifacts"][0]["sha256"] = "f" * 64
        r = self.project()
        self.assertEqual(r["diagnostics"]["configured_context"]["reasons"], ["configured_profile_digest_mismatch"])
        self.assertEqual(r["profile_candidate"]["provider"]["features"], {})

    def test_source_digest_or_pointer_identity_mismatch_is_not_normalized_away(self):
        for mode in ["digest", "function"]:
            saved = copy.deepcopy(self.sources)
            if mode == "digest": self.sources[0]["function_sha256"] = "f" * 64
            else: self.sources[0]["function"] = "unrelated"
            self.assertEqual(self.project()["diagnostics"]["call_order"]["status"], "insufficient")
            self.sources = saved

    def test_configured_original_source_must_match_independent_source_identity(self):
        self.configured["original_sources"][0]["sha256"] = "f" * 64
        self.assertEqual(self.project()["diagnostics"]["configured_context"]["reasons"], ["configured_original_source_mismatch"])

    def test_payload_hash_tamper_and_bad_json_selector_preserve_unknown(self):
        artifacts, rules = self.inputs()
        artifacts["entry.json"] += b" "
        r = project_provider_features(self.profile, artifacts, rules)
        self.assertEqual(r["diagnostics"]["call_order"]["reasons"], ["artifact_digest_mismatch"])
        artifacts, rules = self.inputs()
        rules["selectors"]["entry"]["pointer"] = "/unknown"
        rules["review"]["binding_sha256"] = rules_binding(rules)
        self.assertEqual(project_provider_features(self.profile, artifacts, rules)["diagnostics"]["call_order"]["reasons"], ["json_pointer_missing"])

    def test_unreviewed_or_stale_rules_cannot_supply_semantic_mapping(self):
        for mode in ["origin", "stale"]:
            artifacts, rules = self.inputs()
            if mode == "origin": rules["review"]["origin"] = "model_proposal"
            else: rules["guard_domains"][0]["domain"] = "changed-domain"
            r = project_provider_features(self.profile, artifacts, rules)
            self.assertEqual(r["reasons"], ["rules_review_missing_or_stale"])
            self.assertEqual(r["profile_candidate"]["provider"]["features"], {})

    def test_missing_artifacts_still_clear_old_answers_and_review_without_inplace_edit(self):
        before = copy.deepcopy(self.profile)
        _, rules = self.inputs()
        r = project_provider_features(self.profile, {}, rules)
        self.assertEqual(self.profile, before)
        self.assertEqual(r["profile_candidate"]["provider"]["features"], {})
        self.assertNotEqual(r["profile_candidate"]["provider"]["references"], before["provider"]["references"])
        self.assertEqual(r["profile_candidate"]["review"]["status"], "unreviewed")

    def test_ad_hoc_effect_flag_does_not_act_as_effect_certificate(self):
        self.configured["helper_effects_proved"] = True
        r = self.project()
        self.assertEqual(r["profile_candidate"]["provider"]["features"], {})
        self.assertFalse(r["diagnostics"]["configured_context"]["helper_effects_proved"])

    def test_profile_answer_lookup_is_not_a_rule_kind(self):
        artifacts, rules = self.inputs()
        rules["profile_answers"] = {"P": "ready"}
        r = project_provider_features(self.profile, artifacts, rules)
        self.assertEqual(r["reasons"], ["rules_schema_mismatch"])

    def test_different_source_architecture_cannot_borrow_same_version_config(self):
        self.profile["architecture"] = "other_architecture"
        r = self.project()
        self.assertEqual(r["diagnostics"]["call_order"]["reasons"], ["source_architecture_mismatch"])
        self.assertEqual(r["diagnostics"]["configured_context"]["reasons"], ["configured_architecture_mismatch"])

    def test_configured_binding_architecture_must_independently_match_profile(self):
        self.configured["arch"] = "different_architecture"
        self.assertEqual(self.project()["diagnostics"]["configured_context"]["reasons"], ["configured_architecture_mismatch"])

    def test_malformed_event_or_provider_returns_insufficient_instead_of_crashing(self):
        self.entry["paths"][0]["events"].append(None)
        self.assertEqual(self.project()["diagnostics"]["call_order"]["reasons"], ["entry_path_events_missing"])
        self.profile["provider"] = None
        r = self.project()
        self.assertEqual(r["reasons"], ["profile_schema_malformed"])
        self.assertEqual(r["profile_candidate"]["provider"]["features"], {})

    def test_source_text_tamper_is_detected_even_with_rebound_artifact_digest(self):
        self.sources[0]["text"] += "changed text"
        self.assertEqual(self.project()["diagnostics"]["call_order"]["reasons"], ["source_text_digest_mismatch"])

    def test_guard_coordinate_after_effect_cannot_act_as_precondition(self):
        self.guard["paths"][0]["events"][0]["guards_at_event"][0]["line"] = 41
        self.assertEqual(self.project()["diagnostics"]["eligibility_guard"]["reasons"], ["eligibility_guard_not_before_effect"])

    def test_malformed_nested_containers_return_explicit_insufficiency(self):
        cases = ["arguments", "guard_element", "guard_expression", "artifact_element", "source_element", "configuration"]
        for case in cases:
            with self.subTest(case=case):
                p, g, c = copy.deepcopy(self.profile), copy.deepcopy(self.guard), copy.deepcopy(self.configured)
                if case == "arguments": self.guard["paths"][0]["events"][0]["arguments"] = None
                if case == "guard_element": self.guard["paths"][0]["events"][0]["guards_at_event"] = [None]
                if case == "guard_expression": self.guard["paths"][0]["events"][0]["guards_at_event"][0]["expression"] = None
                if case == "artifact_element": self.configured["selected_artifacts"] = [None]
                if case == "source_element": self.configured["original_sources"] = [None]
                if case == "configuration": self.profile["configuration"] = None
                r = self.project()
                target = "eligibility_guard" if case in {"arguments", "guard_element", "guard_expression"} else "configured_context"
                self.assertEqual(r["diagnostics"][target]["status"], "insufficient")
                self.assertEqual(r["profile_candidate"]["provider"]["features"], {})
                self.profile, self.guard, self.configured = p, g, c


if __name__ == "__main__":
    unittest.main()
