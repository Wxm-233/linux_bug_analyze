import unittest

from linux_bug_analyze.candidate_bridge import _wildcards, _what_lines, build_tu_queries, tu_needs
from linux_bug_analyze.kernel_facts import BUNDLE_SCHEMA, _body_statements, _macro_trace, _returns_only_zero, query

DD = """# 1 "/src/drivers/base/topology.c"
# 1 "/src/arch/x86/include/asm/topology.h" 1
#define topology_die_id(cpu) (cpu_data(cpu).cpu_die_id)
# 5 "/src/include/linux/topology.h" 1
#define topology_die_cpumask(cpu) cpumask_of(cpu)
#define OTHER 1
#undef OTHER
# 9 "/src/drivers/base/topology.c" 2
"""


def bundle(macros, symbols):
    return {"schema": BUNDLE_SCHEMA, "revision": "r", "config": {},
            "files": {"drivers/base/topology.c": {"build_returncode": 0, "macros": macros, "defined_symbols": symbols}}}


class TuMacroFactsTest(unittest.TestCase):
    def test_trace(self):
        t = _macro_trace(DD, ["topology_die_id", "topology_die_cpumask", "OTHER", "MISSING"], ["/src"])
        self.assertEqual(t["topology_die_id"]["origin"], "arch/x86/include/asm/topology.h")
        self.assertEqual(t["topology_die_cpumask"]["origin"], "include/linux/topology.h")
        self.assertFalse(t["OTHER"]["defined"])
        self.assertEqual([e[0] for e in t["OTHER"]["events"]], ["define", "undef"])
        self.assertFalse(t["MISSING"]["defined"])

    def test_queries(self):
        b = bundle(_macro_trace(DD, ["topology_die_id", "topology_die_cpumask"], ["/src"]), ["dev_attr_die_id", "die_id_show", "core_id_show"])
        self.assertEqual(query(b, {"kind": "macro_from_arch", "macro": "topology_die_id"}), (True, True))
        self.assertEqual(query(b, {"kind": "macro_from_arch", "macro": "topology_die_cpumask"}), (True, False))
        self.assertEqual(query(b, {"kind": "macro_defined", "macro": "topology_die_cpumask"}), (True, True))
        self.assertFalse(query(b, {"kind": "macro_defined", "macro": "untraced"})[0])
        self.assertEqual(query(b, {"kind": "object_defines_token", "token": "die_id"}), (True, True))
        self.assertEqual(query(b, {"kind": "object_defines_token", "token": "die_cpus"}), (True, False))
        self.assertEqual(query(b, {"kind": "object_defines_token", "token": "ie_id"}), (True, False))

    def test_needs_and_vocab(self):
        sources = {"include/linux/topology.h": "#ifndef topology_die_id\n#define topology_die_id(cpu) (-1)\n#endif\n",
                   "drivers/base/topology.c": "x\nstatic DEVICE_ATTR_RO(die_id);\n"}
        cands = [{"interface": "topology_die_id", "requirement": "arch defines topology_die_id natively",
                  "consumer": {"file": "drivers/base/topology.c", "line": 2}, "provider": {"file": "include/linux/topology.h", "line": 2}}]
        needs = tu_needs(cands, sources)
        self.assertEqual(needs["macros"], ["topology_die_id"])
        names = {q["name"] for q in build_tu_queries(cands, sources, needs, "drivers/base/topology.c")[0]["queries"]}
        self.assertTrue({"defined_topology_die_id", "arch_provides_topology_die_id", "emits_die_id", "builds_ok"} <= names)
        self.assertNotIn("emits_topology_die_id", names)

    def test_ranges_wildcards_directives(self):
        self.assertEqual(_what_lines("见第3-5及9、11行"), [3, 4, 5, 9, 11])
        self.assertEqual(_what_lines("lines 2-3"), [2, 3])
        self.assertEqual(_what_lines("第1-500行"), [])  # over RANGE_CAP
        self.assertEqual(_wildcards("topology_*_id 与 topology_*_cpumask", {"topology_die_id", "topology_core_cpumask", "topology_id"}),
                         {"topology_die_id", "topology_core_cpumask"})
        sources = {"include/linux/topology.h": "#include <asm/topology.h>\n#ifndef topology_die_id\n#define topology_die_id(cpu) (-1)\n#endif\n",
                   "drivers/base/topology.c": "x\nstatic DEVICE_ATTR_RO(die_id);\n"}
        cands = [{"interface": "topology_*_id", "requirement": "r",
                  "provider": {"file": "include/linux/topology.h", "line": 1, "what": "第2-3行回退"},
                  "consumer": {"file": "drivers/base/topology.c", "line": 1, "what": "第2行导出"}}]
        needs = tu_needs(cands, sources)
        self.assertEqual(needs["macros"], ["topology_die_id"])
        names = {q["name"] for q in build_tu_queries(cands, sources, needs, "drivers/base/topology.c")[0]["queries"]}
        self.assertIn("arch_provides_topology_die_id", names)
        self.assertIn("emits_die_id", names)
        self.assertFalse({"emits_include", "emits_asm", "emits_ifndef"} & names)


