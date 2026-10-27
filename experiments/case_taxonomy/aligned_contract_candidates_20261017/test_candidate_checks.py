import copy
import importlib.util
import json
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location("n25_checks", Path(__file__).with_name("run_candidate_checks.py"))
checks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checks)


def encoded(value):
    return json.dumps(value, sort_keys=True).encode()


def packet(text="void worker(void) {\n  prepare();\n  notify();\n}\n"):
    config_path = "case/profiles/old_s390/kernel.config"
    config = b"CONFIG_SMP=y\n# unrelated\nCONFIG_NR_CPUS=4\n"
    identity = {"profile": "old_s390", "revision": "rev", "configuration_sha256": checks.sha(config),
                "image_sha256": "b" * 64, "preprocessed_sha256": "c" * 64}
    region = {"name": "worker", "expected_source": "/tree/worker.c", "text": text, "sha256": checks.sha(text.encode())}
    source = encoded({**identity, "functions": {"worker": region}})
    config_text = "CONFIG_SMP=y\nCONFIG_NR_CPUS=4"
    docs = [{"id": "D1", **identity, "kind": "configured_function", "function": "worker", "path": "/tree/worker.c",
             "text": text, "text_sha256": checks.sha(text.encode()),
             "source_binding": {"artifact": "regions.json", "artifact_sha256": checks.sha(source), "json_pointer": "/functions/worker/text"}},
            {"id": "D2", "profile": "old_s390", "kind": "selected_config_facts", "function": None, "path": config_path,
             "text": config_text, "text_sha256": checks.sha(config_text.encode()), "configuration_sha256": checks.sha(config),
             "source_binding": {"artifact": config_path, "artifact_sha256": checks.sha(config), "projection": "selected_lines", "source_lines": [1, 3]}}]
    p = {"schema": checks.SCHEMA, "documents": docs, "input_manifest": [{"path": "regions.json", "sha256": checks.sha(source)},
         {"path": config_path, "sha256": checks.sha(config)}], "limits": []}
    return p, {"regions.json": source, config_path: config}


def claim(first="prepare", first_line=2, second="notify", second_line=3):
    return {"id": "L1", "kind": "lexical_call_order", "profile": "old_s390", "document": "D1", "function": "worker",
            "first": {"callee": first, "line": first_line}, "second": {"callee": second, "line": second_line},
            "expected": "before", "evidence": [{"document": "D1", "start_line": 1, "end_line": 4}]}


