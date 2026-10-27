"""N2.22 bounded adapter development tests, not independent case evaluation."""
import hashlib
import unittest

from linux_bug_analyze.gimple_write_effects import SCOPE, analyze_write_effects, check_write_candidate


def record(bodies=None, successors=None, declaration="", function="ordinary"):
    bodies = bodies or {2: "[sample.c:8:3] nr_cpu_ids = value;\nreturn;"}
    successors = successors or {2: [1]}
    nodes = [0, 1] + sorted(bodies)
    lines = [f";; Function {function} ({function}, funcdef_no=1)", ";; 1 loops found", ";; Loop 0",
             ";;  header 0, latch 1", ";;  depth 0, outer -1", ";;  nodes: " + " ".join(map(str, nodes))]
    lines += [f";; {key} succs {{ " + " ".join(map(str, targets)) + " }" for key, targets in successors.items()]
    lines += [f"void {function} (int value)", "{", declaration]
    for key, body in bodies.items():
        lines += [f" <bb {key}> :", body]
    return "\n".join(lines + ["}", ""])


def document(text=None):
    return {"id": "write-component", "path": "sample.cfg", "revision": "development", "text": text or record()}


def analyze(text=None, **kwargs):
    return analyze_write_effects(document(text), function=kwargs.pop("function", "ordinary"),
                                 target=kwargs.pop("target", "nr_cpu_ids"), **kwargs)


def candidate(doc, claim="direct_write_exists", **kwargs):
    result = {"function": "ordinary", "target": "nr_cpu_ids", "claim": claim, "scope": SCOPE,
              "source_sha256": hashlib.sha256(doc["text"].encode("utf-8")).hexdigest()}
    result.update(kwargs)
    return result


