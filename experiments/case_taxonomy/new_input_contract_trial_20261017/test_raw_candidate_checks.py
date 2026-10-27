import copy
import importlib.util
import json
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location("n26_raw_checks", Path(__file__).with_name("run_raw_candidate_checks.py"))
checks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checks)

TEXT = "/* unrelated whole-file prefix */\n\nvoid worker(void)\n{\n  prepare();\n  notify();\n}\n"
PARENT = "a" * 40


def packet(text=TEXT):
    digest = checks.sha(text.encode("utf-8"))
    row = {"id": "S1", "case": "E", "revision": PARENT, "path": "kernel/example.c", "text": text,
           "sha256": digest, "status": "collected", "material_group": "E_parent"}
    payload = json.dumps({"documents": [row]}, sort_keys=True).encode()
    doc = {"id": "D1", "case": "E", "parent": PARENT, "revision": PARENT, "profile": "E_parent",
           "kind": "raw_source_file", "function": None, "path": "kernel/example.c", "text": text,
           "file_sha256": digest, "text_sha256": digest, "configuration_sha256": None,
           "image_sha256": None, "preprocessed_sha256": None,
           "source_binding": {"artifact": "sources.json", "artifact_sha256": checks.sha(payload), "json_pointer": "/documents/0/text"}}
    return {"schema": checks.SCHEMA, "case_parents": {"E": PARENT}, "documents": [doc],
            "input_manifest": [{"path": "sources.json", "sha256": checks.sha(payload)}]}, {"sources.json": payload}


def claim(first=5, second=6):
    return {"id": "L1", "kind": "lexical_call_order", "profile": "E_parent", "document": "D1", "function": "worker",
            "first": {"callee": "prepare", "line": first}, "second": {"callee": "notify", "line": second},
            "expected": "before", "evidence": [{"document": "D1", "start_line": 1, "end_line": max(first, second, 7)}]}


