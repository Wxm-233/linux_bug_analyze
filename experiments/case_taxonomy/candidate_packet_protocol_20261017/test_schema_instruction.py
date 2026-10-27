"""Synthetic connectivity only: no E/F source, outputs, repair, or runtime."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


formatting = load("n27_format", HERE / "schema_instruction.py")
checks = load("n27_frozen_v2", HERE.parent / "new_input_contract_trial_20261017/run_raw_candidate_checks.py")


def packet(case="Q", text=None, doc_id="D1"):
    text = text or formatting.EXAMPLE_TEXT
    parent = "d" * 40
    digest = checks.sha(text.encode())
    source = {"id": "synthetic", "case": case, "revision": parent, "path": "synthetic/format.c",
              "text": text, "sha256": digest, "status": "collected", "material_group": case + "_parent"}
    artifact = json.dumps({"documents": [source]}).encode()
    sha = checks.sha(artifact)
    doc = {"id": doc_id, "case": case, "parent": parent, "revision": parent, "profile": case + "_parent",
           "kind": "raw_source_file", "function": None, "path": source["path"], "text": text,
           "file_sha256": digest, "text_sha256": digest, "configuration_sha256": None,
           "image_sha256": None, "preprocessed_sha256": None,
           "source_binding": {"artifact": "synthetic.json", "artifact_sha256": sha, "json_pointer": "/documents/0/text"}}
    return {"schema": checks.SCHEMA, "case_parents": {case: parent}, "documents": [doc],
            "input_manifest": [{"path": "synthetic.json", "sha256": sha}]}, {"synthetic.json": artifact}


def example(text=None):
    seed, _ = packet()
    description = formatting.schema_description(seed)
    output = description["synthetic_example"]["output"]
    p, artifacts = packet(text=text, doc_id=formatting.EXAMPLE_ID)
    return output, checks.bind_documents(p, artifacts)


class FormatProtocolTests(unittest.TestCase):
    def test_material_group_is_instantiated_from_each_packet_without_source_inference(self):
        for case in ["Q", "Trial_2"]:
            p, _ = packet(case)
            d = formatting.schema_description(p)
            self.assertEqual(d["required_material_group"], case + "_parent")
            self.assertEqual(d["allowed_document_ids"], ["D1"])
            self.assertEqual({item["profile"] for key in ["architecture_paths", "local_checks"]
                              for item in d["synthetic_example"]["output"][key]}, {case + "_parent"})
            self.assertFalse(d["material_group_is_architecture_or_configuration_proof"])

    def test_missing_mixed_ambiguous_or_reserved_identity_rejects(self):
        p, _ = packet()
        for mode in ["missing", "mixed", "duplicate", "reserved", "multi_case", "changed_revision"]:
            q = copy.deepcopy(p)
            if mode == "missing": q["case_parents"] = {}
            if mode == "mixed": q["documents"][0]["profile"] = "CASE_parent"
            if mode == "duplicate": q["documents"].append(copy.deepcopy(q["documents"][0]))
            if mode == "reserved": q["documents"][0]["id"] = formatting.EXAMPLE_ID
            if mode == "multi_case": q["case_parents"]["Other"] = "e" * 40
            if mode == "changed_revision": q["documents"][0]["revision"] = "e" * 40
            with self.subTest(mode=mode), self.assertRaises(ValueError): formatting.schema_description(q)

    def test_generated_full_synthetic_example_reaches_frozen_binding_and_lexical_checks(self):
        output, bound = example()
        result = checks.check_output(output, bound)
        self.assertEqual([r["status"] for r in result["candidate_bindings"]], ["source_bound_candidate"] * 3)
        self.assertEqual(result["local_checks"][0]["status"], "verified_lexical_order")
        self.assertFalse(result["semantic_or_effect_proof"])
        self.assertFalse(result["local_checks"][0]["control_flow_proved"])

    def test_uninstantiated_case_placeholder_is_not_salvaged(self):
        output, bound = example()
        output["architecture_paths"][0]["profile"] = output["local_checks"][0]["profile"] = "CASE_parent"
        result = checks.check_output(output, bound)
        self.assertEqual(result["candidate_bindings"][1]["reasons"], ["unknown_material_group"])
        self.assertEqual(result["local_checks"][0]["reasons"], ["material_group_or_function_invalid"])

    def test_lines_string_is_not_mapped_or_repaired(self):
        output, bound = example()
        bad = [{"document": formatting.EXAMPLE_ID, "lines": "3-4"}]
        output["requirements"][0]["evidence"] = output["local_checks"][0]["evidence"] = bad
        result = checks.check_output(output, bound)
        self.assertEqual(result["candidate_bindings"][0]["reasons"], ["evidence_schema_mismatch"])
        self.assertEqual(result["local_checks"][0]["reasons"], ["evidence_schema_mismatch"])

    def test_overspan_and_noninteger_coordinates_remain_insufficient(self):
        for start, end in [(1, 25), (True, 4), ("3", 4)]:
            output, bound = example(formatting.EXAMPLE_TEXT + "/* pad */\n" * 25)
            output["requirements"][0]["evidence"] = [{"document": formatting.EXAMPLE_ID,
                                                       "start_line": start, "end_line": end}]
            self.assertEqual(checks.check_output(output, bound)["candidate_bindings"][0]["reasons"],
                             ["evidence_line_range_invalid"])

    def test_fake_document_and_nonsupported_condition_anchor_are_not_accepted(self):
        output, bound = example()
        output["requirements"][0]["evidence"][0]["document"] = "not_provided"
        self.assertEqual(checks.check_output(output, bound)["candidate_bindings"][0]["reasons"], ["evidence_document_unknown"])
        output, bound = example(formatting.EXAMPLE_TEXT.replace("prepare();", "if (prepare()) return;"))
        self.assertEqual(checks.check_output(output, bound)["local_checks"][0]["status"], "insufficient")

    def test_generator_does_not_mutate_packet_and_labels_synthetic_example_separately(self):
        p, _ = packet(); original = copy.deepcopy(p)
        d = formatting.schema_description(p)
        self.assertNotIn(d["synthetic_example"]["document"]["id"], d["allowed_document_ids"])
        text = formatting.render_schema_instructions(p)
        self.assertIn("document/start_line/end_line", text)
        self.assertIn("最多24行", text)
        self.assertIn("Q_parent", text)
        self.assertEqual(p, original)


if __name__ == "__main__":
    unittest.main()