class CandidateChecksTests(unittest.TestCase):
    def run_claim(self, c=None, text=None):
        p, artifacts = packet() if text is None else packet(text)
        return checks.check_lexical_order(claim() if c is None else c, checks.bind_documents(p, artifacts))

    def test_independent_statement_order_and_inverse_claim(self):
        r = self.run_claim()
        self.assertEqual(r["status"], "verified_lexical_order")
        self.assertFalse(r["control_flow_proved"])
        self.assertFalse(r["preparation_effect_proved"])
        c = claim(); c["expected"] = "after"
        self.assertEqual(self.run_claim(c)["status"], "not_established")

    def test_strings_and_comments_cannot_supply_call_anchor(self):
        text = 'void worker(void) {\n  puts("prepare()"); /* prepare(); */\n  notify();\n}\n'
        self.assertEqual(self.run_claim(text=text)["status"], "insufficient")

    def test_ambiguous_same_line_needs_exact_column(self):
        text = "void worker(void) {\n  prepare(); prepare();\n  notify();\n}\n"
        self.assertEqual(self.run_claim(text=text)["status"], "insufficient")
        c = claim(); c["first"]["column"] = 3
        self.assertEqual(self.run_claim(c, text)["status"], "verified_lexical_order")

    def test_declaration_definition_and_nested_expression_are_not_supported_calls(self):
        for text, c in [("void worker(void) {\n  extern void prepare(void);\n  notify();\n}\n", claim()),
                        ("void worker(void) {\n  prepare();\n  notify();\n}\n", claim("worker", 1)),
                        ("void worker(void) {\n  wrapper(prepare());\n  notify();\n}\n", claim())]:
            self.assertEqual(self.run_claim(c, text)["status"], "insufficient")

    def test_nested_gnu_argument_types_do_not_turn_outer_statement_into_declaration(self):
        text = "void worker(void) {\n  prepare(({ unsigned long tmp = 1; (void)tmp; tmp; }));\n  notify();\n}\n"
        r = self.run_claim(text=text)
        self.assertEqual(r["status"], "verified_lexical_order")
        self.assertFalse(r["control_flow_proved"])
        self.assertFalse(r["preparation_effect_proved"])

    def test_bad_reference_range_document_and_missing_anchor_coverage_reject(self):
        for evidence in [[{"document": "missing", "start_line": 1, "end_line": 2}],
                         [{"document": "D1", "start_line": True, "end_line": 3}],
                         [{"document": "D1", "start_line": 0, "end_line": 3}],
                         [{"document": "D1", "start_line": 2, "end_line": 20}],
                         [{"document": "D1", "start_line": 3, "end_line": 4}]]:
            c = claim(); c["evidence"] = evidence
            self.assertEqual(self.run_claim(c)["status"], "insufficient")
        text = "void worker(void) {\n" + "  prepare();\n" + "\n" * 25 + "  notify();\n}\n"
        p, a = packet(text)
        with self.assertRaises(checks.EvidenceError):
            checks.evidence_spans([{"document": "D1", "start_line": 1, "end_line": 25}], checks.bind_documents(p, a))

    def test_local_document_profile_function_and_source_build_profile_must_agree(self):
        for field, value in [("document", "D2"), ("profile", "old_x86"), ("function", "other")]:
            c = claim(); c[field] = value
            self.assertEqual(self.run_claim(c)["status"], "insufficient")
        p, a = packet(); p["documents"][0]["profile"] = "old_x86"
        self.assertEqual(checks.bind_documents(p, a)["D1"]["status"], "insufficient")

    def test_packet_text_and_source_digests_are_independent_identity_gates(self):
        p, a = packet(); raw = encoded(p)
        checks.packet_identity(raw, {"documents_sha256": checks.sha(raw)})
        with self.assertRaises(checks.EvidenceError):
            checks.packet_identity(raw + b" ", {"documents_sha256": checks.sha(raw)})
        for mode in ["doc", "artifact"]:
            p, a = packet()
            if mode == "doc": p["documents"][0]["text"] += "modified"
            else: a["regions.json"] += b" "
            self.assertEqual(checks.bind_documents(p, a)["D1"]["status"], "insufficient")

    def test_selected_config_lines_are_a_projection_not_a_contiguous_excerpt(self):
        p, a = packet()
        self.assertEqual(checks.bind_documents(p, a)["D2"]["status"], "source_bound")
        p["documents"][1]["source_binding"]["source_lines"] = [1, 2]
        r = checks.bind_documents(p, a)
        self.assertEqual(r["D2"]["status"], "insufficient")
        self.assertEqual(r["D1"]["status"], "insufficient")

    def test_bound_candidate_is_not_semantically_approved_or_exported_as_feature(self):
        p, a = packet()
        o = {"schema": checks.SCHEMA, "requirements": [{"id": "R1", "statement": "unproved claim", "evidence": claim()["evidence"]}],
             "architecture_paths": [], "local_checks": [], "recommended_checks": [], "limits": []}
        before = copy.deepcopy(o)
        r = checks.check_output(o, checks.bind_documents(p, a))
        self.assertEqual(r["candidate_bindings"][0]["status"], "source_bound_candidate")
        self.assertTrue(r["candidate_bindings"][0]["semantic_review_required"])
        self.assertFalse(r["formal_features_updated"])
        self.assertEqual(o, before)
        for profile in [None, "bogus"]:
            o["architecture_paths"] = [{"profile": profile, "evidence": claim()["evidence"]}]
            bound = checks.check_output(o, checks.bind_documents(p, a))
            self.assertEqual(bound["candidate_bindings"][-1]["status"], "insufficient")
        o["architecture_paths"] = [{"evidence": claim()["evidence"]}]
        self.assertEqual(checks.check_output(o, checks.bind_documents(p, a))["candidate_bindings"][-1]["status"], "insufficient")

    def test_raw_or_single_complete_fence_only_no_mixed_or_duplicate_answers(self):
        self.assertEqual(checks.parse_final(b'{"one": 1}')[1], "bare_json")
        self.assertEqual(checks.parse_final(b'```json\n{"one": 1}\n```')[1], "unique_complete_outer_json_fence")
        for raw in [b'preface {"one":1}', b'{"one":1}{"two":2}', b'```json\n{"one":1}\n```\nextra', b'{"one":1,"one":2}']:
            with self.assertRaises(ValueError):
                checks.parse_final(raw)


if __name__ == "__main__":
    unittest.main()
