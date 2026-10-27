"""Falsifiable frontend boundaries, not new defect or generalization samples."""

import unittest
from unittest.mock import patch

from linux_bug_analyze.source_conditions import analyze_function, check_source_claim, c_parser


def document(text):
    return {"id": "D", "revision": "revision-A", "path": "sample.c", "start_line": 10,
            "end_line": 9 + len(text.splitlines()), "text": text}


def analyze(text, **options):
    return analyze_function(document(text), **options)


def call(analysis, name, occurrence=0):
    row = [x for x in analysis["calls"] if x["callee"] == name][occurrence]
    return {k: row[k] for k in ("callee", "line", "column")}


def before(analysis):
    return {"id": "C", "document": "D", "revision": "revision-A", "function": "f",
            "kind": "before", "first": call(analysis, "prepare"), "target": call(analysis, "consume"),
            "argument_index": 0}


@unittest.skipIf(c_parser is None, "install the optional research dependencies")
class SourceConditionsTests(unittest.TestCase):
    def test_simple_source_order_has_no_preparation_or_object_content_proof(self):
        a = analyze("void f(int cpu) { prepare(cpu); consume(cpu); }")
        r = check_source_claim(a, before(a))
        self.assertEqual(r["status"], "verified_local_structure")
        self.assertEqual(r["object_identity"], "same_local_argument_version_only")
        self.assertEqual(r["whole_contract"], "insufficient")
        self.assertFalse(r["runtime_witness"])

    def test_conditional_prepare_is_not_a_required_predecessor(self):
        a = analyze("void f(int cpu, int p) { if (p) prepare(cpu); consume(cpu); }")
        self.assertEqual(check_source_claim(a, before(a))["status"], "not_established")

    def test_early_return_keeps_surviving_path_condition(self):
        a = analyze("void f(int cpu, int p) { if (p) return; prepare(cpu); consume(cpu); }")
        r = check_source_claim(a, before(a))
        self.assertEqual(r["status"], "verified_local_structure")
        self.assertEqual(r["guards_to_target"][0][0]["taken"], False)
        claim = {**before(a), "kind": "unconditional_call"}
        self.assertEqual(check_source_claim(a, claim)["status"], "not_established")

    def test_if_else_and_required_branch_polarity(self):
        a = analyze("void f(int cpu, int p) { if (!p) { prepare(cpu); consume(cpu); } else return; }")
        condition = a["conditions"][0]
        claim = {**before(a), "kind": "requires_branch", "branch": {"line": condition["line"], "taken": True}}
        self.assertEqual(check_source_claim(a, claim)["status"], "verified_local_structure")
        claim["branch"]["taken"] = False
        self.assertEqual(check_source_claim(a, claim)["status"], "not_established")

    def test_later_guard_is_not_a_condition_for_an_earlier_target(self):
        a = analyze("void f(int cpu, int p) {\n prepare(cpu); consume(cpu);\n if (p) later();\n}")
        r = check_source_claim(a, before(a))
        self.assertTrue(all(not guards for guards in r["guards_to_target"]))
        claim = {**before(a), "kind": "requires_branch", "branch": {"line": a["conditions"][0]["line"], "taken": True}}
        self.assertEqual(check_source_claim(a, claim)["status"], "not_established")

    def test_same_condition_text_is_not_shared_across_evaluation_sites(self):
        a = analyze("void f(int cpu, int p) {\n if (p) prepare(cpu);\n change();\n if (p) consume(cpu);\n}")
        self.assertEqual(len(a["paths"]), 4)
        self.assertEqual(check_source_claim(a, before(a))["status"], "not_established")

    def test_different_cpu_expression_is_not_bound(self):
        a = analyze("void f(int cpu) { prepare(cpu + 1); consume(cpu); }")
        self.assertEqual(check_source_claim(a, before(a))["object_identity"], "unproved")

    def test_reassignment_breaks_local_version_identity(self):
        a = analyze("void f(int cpu) { prepare(cpu); cpu = other(); consume(cpu); }")
        self.assertEqual(check_source_claim(a, before(a))["object_identity"], "unproved")

    def test_address_escape_breaks_local_version_identity(self):
        a = analyze("void f(int cpu) { prepare(cpu); change(&cpu); consume(cpu); }")
        self.assertEqual(check_source_claim(a, before(a))["object_identity"], "unproved")

    def test_shadowing_is_not_same_object(self):
        a = analyze("void f(int cpu) { prepare(cpu); { int cpu = 4; consume(cpu); } }")
        self.assertEqual(check_source_claim(a, before(a))["object_identity"], "unproved")

    def test_different_getters_are_not_assumed_equivalent(self):
        a = analyze("void f(void) { int cpu = get_cpu(); prepare(raw_cpu()); consume(cpu); }")
        self.assertEqual(check_source_claim(a, before(a))["object_identity"], "unproved")

    def test_control_flow_outside_subset_retains_inventory_without_proof(self):
        for body in ("for (;;) prepare(cpu); consume(cpu);", "while (p) prepare(cpu); consume(cpu);",
                     "if (p) goto done; prepare(cpu); done: consume(cpu);",
                     "switch (p) { case 1: prepare(cpu); } consume(cpu);"):
            with self.subTest(body=body):
                a = analyze("void f(int cpu, int p) { " + body + " }")
                self.assertEqual(a["status"], "insufficient")
                self.assertTrue(a["calls"])
                self.assertEqual(check_source_claim(a, {"id": "C"})["status"], "insufficient")

    def test_indirect_call_is_not_silently_ignored(self):
        a = analyze("void f(int cpu, void (*hook)(int)) { prepare(cpu); hook(cpu); consume(cpu); }")
        # A direct identifier can still denote a function-pointer parameter.
        # This assertion prevents confusing its spelling with a known function.
        self.assertEqual(a["status"], "insufficient")

    def test_adjusted_or_typedef_function_parameters_are_not_direct_calls(self):
        a = analyze("void f(void hook(int), int cpu) { hook(cpu); consume(cpu); }")
        self.assertEqual(a["status"], "insufficient")
        a = analyze("void f(callback_t hook, int cpu) { hook(cpu); consume(cpu); }", type_names=("callback_t",))
        self.assertEqual(a["status"], "insufficient")
        a = analyze("void f(int cpu) { callback_t hook; hook(cpu); consume(cpu); }", type_names=("callback_t",))
        self.assertEqual(a["status"], "insufficient")

    def test_unexpanded_macro_and_directives_are_not_parsed_as_complete_flow(self):
        for text in ("void f(int cpu) { for_each_cpu(cpu, mask) { prepare(cpu); } consume(cpu); }",
                     "void f(int cpu) {\n#if ENABLED\n prepare(cpu);\n#endif\n consume(cpu);\n}"):
            self.assertEqual(analyze(text)["status"], "insufficient")

    def test_incomplete_or_multiple_functions_are_insufficient(self):
        for text in ("void f(int cpu) { prepare(cpu);", "void f(int cpu);", "void f(void) {} void g(void) {}"):
            self.assertEqual(analyze(text)["status"], "insufficient")

    def test_source_interval_gaps_are_not_complete_functions(self):
        d = document("void f(void) {}")
        d["end_line"] += 2
        self.assertEqual(analyze_function(d)["status"], "insufficient")

    def test_comments_strings_and_line_coordinates(self):
        a = analyze('void f(int cpu) {\n /* if (x) return; prepare(cpu); */\n say("if return prepare(cpu)");\n prepare(cpu);\n consume(cpu);\n}')
        self.assertEqual(len([x for x in a["calls"] if x["callee"] == "prepare"]), 1)
        self.assertEqual(call(a, "prepare")["line"], 13)
        self.assertEqual(check_source_claim(a, before(a))["status"], "verified_local_structure")

    def test_duplicate_calls_require_an_unambiguous_anchor(self):
        a = analyze("void f(int cpu) { prepare(cpu); prepare(cpu); consume(cpu); }")
        claim = before(a)
        del claim["first"]["column"]
        self.assertEqual(check_source_claim(a, claim)["status"], "insufficient")

    def test_reversing_source_order_changes_result(self):
        a = analyze("void f(int cpu) { consume(cpu); prepare(cpu); }")
        self.assertEqual(check_source_claim(a, before(a))["status"], "not_established")

    def test_labels_and_architecture_names_do_not_control_facts(self):
        d = document("void f(int cpu) { prepare(cpu); consume(cpu); }")
        for label in ("old", "fixed", "architecture-A", "architecture-B"):
            d["label"] = label
            a = analyze_function(d)
            self.assertEqual(check_source_claim(a, before(a))["status"], "verified_local_structure")

    def test_revision_function_or_document_cannot_borrow_evidence(self):
        a = analyze("void f(int cpu) { prepare(cpu); consume(cpu); }")
        for key, value in (("revision", "other"), ("document", "other"), ("function", "other")):
            claim = before(a);claim[key] = value
            self.assertEqual(check_source_claim(a, claim)["status"], "insufficient")

    def test_explicit_path_arguments_and_coordinate_types_are_checked(self):
        a = analyze("void f(int cpu) { prepare(cpu); consume(cpu); }")
        claim = before(a);claim["path"] = "another.c"
        self.assertEqual(check_source_claim(a, claim)["status"], "insufficient")
        claim = before(a);claim["first"]["arguments"] = ["another_cpu"]
        self.assertEqual(check_source_claim(a, claim)["status"], "insufficient")
        claim = before(a);claim["first"]["line"] = True
        self.assertEqual(check_source_claim(a, claim)["status"], "insufficient")

    def test_expression_nested_call_is_not_a_standalone_call_anchor(self):
        a = analyze("void f(int cpu) { prepare(cpu); int x = consume(cpu); }")
        self.assertEqual(check_source_claim(a, before(a))["status"], "insufficient")

    def test_condition_side_effects_and_path_overflow_are_insufficient(self):
        self.assertEqual(analyze("void f(int cpu) { if (cpu++) prepare(cpu); consume(cpu); }")["status"], "insufficient")
        text = "void f(int cpu, int p) { if(p) a(); if(p) b(); if(p) c(); consume(cpu); }"
        self.assertEqual(analyze(text, max_paths=4)["status"], "insufficient")

    def test_annotation_masking_cannot_remove_control_flow(self):
        a = analyze("void f(int cpu) { if (cpu) return; consume(cpu); }", annotations=("return",))
        self.assertEqual(a["status"], "insufficient")
        a = analyze('void __init f(int cpu) { say("__init"); prepare(cpu); consume(cpu); }', annotations=("__init",))
        self.assertEqual(a["status"], "bounded_local_flow")
        self.assertEqual([x for x in a["calls"] if x["callee"] == "say"][0]["arguments"], ['"__init"'])

    def test_missing_optional_parser_is_explicitly_insufficient(self):
        with patch("linux_bug_analyze.source_conditions.c_parser", None):
            self.assertEqual(analyze("void f(void) {}")["status"], "insufficient")


if __name__ == "__main__":
    unittest.main()