class GimpleWriteEffectsTests(unittest.TestCase):
    def test_plain_function_direct_write_with_exact_source_evidence(self):
        result = analyze()
        self.assertEqual(result["status"], "direct_write_observed", result["unknowns"])
        write = result["writes"][0]
        self.assertEqual(write["id"], "B2S1")
        self.assertEqual(write["source_sha256"], result["source_sha256"])
        self.assertEqual(write["source_locations"], [{"path": "sample.c", "line": 8, "column": 3, "discriminator": None}])
        self.assertEqual(document()["text"][write["start_offset"]:write["end_offset"]], write["raw"])
        self.assertFalse(result["unconditional_write_proved"])
        self.assertFalse(result["external_state_binding_proved"])
        renamed = analyze(record(function="unrelated_name"), function="unrelated_name")
        self.assertEqual(renamed["status"], "direct_write_observed")

    def test_read_and_write_of_different_local_not_target_write(self):
        result = analyze(record({2: "value = nr_cpu_ids;\nreturn;"}))
        self.assertEqual(result["status"], "no_direct_write_observed")
        self.assertFalse(result["writes"])
        self.assertFalse(result["no_global_or_indirect_effect_proved"])

    def test_conditional_assignment_retains_branch_without_must_write(self):
        text = record({2: "if (value != 0) goto <bb 3>; [INV] else goto <bb 4>; [INV]",
                       3: "[sample.c:8:3] nr_cpu_ids = value;", 4: "return;"}, {2: [3, 4], 3: [4], 4: [1]})
        result = analyze(text)
        self.assertEqual(result["status"], "direct_write_observed")
        self.assertEqual(result["writes"][0]["branch_context"][0]["arm"], "true")
        self.assertFalse(result["writes"][0]["branch_context_complete"])
        self.assertFalse(result["unconditional_write_proved"])
        doc = document(text)
        self.assertEqual(check_write_candidate(doc, candidate(doc))["status"], "observed")
        checked = check_write_candidate(doc, candidate(doc, "unconditional_write"))
        self.assertEqual((checked["status"], checked["reason"]), ("insufficient", "unconditional_or_must_write_not_proved"))

    def test_called_setter_and_alias_do_not_become_direct_write(self):
        result = analyze(record({2: "set_nr_cpu_ids (value);\nchange (&nr_cpu_ids);\nreturn;"}))
        self.assertEqual(result["status"], "no_direct_write_observed")
        self.assertFalse(result["writes"])
        self.assertEqual(sum(item.get("kind") == "call" for item in result["unknowns"]), 2)
        doc = document(record({2: "set_nr_cpu_ids (value);\nreturn;"}))
        self.assertEqual(check_write_candidate(doc, candidate(doc))["status"], "insufficient")
        result = analyze(record({2: "*pointer = value;\nreturn;"}))
        self.assertEqual(result["status"], "insufficient")
        self.assertTrue(result["unknowns"])

    def test_same_spelling_local_and_parameter_are_not_external_state(self):
        local = analyze(record(declaration="int nr_cpu_ids;"))
        self.assertEqual(local["status"], "direct_write_observed")
        self.assertEqual(local["shadow_facts"][0]["kind"], "local_declaration")
        text = record().replace("int value)", "int nr_cpu_ids, int value)")
        parameter = analyze(text)
        self.assertEqual(parameter["shadow_facts"][0]["kind"], "parameter_spelling_present")
        for text in (record(declaration="int nr_cpu_ids;"), text):
            doc = document(text)
            checked = check_write_candidate(doc, candidate(doc, scope="external_state"))
            self.assertEqual(checked["status"], "insufficient")
            self.assertFalse(checked["external_state_binding_proved"])
            self.assertEqual(check_write_candidate(doc, candidate(doc, **{"global": True}))["status"], "insufficient")

    def test_pointer_field_array_and_unknown_target_definitions_are_insufficient(self):
        for target in ("*pointer", "p->field", "array[0]", "D.123"):
            with self.subTest(target=target):
                self.assertEqual(analyze(target=target)["status"], "insufficient")
        for declaration in ("int * nr_cpu_ids;",):
            self.assertEqual(analyze(record(declaration=declaration))["status"], "insufficient")
        for body in ("nr_cpu_ids = helper (value);\nreturn;", "nr_cpu_ids = p->field;\nreturn;"):
            result = analyze(record({2: body}))
            self.assertEqual(result["status"], "insufficient")
            self.assertIn("target_definition_outside_supported_scalar_assignment", str(result["unknowns"]))

    def test_function_text_and_source_hash_are_bound(self):
        result = analyze(function="some_setter")
        self.assertEqual(result["status"], "insufficient")
        self.assertIn("selected_function_mismatch", str(result["unknowns"]))
        for binding in ("0" * 64, "not-a-sha", 42):
            with self.subTest(binding=binding):
                self.assertEqual(analyze(expected_sha256=binding)["status"], "insufficient")
        doc = document()
        self.assertEqual(analyze(expected_sha256=candidate(doc)["source_sha256"])["status"], "direct_write_observed")
        original = candidate(doc)
        doc["text"] += "\n"
        self.assertEqual(check_write_candidate(doc, original)["status"], "insufficient")

    def test_bad_metadata_multifunction_and_missing_input_fail_closed(self):
        for text in (record() + record(function="second"), record().replace(";; 2 succs { 1 }", ""), record()[:-3]):
            with self.subTest(text=text[:30]):
                self.assertEqual(analyze(text)["status"], "insufficient")
        for doc in (None, {}, {"text": 3}):
            self.assertEqual(analyze_write_effects(doc, function="ordinary", target="nr_cpu_ids")["status"], "insufficient")
        doc = document()
        for bad in (None, {}, candidate(doc, source_sha256="bad"), candidate(doc, claim="complete_global_effect")):
            self.assertEqual(check_write_candidate(doc, bad)["status"], "insufficient")

    def test_comments_and_strings_never_create_assignments(self):
        result = analyze(record({2: "/* nr_cpu_ids = value; */\nreturn;"}))
        self.assertEqual(result["status"], "no_direct_write_observed")
        result = analyze(record({2: 'say ("nr_cpu_ids = value;");\nreturn;'}))
        self.assertEqual(result["status"], "insufficient")
        self.assertFalse(result["writes"])


if __name__ == "__main__":
    unittest.main()
