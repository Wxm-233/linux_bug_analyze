"""Synthetic context/binding boundaries; no new runtime or accuracy samples."""
import copy
import unittest

import context_binding as binding


CALLER = """static void sched_core_cpu_starting(unsigned int cpu)
{
 const struct cpumask *smt_mask = cpu_smt_mask(cpu);
 struct rq *rq = cpu_rq(cpu);
 unsigned long flags;
 int t;
 sched_core_lock(cpu, &flags);
 if (cpumask_weight(smt_mask) == 1)
  return;
}
"""
CALLEE = """static void sched_core_lock(int cpu, unsigned long *flags)
{
 const struct cpumask *other_alias = cpu_smt_mask(cpu);
 int t;
 local_irq_save(*flags);
 for_each_cpu(t, other_alias)
  raw_spin_lock_nested(&cpu_rq(t)->__lock, 0);
}
"""


def document(identifier, text, start):
    lines = text.splitlines()
    return {"id": identifier, "path": "kernel/sched/core.c", "kind": "source", "start_line": start,
            "end_line": start + len(lines) - 1, "text": "\n".join(f"{n}: {line}" for n, line in enumerate(lines, start))}


def archives():
    return {"inputs_unchanged": True, "rows": [{"profile": name, "failed_foundation": [],
        "status": "irrelevant_old_label", "predicates": {"irrelevant": "must_not_grade"},
        "first_consumption": {"cpu": 1, "mask": mask, "weight": mask.bit_count(), "online": 0}}
        for name, mask in (("a", 0), ("b", 2), ("c", 2), ("d", 2))]}


def fixture(caller=CALLER, callee=CALLEE):
    request = {"revision": binding.AST.OLD, "documents": [document("C", caller, 10), document("L", callee, 30)]}
    ref = {"document": "C", "start_line": 12, "end_line": 12}
    check = {"id": "fixture", "providers": [], "configuration": [],
        "consumer": {"function": "sched_core_cpu_starting", "event": "first_read", "anchor": "cpu_smt_mask(cpu)", "evidence": [ref]},
        "predicate": {"op": "contains", "args": [{"symbol": "smt_mask"}, {"symbol": "cpu"}]},
        "polarity": "must_hold", "authority_status": "policy_proposal", "evidence": [copy.deepcopy(ref)]}
    return request, {"scope": "local_candidate", "checks": [check]}


