"""Synthetic, offline adapter tests, not new kernel cases or detection accuracy."""
import copy
import unittest

import evaluate_predicates as adapter


SOURCE = """static void sched_core_cpu_starting(unsigned int cpu)
{
 const struct cpumask *smt_mask = cpu_smt_mask(cpu);
 sched_core_lock(cpu, &flags);
 if (cpumask_weight(smt_mask) == 1)
  return;
}
"""


def fixture(predicate=None, polarity="must_hold"):
    lines = SOURCE.splitlines()
    request = {"revision": adapter.OLD, "documents": [{"id": "C", "kind": "source", "path": "kernel/sched/core.c",
               "start_line": 10, "end_line": 10 + len(lines) - 1,
               "text": "\n".join(f"{n}: {line}" for n, line in enumerate(lines, 10))}]}
    ref = {"document": "C", "start_line": 10, "end_line": 10 + len(lines) - 1}
    check = {"id": "neutral", "providers": [], "configuration": [],
             "consumer": {"function": "sched_core_cpu_starting", "event": "before_call",
                          "anchor": "sched_core_lock(cpu, &flags)", "evidence": [ref]},
             "evidence": [ref], "predicate": predicate, "polarity": polarity,
             "authority_status": "existing_requirement"}
    return request, {"scope": "local_candidate", "checks": [check]}


def observations():
    return {"inputs_unchanged": True, "rows": [{"profile": name, "failed_foundation": [],
                "first_consumption": {"cpu": 1, "current": 1, "phase": "lock_snapshot", "mask": mask,
                                      "weight": mask.bit_count(), "online": 0}}
                for name, mask in (("a", 0), ("b", 2), ("c", 2), ("d", 2))]}


def run(predicate, polarity="must_hold"):
    request, proposal = fixture(predicate, polarity)
    return adapter.adapt(request, proposal, observations)