class RawCandidateChecksTests(unittest.TestCase):
    def run_claim(self, c=None, text=TEXT):
        p, a = packet(text)
        return checks.check_lexical_order(claim() if c is None else c, checks.bind_documents(p, a))

    def test_exact_raw_bytes_parent_and_material_group_bind_without_configuration(self):
        p, a = packet()
        r = checks.bind_documents(p, a)["D1"]
        self.assertEqual(r["status"], "source_bound")
        self.assertEqual(r["source_layer"], "raw_source_only")
        self.assertIsNone(r["document"]["configuration_sha256"])

    def test_raw_text_or_artifact_byte_change_is_not_normalized(self):
        for mode in ["text", "artifact", "file_digest"]:
            p, a = packet()
            if mode == "text": p["documents"][0]["text"] += "\n"
            if mode == "artifact": a["sources.json"] += b" "
            if mode == "file_digest": p["documents"][0]["file_sha256"] = "b" * 64
            self.assertEqual(checks.bind_documents(p, a)["D1"]["status"], "insufficient")

    def test_parent_revision_path_and_material_group_cannot_be_borrowed(self):
        for field, value in [("case", "F"), ("parent", "b" * 40), ("revision", "b" * 40),
                             ("profile", "old_s390"), ("path", "kernel/other.c")]:
            p, a = packet(); p["documents"][0][field] = value
            self.assertEqual(checks.bind_documents(p, a)["D1"]["status"], "insufficient")
        p, a = packet(); p["case_parents"]["E"] = "b" * 40
        self.assertEqual(checks.bind_documents(p, a)["D1"]["status"], "insufficient")

    def test_raw_document_cannot_claim_configured_identity_or_failed_collection(self):
        for field in ["configuration_sha256", "image_sha256", "preprocessed_sha256"]:
            p, a = packet(); p["documents"][0][field] = "b" * 64
            self.assertEqual(checks.bind_documents(p, a)["D1"]["status"], "insufficient")
        p, a = packet()
        origin = json.loads(a["sources.json"]); origin["documents"][0]["status"] = "missing"
        a["sources.json"] = json.dumps(origin).encode(); h = checks.sha(a["sources.json"])
        p["documents"][0]["source_binding"]["artifact_sha256"] = p["input_manifest"][0]["sha256"] = h
        self.assertEqual(checks.bind_documents(p, a)["D1"]["status"], "insufficient")

    def test_unique_complete_slice_preserves_whole_file_and_fragment_coordinates(self):
        r = self.run_claim()
        self.assertEqual(r["status"], "verified_lexical_order")
        self.assertEqual(r["function_slice"]["first_line"], 3)
        self.assertEqual([a["line"] for a in r["anchors"]], [5, 6])
        self.assertEqual([a["fragment_line"] for a in r["anchors"]], [3, 4])
        self.assertFalse(r["configuration_applicability_proved"])
        self.assertFalse(r["preparation_effect_proved"])
        c = claim(); c["expected"] = "after"
        self.assertEqual(self.run_claim(c)["status"], "not_established")

    def test_wrong_unsupported_or_multiple_definitions_are_insufficient(self):
        c = claim(); c["function"] = "missing"
        self.assertEqual(self.run_claim(c)["status"], "insufficient")
        self.assertEqual(self.run_claim(text=TEXT + TEXT)["status"], "insufficient")
        self.assertEqual(self.run_claim(text=TEXT.replace("void worker", "long worker"))["status"], "insufficient")

    def test_directives_inside_fragment_are_preserved_and_not_repaired(self):
        text = TEXT.replace("  prepare();", "#if ACTIVE\n  prepare();\n#endif")
        c = claim(6, 8); p, a = packet(text); before = copy.deepcopy(p)
        r = checks.check_lexical_order(c, checks.bind_documents(p, a))
        self.assertEqual(r["status"], "insufficient")
        self.assertTrue(any("directive" in reason for reason in r["reasons"]))
        self.assertEqual(p, before)

    def test_cast_and_gnu_argument_support_is_reused_but_nested_call_is_not_expanded(self):
        text = TEXT.replace("prepare();", "prepare(({ unsigned long v=1; (void)v; v; }));")
        self.assertEqual(self.run_claim(text=text)["status"], "verified_lexical_order")
        text = TEXT.replace("prepare();", "prepare((unsigned long)1);")
        self.assertEqual(self.run_claim(text=text)["status"], "verified_lexical_order")
        self.assertEqual(self.run_claim(text=TEXT.replace("prepare();", "wrapper(prepare());"))["status"], "insufficient")

    def test_bad_reference_wrong_group_and_anchor_outside_unique_function_reject(self):
        c = claim(); c["profile"] = "F_parent"
        self.assertEqual(self.run_claim(c)["status"], "insufficient")
        c = claim(); c["first"]["line"] = 1
        self.assertEqual(self.run_claim(c)["status"], "insufficient")
        c = claim(); c["evidence"][0]["start_line"] = True
        self.assertEqual(self.run_claim(c)["status"], "insufficient")

    def test_strings_comments_and_prototypes_do_not_become_call_anchors(self):
        for replacement in ['puts("prepare()"); /* prepare(); */', "extern void prepare(void);"]:
            self.assertEqual(self.run_claim(text=TEXT.replace("prepare();", replacement))["status"], "insufficient")

    def test_candidate_groups_and_frozen_parse_keep_semantic_insufficiency(self):
        p, a = packet(); bound = checks.bind_documents(p, a)
        output = {"schema": checks.SCHEMA, "requirements": [{"evidence": claim()["evidence"]}],
                  "architecture_paths": [{"profile": "E_parent", "evidence": claim()["evidence"]}],
                  "recommended_checks": [], "local_checks": [], "limits": []}
        result = checks.check_output(output, bound)
        self.assertEqual([x["status"] for x in result["candidate_bindings"]], ["source_bound_candidate"] * 2)
        self.assertFalse(result["semantic_or_effect_proof"])
        self.assertFalse(result["material_groups_are_architecture_or_configuration_proof"])
        output["architecture_paths"][0]["profile"] = "old_s390"
        self.assertEqual(checks.check_output(output, bound)["candidate_bindings"][1]["status"], "insufficient")
        self.assertEqual(checks.old.parse_final(b'```json\n{"x":1}\n```')[1], "unique_complete_outer_json_fence")

    def test_supplement_budget_distinguishes_kconfig_authority_from_c_implementation(self):
        p, _ = packet()
        selection = {"candidates": [{"case": "E", "hash": "c" * 40, "parent": PARENT,
                      "initial_file_plan": {"public_implementation_paths": ["kernel/example.c"], "public_header_paths": []}}]}
        initial = {"cases": [{"case": "E", "hash": "c" * 40, "parent": PARENT, "paths": ["kernel/example.c"]}]}
        supplement = {"cases": [{"case": "E", "parent": PARENT,
                      "paths": ["arch/example/a.c", "arch/example/b.c", "include/example.h", "arch/example/Kconfig"]}]}
        self.assertEqual(checks.validate_material_identity(p, selection, initial, supplement)["status"],
                         "selected_parent_and_paths_bound")
        for paths in [["a.c", "b.c", "c.c", "Kconfig"],
                      ["a.c", "a.h", "b.h", "Kconfig"], ["a.c", "Makefile"]]:
            with self.subTest(paths=paths):
                supplement["cases"][0]["paths"] = paths
                with self.assertRaisesRegex(checks.old.EvidenceError, "supplement_file_budget"):
                    checks.validate_material_identity(p, selection, initial, supplement)

    def test_external_selection_and_path_plan_reject_self_consistent_but_different_parent(self):
        p, _ = packet()
        selection = {"candidates": [{"case": "E", "hash": "c" * 40, "parent": PARENT,
                      "initial_file_plan": {"public_implementation_paths": ["kernel/example.c"], "public_header_paths": []}}]}
        initial = {"cases": [{"case": "E", "hash": "c" * 40, "parent": PARENT, "paths": ["kernel/example.c"]}]}
        self.assertEqual(checks.validate_material_identity(p, selection, initial)["status"], "selected_parent_and_paths_bound")
        changed = copy.deepcopy(p)
        changed["case_parents"]["E"] = changed["documents"][0]["parent"] = changed["documents"][0]["revision"] = "b" * 40
        with self.assertRaises(checks.old.EvidenceError): checks.validate_material_identity(changed, selection, initial)
        changed = copy.deepcopy(p); changed["documents"][0]["path"] = "drivers/unregistered.c"
        with self.assertRaises(checks.old.EvidenceError): checks.validate_material_identity(changed, selection, initial)
        supplement = {"cases": [{"case": "E", "parent": PARENT, "paths": ["drivers/unregistered.c"]}]}
        self.assertEqual(checks.validate_material_identity(changed, selection, initial, supplement)["status"], "selected_parent_and_paths_bound")
        supplement["cases"][0]["paths"] = ["a.c", "b.c", "c.c"]
        with self.assertRaises(checks.old.EvidenceError): checks.validate_material_identity(p, selection, initial, supplement)


if __name__ == "__main__":
    unittest.main()