class ContextTests(unittest.TestCase):
    def test_context_expansion_is_not_model_reference(self):
        request, proposal = fixture()
        original = copy.deepcopy(proposal)
        result = binding.analyze(request, proposal, "formal_proposal", archives)
        self.assertEqual(result["status"], "context_bound_original_event_insufficient")
        self.assertEqual(result["original_model_references"]["consumer"], proposal["checks"][0]["consumer"]["evidence"])
        self.assertEqual(result["program_expanded_context"][0]["start_line"], 10)
        self.assertEqual(result["original_event_evaluation"]["status"], "insufficient")
        self.assertFalse(result["original_position_classification"]["is_content_snapshot"])
        self.assertEqual(proposal, original)
        projection = result["diagnostic_content_projection"]
        self.assertFalse(projection["at_original_model_event"])
        self.assertEqual(projection["observed_event"], "pre_irq_disable_content_sample")
        self.assertTrue(projection["not_exact_iteration_observation"])
        self.assertEqual(projection["value_at_exact_suggested_iteration"], "insufficient")
        self.assertFalse(projection["inherited_foundation_interpretation"]["continuous_object_stability_proved"])
        self.assertEqual([row["value"] for row in projection["values"]], [False, True, True, True])

    def test_function_scope_requires_complete_signature_and_body(self):
        for caller in (CALLER.replace("static void sched_core_cpu_starting(unsigned int cpu)\n", ""), CALLER.rsplit("}", 1)[0]):
            result = binding.analyze(*fixture(caller=caller), "formal_proposal", archives)
            self.assertEqual(result["status"], "insufficient")
            self.assertFalse(result["source_connection"])

    def test_same_named_variable_in_other_function_does_not_bind(self):
        callee = CALLEE.replace("cpu_smt_mask(cpu)", "cpu_smt_mask(other_cpu)")
        result = binding.analyze(*fixture(callee=callee), "formal_proposal", archives)
        self.assertEqual(result["status"], "insufficient")
        self.assertFalse(result["source_connection"])

    def test_explicit_parameter_map_accepts_different_alias_names(self):
        result = binding.analyze(*fixture(), "formal_proposal", archives)
        edge = result["source_connection"]
        self.assertEqual(edge["parameter_to_argument"]["cpu"], "cpu")
        self.assertEqual(edge["callee_alias"]["name"], "other_alias")

    def test_intermediate_write_or_unknown_call_is_insufficient(self):
        for inserted in ("cpumask_clear(smt_mask);", "smt_mask = another;", "cpu = 0;", "unknown_update();", "if (cpu) return;"):
            caller = CALLER.replace(" int t;", " int t;\n " + inserted)
            result = binding.analyze(*fixture(caller=caller), "formal_proposal", archives)
            self.assertEqual(result["status"], "insufficient")
            self.assertFalse(result["source_connection"])
        callee = CALLEE.replace(" int t;", " int t;\n cpumask_clear(other_alias);")
        self.assertEqual(binding.analyze(*fixture(callee=callee), "formal_proposal", archives)["status"], "insufficient")

    def test_prefix_compound_and_indexed_writes_reject(self):
        statements = ("++cpu;", "--cpu;", "cpu ^= 1;", "cpu |= 1;", "cpu <<= 1;",
                      "cpu >>= 1;", "cpu *= 2;", "cpu /= 2;", "cpu %= 2;", "cpu &= 1;",
                      "smt_mask[0] = replacement;", "(*smt_mask).bits[0] = 0;",
                      "*smt_mask = replacement;", "++smt_mask;", "unrelated = 1;", "asm volatile(\"\");")
        for statement in statements:
            with self.subTest(statement=statement):
                caller = CALLER.replace(" int t;", " int t;\n " + statement)
                result = binding.analyze(*fixture(caller=caller), "formal_proposal", archives)
                self.assertEqual(result["status"], "insufficient")
                self.assertFalse(result["source_connection"])
                self.assertNotIn("diagnostic_content_projection", result)

    def test_wrong_argument_and_missing_callee_stay_insufficient(self):
        request, proposal = fixture(caller=CALLER.replace("sched_core_lock(cpu, &flags)", "sched_core_lock(0, &flags)"))
        self.assertEqual(binding.analyze(request, proposal, "formal_proposal", archives)["status"], "insufficient")
        request, proposal = fixture()
        request["documents"].pop()
        self.assertEqual(binding.analyze(request, proposal, "formal_proposal", archives)["status"], "insufficient")

    def test_comment_text_cannot_supply_function_or_alias(self):
        caller = CALLER.replace("const struct cpumask *smt_mask = cpu_smt_mask(cpu);", "/* const struct cpumask *smt_mask = cpu_smt_mask(cpu); */")
        result = binding.analyze(*fixture(caller=caller), "formal_proposal", archives)
        self.assertEqual(result["status"], "insufficient")

    def test_archival_failure_retains_source_but_not_values(self):
        request, proposal = fixture()
        archive = archives()
        archive["rows"][0]["failed_foundation"] = ["wrong_cpu_or_phase"]
        result = binding.analyze(request, proposal, "formal_proposal", lambda: archive)
        self.assertEqual(result["status"], "context_bound_original_event_insufficient")
        self.assertEqual(result["diagnostic_content_projection"]["status"], "unmapped")
        self.assertFalse(result["diagnostic_content_projection"]["values"])

    def test_original_ast_and_diagnostic_protocol_status_preserved(self):
        for predicate in ({"op": "nonempty", "args": [{"symbol": "smt_mask"}]},
                          {"op": "eq", "args": [{"symbol": "cpumask_weight(smt_mask)"}, {"literal": 1}]}):
            request, proposal = fixture()
            proposal["checks"][0]["predicate"] = predicate
            result = binding.analyze(request, proposal, "posthoc_diagnostic_not_formal_pass", archives)
            self.assertEqual(result["original_model_ast"], predicate)
            self.assertFalse(result["model_protocol_status_changed"])
            self.assertEqual(result["input_origin"], "posthoc_diagnostic_not_formal_pass")
            self.assertEqual(result["diagnostic_content_projection"]["status"], "diagnostic_values_at_separate_content_boundary")

    def test_revision_or_original_reference_error_does_not_expand(self):
        for mutation in ("revision", "reference"):
            request, proposal = fixture()
            if mutation == "revision": request["revision"] = "0" * 40
            else: proposal["checks"][0]["consumer"]["evidence"][0]["end_line"] = 99999
            result = binding.analyze(request, proposal, "formal_proposal", archives)
            self.assertEqual(result["status"], "insufficient")
            self.assertFalse(result["program_expanded_context"])


if __name__ == "__main__":
    unittest.main()
