"""Gate boundaries; synthetic attributed cards are not independent truth."""
import copy
import hashlib
import json
import unittest
from pathlib import Path

import authority_gate as gate
import contract_assertion_generator_test as development_fixture


def fixture():
    developer = development_fixture.ContractGeneratorTests()
    files = developer.files()
    plan = developer.plan(files)
    program = plan["programs"][0]
    report = program["validated_inputs"]["report"]
    findings = {field["field"]: field for field in report["findings"]}
    card = {"binding": {"revision": program["source_revision"], "source_file": program["source_file"],
        "function": program["function"], "variable": program["variable"], "payload_struct": program["payload_struct"]},
        "review": {"status": "reviewed", "reviewed_by": "synthetic-development-reviewer", "reviewer_kind": "assistant", "scope": "source_contract"},
        "fields": []}
    for field in program["fields"]:
        finding = findings[field["name"]]
        source = field["source_declaration"]
        target = finding["target_declaration"]["evidence"]
        assignment = field["assignment_evidence"]
        def evidence(value):
            return {"file": value["file"], "line": value["line"], "quote": value["text"], "sha256": value["source_sha256"]}
        facts = [
            {"kind": "source_numeric_domain", "status": "supported", "origin": "source_review",
             "value": "host_numeric", "claim": "Development reviewer explicitly assumes this declared field holds host numeric inputs; not machine-derived.", "evidence": [evidence(source)]},
            {"kind": "consumer_format", "status": "supported", "origin": "source_review",
             "value": {"endian": field["endian"], "bits": field["bits"]},
             "claim": "Development reviewer accepts this same-version field annotation as a conditional local schema.", "evidence": [evidence(target)]},
            {"kind": "applicability", "status": "supported", "origin": "source_review",
             "value": {"revision": program["source_revision"], "scope": "source_contract"},
             "claim": "Applicable only to the selected source revision and generated projection, with no runtime reachability assertion.", "evidence": [evidence(assignment)]}]
        card["fields"].append({"name": field["name"],
            "producer": {"struct": field["source_struct"], "field": field["source_field"], "type": field["source_type"]},
            "consumer": {"endian": field["endian"], "bits": field["bits"]}, "facts": facts})
    return plan, card, files