class MissingIntFactTest(unittest.TestCase):
    def test_missing_int_fact_is_unavailable_not_invalid(self):
        from linux_bug_analyze.candidate_bridge import evaluate_candidate
        formal = {"expressible": True, "config_symbols": ["thp"], "scope": {"symbol": "thp"},
                  "relation": {"op": "le", "args": [{"symbol": "a"}, {"symbol": "b"}]}}
        r = evaluate_candidate(formal, {"thp": False, "b": 8}, context="c", revision="r", basis="compiled_object", documents={}, reviewed=True)
        self.assertEqual(r, {"status": "facts_unavailable", "missing": ["a"]})


class ValueAndOptimizedFactsTest(unittest.TestCase):
    def test_returns_only_zero(self):
        folded = ";; Function f (f, funcdef_no=1)\n\nbool f (int x)\n{\n  <bb 2> [local count: 1073741824]:\n  return 0;\n\n}\n"
        live = ";; Function f (f, funcdef_no=1)\n\nbool f (int x)\n{\n  <bb 2> :\n  _1 = x > 3;\n  return _1;\n\n}\n"
        self.assertTrue(_returns_only_zero(folded))
        self.assertFalse(_returns_only_zero(live))
        debug = folded.replace("  return 0;", "  # DEBUG BEGIN_STMT\n  # DEBUG x => NULL\n  return 0;")
        self.assertTrue(_returns_only_zero(debug))
        self.assertEqual(_body_statements(";; Function p (p)\nlong long int p ()\n{\n  <bb 2> [local count: 1]:\n  return 11;\n\n}\n"), ["return 11;"])
        b = {"schema": BUNDLE_SCHEMA, "revision": "r", "config": {}, "files": {"mm/shmem.c": {
            "optimized_records": {"f": folded}, "macro_values": {"A": {"answered": True, "value": 13}, "B": {"answered": False, "reason": "probe_compile_failed"}}}}}
        self.assertEqual(query(b, {"kind": "returns_only_zero", "function": "f"}), (True, True))
        self.assertFalse(query(b, {"kind": "returns_only_zero", "function": "g"})[0])
        self.assertEqual(query(b, {"kind": "macro_value", "macro": "A"}), (True, 13))
        self.assertEqual(query(b, {"kind": "macro_value", "macro": "B"}), (False, "probe_compile_failed"))

    def test_trace_all_needs(self):
        sources = {"mm/shmem.c": "bool shmem_is_huge(int i)\n{\n\treturn i > HPAGE_PMD_ORDER;\n}\n"}
        cands = [{"interface": "HPAGE_PMD_ORDER", "requirement": "shmem_is_huge must not allow orders above MAX_PAGECACHE_ORDER",
                  "consumer": {"file": "mm/shmem.c", "line": 3}}]
        needs = tu_needs(cands, sources, trace_all=True)
        self.assertIn("HPAGE_PMD_ORDER", needs["macros"])
        self.assertEqual(needs["values"], ["HPAGE_PMD_ORDER", "MAX_PAGECACHE_ORDER"])
        self.assertEqual(needs["functions"], ["shmem_is_huge"])
        names = {q["name"] for q in build_tu_queries(cands, sources, dict(needs, macros=["HPAGE_PMD_ORDER"]), "mm/shmem.c")[0]["queries"]}
        self.assertTrue({"value_HPAGE_PMD_ORDER", "value_MAX_PAGECACHE_ORDER", "shmem_is_huge_returns_only_zero", "defined_HPAGE_PMD_ORDER"} <= names)


if __name__ == "__main__":
    unittest.main()
