"""Small offline boundary tests; mutations are in memory, not new observations."""
import json
import unittest

import check_contract as gate


def load_request(view="pair"):
    return json.loads((gate.MODEL / "requests" / ("startup_target_" + view + ".json")).read_text(encoding="utf-8-sig"))


def load_final(view="pair"):
    return json.loads((gate.MODEL / "proposals" / ("startup_target_" + view + ".json")).read_text(encoding="utf-8-sig"))


def fixture():
    return json.loads((gate.HERE / "contract_card.json").read_text(encoding="utf-8-sig"))


class GateTests(unittest.TestCase):
    def test_model_pair_baseline(self):
        result = gate.evaluate_model(load_request(), load_final())
        self.assertEqual(result["classification"], "cross_arch_source_candidate")
        self.assertEqual(result["status"], "candidate_only")
        self.assertTrue(result["findings"][0]["conditional_configuration_not_cited"])
        self.assertFalse(result["findings"][0]["structured_predicate_supplied"])

    def test_model_ablation_baseline(self):
        result = gate.evaluate_model(load_request("ablated"), load_final("ablated"))
        self.assertEqual(result["original_scope"], "cross_arch_candidate")
        self.assertEqual(result["classification"], "local_candidate")
        self.assertIn("candidate.provider.s390", result["findings"][0]["missing"])

    def test_card_baseline(self):
        result = gate.evaluate_contract_card(fixture(), load_request())
        self.assertTrue(result["eligible_for_archived_replay"])
        self.assertFalse(result["validated_detector"])

    def test_missing_four_layers(self):
        for layer in ("providers", "configuration", "common_consumer", "predicate"):
            with self.subTest(layer=layer):
                card = fixture()
                del card["evidence"][layer]
                self.assertEqual(gate.evaluate_contract_card(card, load_request())["status"], "insufficient")

    def test_missing_predicate_never_inferred(self):
        card = fixture()
        del card["predicate"]
        result = gate.evaluate_contract_card(card, load_request())
        self.assertEqual(result["status"], "candidate_only")
        self.assertFalse(result["eligible_for_archived_replay"])

    def test_bad_reference_document_or_bounds(self):
        for field, val in (("document", "NO_DOCUMENT"), ("end_line", 999999), ("start_line", True)):
            with self.subTest(field=field):
                proposal = load_final()
                proposal["findings"][0]["evidence"][0][field] = val
                self.assertEqual(gate.evaluate_model(load_request(), proposal)["status"], "insufficient")
                card = fixture()
                card["evidence"]["predicate"][0][field] = val
                self.assertEqual(gate.evaluate_contract_card(card, load_request())["status"], "insufficient")

    def test_revision_and_origin_binding(self):
        for field, val in (("revision", "0" * 40), ("origin", "model_generated"), ("request_id", "other")):
            with self.subTest(field=field):
                card = fixture()
                card[field] = val
                self.assertEqual(gate.evaluate_contract_card(card, load_request())["status"], "insufficient")

    def test_unsupported_predicate_phase_object(self):
        for field, val in (("operator", "nonempty"), ("operator", "weight_equals_one"),
                           ("phase", "final"), ("object", "different_cpu"), ("member", "cpu0")):
            with self.subTest(field=field):
                card = fixture()
                card["predicate"][field] = val
                self.assertEqual(gate.evaluate_contract_card(card, load_request())["status"], "insufficient")

    def test_wrong_scope_cpu_or_mode(self):
        for field, val in (("target_cpu", 0), ("boot", "hotplug"), ("s390_mode", "HW"), ("cpus", 4)):
            with self.subTest(field=field):
                card = fixture()
                card["scope"][field] = val
                self.assertEqual(gate.evaluate_contract_card(card, load_request())["status"], "insufficient")

    def test_configuration_missing_vs_disabled(self):
        for replacement, expected in (("CONFIG_OTHER=y", "insufficient"),
                                       ("# CONFIG_SCHED_CORE is not set", "not_applicable")):
            with self.subTest(expected=expected):
                request = load_request()
                for doc in request["documents"]:
                    if doc["id"] == "C_x86":
                        doc["text"] = doc["text"].replace("CONFIG_SCHED_CORE=y", replacement)
                result = gate.evaluate_contract_card(fixture(), request)
                self.assertEqual(result["status"], expected)
                self.assertFalse(result["eligible_for_archived_replay"])

    def test_architecture_configuration_key_binding(self):
        request = load_request()
        for doc in request["documents"]:
            if doc["id"] == "C_x86":
                doc["text"] = doc["text"].replace("CONFIG_X86_64=y", "CONFIG_GENERIC=y")
        self.assertEqual(gate.evaluate_contract_card(fixture(), request)["status"], "insufficient")

    def test_omitting_arch_citation_downgrades(self):
        proposal = load_final()
        proposal["findings"][0]["evidence"] = [r for r in proposal["findings"][0]["evidence"]
                                             if not r["document"].startswith("S_s390_")]
        self.assertEqual(gate.evaluate_model(load_request(), proposal)["classification"], "local_candidate")

    def test_weight_one_other_is_logical_counterexample(self):
        # This set is not asserted reachable; it only refutes a logical implication.
        self.assertEqual((1).bit_count(), 1)
        self.assertFalse(gate.interpret_registered_predicate(gate.REGISTERED, mask=1, target_cpu=1))
        self.assertTrue(gate.interpret_registered_predicate(gate.REGISTERED, mask=2, target_cpu=1))

    def test_explicit_authority_and_provenance(self):
        for section, field, value in (("provenance", "automatic_model_derivation", True),
                                      ("provenance", "automatic_model_derivation", None),
                                      ("authority", "kind", "model_assertion")):
            with self.subTest(section=section, value=value):
                card = fixture()
                card[section][field] = value
                self.assertEqual(gate.evaluate_contract_card(card, load_request())["status"], "insufficient")

    def test_early_update_online_guard_logical_only(self):
        # Literal old provider guard: moving the call earlier does not change membership eligibility.
        online, target, mask = False, 1, set()
        if online:
            mask.add(target)
        self.assertFalse(target in mask)

    def test_missing_or_wrong_cpu_first_event_rejects_judgment(self):
        # In-memory rejection test; originals are never edited, no new run is claimed.
        replay = gate.load_replay()
        material = replay.metadata("old_s390")
        raw = material["raw"]
        edits = [replay.re.sub(r"^.*R4 phase=lock_snapshot cpu=1[^\n]*\n", "", raw, flags=replay.re.M),
                 raw.replace("R4 phase=lock_snapshot cpu=1", "R4 phase=lock_snapshot cpu=0")]
        for changed in edits:
            self.assertNotEqual(raw, changed)
            result = replay.replay(material, changed)
            self.assertEqual(result["status"], "insufficient")
            self.assertIsNone(result["predicates"])


if __name__ == "__main__":
    unittest.main()