class AuthorityGateTests(unittest.TestCase):
    def run_gate(self, mutation=None):
        plan, card, files = fixture()
        if mutation:
            mutation(plan, card, files)
        return gate.evaluate(plan, card, files)

    def test_attributed_complete_card_ready_is_not_machine_or_runtime_proof(self):
        result = self.run_gate()
        self.assertEqual(result["status"], "source_contract_ready", result)
        self.assertEqual(result["reference_integrity"]["status"], "matched")
        for key in ("machine_contract_proven", "runtime_reachability_proven", "full_kernel_proven", "external_protocol_proven"):
            self.assertFalse(result[key])
        self.assertIn("assistant", result["semantic_review"]["qualification"])

    def test_matching_quotes_without_semantic_review_do_not_upgrade(self):
        result = self.run_gate(lambda p, c, f: c.pop("review"))
        self.assertEqual(result["status"], "conditional")
        self.assertEqual(result["reference_integrity"]["status"], "matched")

    def test_missing_card_plan_or_field_is_insufficient(self):
        plan, card, files = fixture()
        self.assertEqual(gate.evaluate(plan, None, files)["status"], "insufficient")
        self.assertEqual(gate.evaluate({}, card, files)["status"], "insufficient")
        self.assertEqual(self.run_gate(lambda p, c, f: c["fields"].pop())["status"], "insufficient")

    def test_wrong_identity_binding_never_selects_program(self):
        for key in ("revision", "source_file", "function", "variable", "payload_struct"):
            self.assertEqual(self.run_gate(lambda p, c, f, key=key: c["binding"].update({key: "other"}))["status"], "insufficient")

    def test_source_type_and_consumer_domain_binding_mismatch_is_insufficient(self):
        for part, key, value in (("producer", "struct", "other"), ("producer", "field", "other"),
            ("producer", "type", "__le16"), ("consumer", "endian", "be"), ("consumer", "bits", 32)):
            result = self.run_gate(lambda p, c, f, part=part, key=key, value=value: c["fields"][0][part].update({key: value}))
            self.assertEqual(result["status"], "insufficient")

    def test_report_or_program_tamper_cannot_be_reviewed_ready(self):
        result = self.run_gate(lambda p, c, f: p["programs"][0]["fields"][0].update(source_type="__le16"))
        self.assertEqual(result["status"], "insufficient")

    def test_same_revision_metadata_and_original_bytes_both_required(self):
        def revision_bad(plan, card, files):
            path = card["fields"][0]["facts"][0]["evidence"][0]["file"]
            text = files[path]
            files[path] = {"revision": "different", "text": text, "sha256": hashlib.sha256(text.encode()).hexdigest()}
        self.assertEqual(self.run_gate(revision_bad)["status"], "insufficient")
        def changed_bytes(plan, card, files):
            path = card["fields"][0]["facts"][0]["evidence"][0]["file"]
            text = files[path] + "\n"
            digest = hashlib.sha256(text.encode()).hexdigest()
            files[path] = {"revision": "synthetic", "text": text, "sha256": digest}
            card["fields"][0]["facts"][0]["evidence"][0]["sha256"] = digest
        self.assertEqual(self.run_gate(changed_bytes)["status"], "insufficient")

    def test_quote_line_hash_and_missing_source_fail_integrity(self):
        for key, value in (("quote", "unrelated nonexistent"), ("line", 999), ("line", True), ("sha256", "0" * 64)):
            result = self.run_gate(lambda p, c, f, key=key, value=value: c["fields"][0]["facts"][0]["evidence"][0].update({key: value}))
            self.assertEqual(result["status"], "insufficient")
        result = self.run_gate(lambda p, c, f: f.pop(c["fields"][0]["facts"][0]["evidence"][0]["file"]))
        self.assertEqual(result["status"], "insufficient")

    def test_partial_quote_coverage_is_not_complete_reference_integrity(self):
        result = self.run_gate(lambda p, c, f: c["fields"][0]["facts"][0].update(evidence=[]))
        self.assertEqual(result["status"], "insufficient")
        self.assertEqual(result["reference_integrity"]["status"], "insufficient")
        result = self.run_gate(lambda p, c, f: c["fields"][0]["facts"].pop())
        self.assertFalse(result["reference_integrity"]["coverage_complete"])

    def test_assumption_is_conditional_even_with_supported_and_matching_quote(self):
        self.assertEqual(self.run_gate(lambda p, c, f: c["fields"][0]["facts"][0].update(origin="assumption"))["status"], "conditional")

    def test_unknown_numeric_value_consumer_format_or_scope_cannot_upgrade(self):
        for index, value in ((0, "unknown"), (0, "encoded"), (1, {"endian": "be", "bits": 16}),
                             (2, {"revision": "synthetic", "scope": "all_hardware"})):
            self.assertEqual(self.run_gate(lambda p, c, f, index=index, value=value: c["fields"][0]["facts"][index].update(value=value))["status"], "insufficient")

    def test_normative_unknown_version_or_history_cannot_upgrade(self):
        def add_normative(plan, card, files):
            card["fields"][0]["facts"][1].update(origin="normative_review", document_version="unknown",
                historical_applicability={"status": "unknown", "claim": "not established"})
        self.assertEqual(self.run_gate(add_normative)["status"], "conditional")
        def known_doc_unknown_history(plan, card, files):
            add_normative(plan, card, files)
            card["fields"][0]["facts"][1]["document_version"] = "historical v1, 2017"
        self.assertEqual(self.run_gate(known_doc_unknown_history)["status"], "conditional")

    def test_reviewed_normative_history_preserved_but_document_not_machine_authenticated(self):
        def normative(plan, card, files):
            card["fields"][0]["facts"][1].update(origin="normative_review", document_version="historical v1, 2017",
                historical_applicability={"status": "reviewed", "claim": "Reviewer checked the applicable historical interface mode."})
        result = self.run_gate(normative)
        self.assertEqual(result["status"], "source_contract_ready")
        check = result["field_checks"][0]["facts"][1]
        self.assertEqual(check["document_version"], "historical v1, 2017")
        self.assertIn("not checked", check["normative_document_integrity"])

    def test_current_or_latest_document_alias_is_not_a_pinned_historical_version(self):
        for version in ("current", "latest", "HEAD"):
            def unpinned(plan, card, files, version=version):
                card["fields"][0]["facts"][1].update(origin="normative_review", document_version=version,
                    historical_applicability={"status": "reviewed", "claim": "Reviewer declaration cannot pin a floating version alias."})
            self.assertEqual(self.run_gate(unpinned)["status"], "conditional")

    def test_any_reported_conflict_takes_priority_over_missing_evidence_and_binding(self):
        def conflict(plan, card, files):
            card["fields"][0]["facts"][0].update(status="conflict", evidence=[])
            card["binding"]["revision"] = "wrong"
        result = self.run_gate(conflict)
        self.assertEqual(result["status"], "conflict")
        self.assertFalse(result["source_contract_ready"])
        self.assertFalse(result["machine_contract_proven"])

    def test_historical_conflict_preserved_even_when_other_fields_are_supported(self):
        def history_conflict(plan, card, files):
            card["fields"][0]["facts"][1].update(origin="normative_review", document_version="historic v1",
                historical_applicability={"status": "conflict", "claim": "Two versions imply different formats."})
        self.assertEqual(self.run_gate(history_conflict)["status"], "conflict")

    def test_missing_fact_kind_duplicate_field_and_unknown_metadata_insufficient(self):
        self.assertEqual(self.run_gate(lambda p, c, f: c["fields"][0]["facts"].pop())["status"], "insufficient")
        self.assertEqual(self.run_gate(lambda p, c, f: c["fields"].append(copy.deepcopy(c["fields"][0])))["status"], "insufficient")
        for key, value in (("status", "unknown"), ("kind", {}), ("origin", "unknown")):
            self.assertEqual(self.run_gate(lambda p, c, f, key=key, value=value: c["fields"][0]["facts"][0].update({key: value}))["status"], "insufficient")


if __name__ == "__main__":
    unittest.main()