class AdapterTests(unittest.TestCase):
    def test_multiple_predicates_preserved_and_evaluated(self):
        predicates = [{"op": "nonempty", "args": [{"symbol": "smt_mask"}]},
                      {"op": "eq", "args": [{"symbol": "cpumask_weight(smt_mask)"}, {"literal": 1}]},
                      {"op": "contains", "args": [{"symbol": "cpu_smt_mask(cpu)"}, {"symbol": "cpu"}]}]
        for predicate in predicates:
            with self.subTest(predicate=predicate):
                result = run(predicate)
                self.assertEqual(result["status"], "mapped")
                self.assertEqual(result["checks"][0]["predicate"], predicate)
                self.assertEqual([r["value"] for r in result["checks"][0]["archived_values"]], [False, True, True, True])
                self.assertEqual(result["checks"][0]["source_scope"]["classification"], "local_or_conditional_candidate")

    def test_polarity_is_not_inferred(self):
        predicate = {"op": "nonempty", "args": [{"symbol": "smt_mask"}]}
        must, alert = run(predicate), run(predicate, "alert_if_true")
        self.assertEqual([r["value"] for r in must["checks"][0]["archived_values"]],
                         [r["value"] for r in alert["checks"][0]["archived_values"]])
        self.assertNotEqual(must["checks"][0]["archived_values"][0]["alert_candidate"],
                            alert["checks"][0]["archived_values"][0]["alert_candidate"])

    def test_no_short_circuit_hides_unknown(self):
        predicate = {"op": "or", "args": [{"literal": True}, {"symbol": "unknown_call(cpu)"}]}
        result = run(predicate)
        self.assertEqual(result["status"], "unmapped")
        self.assertFalse(result["checks"][0]["archived_values"])

    def test_cross_function_online_is_unmapped(self):
        request, proposal = fixture({"symbol": "cpu_online(cpu)"})
        lines = ["static void different(int cpu)", "{", " if (cpu_online(cpu)) return;", "}"]
        request["documents"].append({"id": "OTHER", "kind": "source", "path": "arch/s390/kernel/topology.c",
            "start_line": 1, "end_line": 4, "text": "\n".join(f"{n}: {line}" for n, line in enumerate(lines, 1))})
        proposal["checks"][0]["evidence"].append({"document": "OTHER", "start_line": 1, "end_line": 4})
        self.assertEqual(adapter.adapt(request, proposal, observations)["status"], "unmapped")

    def test_missing_alias_signature_and_wrong_time(self):
        for mutation in ("alias", "signature", "event", "anchor"):
            with self.subTest(mutation=mutation):
                request, proposal = fixture({"op": "nonempty", "args": [{"symbol": "smt_mask"}]})
                check = proposal["checks"][0]
                if mutation == "alias": request["documents"][0]["text"] = request["documents"][0]["text"].replace("*smt_mask =", "*different =")
                elif mutation == "signature":
                    for ref in check["evidence"] + check["consumer"]["evidence"]: ref["start_line"] = 11
                elif mutation == "event": check["consumer"]["event"] = "entry"
                else: check["consumer"]["anchor"] = "other_call(cpu)"
                self.assertEqual(adapter.adapt(request, proposal, observations)["status"], "unmapped")

    def test_bounds_revision_schema_and_types(self):
        request, proposal = fixture({"op": "eq", "args": [{"literal": True}, {"literal": 1}]})
        self.assertEqual(adapter.adapt(request, proposal, observations)["status"], "unmapped")
        for mutation in ("revision", "bounds", "operator"):
            req, prop = fixture({"op": "nonempty", "args": [{"symbol": "smt_mask"}]})
            if mutation == "revision": req["revision"] = "0" * 40
            elif mutation == "bounds": prop["checks"][0]["evidence"][0]["end_line"] = 99999
            else: prop["checks"][0]["predicate"]["op"] = "eval"
            self.assertEqual(adapter.adapt(req, prop, observations)["status"], "invalid")
        for op, expected in (("eq", False), ("ne", True), ("lt", True), ("le", True), ("gt", False), ("ge", False)):
            result = run({"op": op, "args": [{"literal": 1}, {"literal": 2}]})
            self.assertEqual(result["status"], "mapped")
            self.assertTrue(all(row["value"] is expected for row in result["checks"][0]["archived_values"]))
        result = run({"op": "and", "args": [{"literal": True}, {"op": "not", "args": [{"literal": False}]}]})
        self.assertTrue(all(row["value"] is True for row in result["checks"][0]["archived_values"]))

    def test_absent_or_null_predicate_stays_unmapped(self):
        request, proposal = fixture()
        self.assertEqual(adapter.adapt(request, proposal, observations)["status"], "unmapped")
        proposal["checks"] = []
        self.assertEqual(adapter.adapt(request, proposal, observations)["status"], "unmapped")

    def test_no_event_observation_for_precedes(self):
        result = run({"op": "precedes", "args": [{"symbol": "update_cpu_masks()"}, {"symbol": "notify_cpu_starting(cpu)"}]})
        self.assertEqual(result["status"], "unmapped")

    def test_foundation_failure_never_yields_values(self):
        for failure in ("provider", "config", "cpu", "phase", "revision", "pair_config", "source"):
            request, proposal = fixture({"op": "nonempty", "args": [{"symbol": "smt_mask"}]})
            archive = observations()
            archive["rows"][0]["failed_foundation"] = [failure]
            result = adapter.adapt(request, proposal, lambda: archive)
            self.assertEqual(result["status"], "unmapped")
            self.assertFalse(result["checks"][0]["archived_values"])

    def test_archive_judgments_are_ignored_and_identity_is_checked(self):
        class FakeReplay:
            PROFILES = ("old_s390", "fixed_s390", "old_x86", "fixed_x86")
            @staticmethod
            def replay(material):
                # Deliberately irrelevant historical labels must not leak into output.
                return {"status": "invented", "predicates": {"must_not_be_used": True},
                        "foundation": {"synthetic_foundation": True},
                        "first_consumption": {"cpu": 1, "current": 1, "phase": "lock_snapshot", "mask": 2, "weight": 1, "online": 0}}
        materials = []
        for profile in FakeReplay.PROFILES:
            variant, arch = profile.split("_")
            materials.append({"profile": profile, "build": {"variant": variant, "revision": adapter.REVISIONS[variant]},
                "details": {"arch": arch}, "cfg": {"CONFIG_A": "y", "CONFIG_LOCALVERSION": variant},
                "source_hashes": {path: "same" for path in ("kernel/cpu.c", "kernel/sched/core.c", "arch/x86/kernel/smpboot.c")}})
        rows = adapter.archive_from_materials(FakeReplay, materials)
        self.assertTrue(all(not row["failed_foundation"] for row in rows))
        self.assertTrue(all("predicates" not in row and "status" not in row for row in rows))
        broken = copy.deepcopy(materials)
        broken[0]["cfg"]["CONFIG_A"] = "n"
        broken[0]["build"]["revision"] = "0" * 40
        broken[0]["source_hashes"]["kernel/cpu.c"] = "other"
        rows = adapter.archive_from_materials(FakeReplay, broken)
        self.assertTrue(any(row["failed_foundation"] for row in rows))
        for field, value in (("cpu", 0), ("current", 0), ("phase", "final")):
            class WrongFirst(FakeReplay):
                @staticmethod
                def replay(material):
                    parsed = FakeReplay.replay(material)
                    parsed["first_consumption"][field] = value
                    return parsed
            rows = adapter.archive_from_materials(WrongFirst, materials)
            self.assertTrue(all("first_cpu_object_and_phase" in row["failed_foundation"] for row in rows))

    def test_weak_check_logical_counterexample_not_reachable_claim(self):
        # Pure sets, not archived/new kernel observations: weight one need not contain target.
        values = {"mask": {0}, "target": 1}
        self.assertTrue(adapter.evaluate_ast({"op": "nonempty", "args": [{"symbol": "mask"}]}, values))
        self.assertFalse(adapter.evaluate_ast({"op": "contains", "args": [{"symbol": "mask"}, {"symbol": "target"}]}, values))


if __name__ == "__main__":
    unittest.main()
