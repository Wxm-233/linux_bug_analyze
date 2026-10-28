import unittest

from linux_bug_analyze.candidate_bridge import _wildcards, _what_lines, build_tu_queries, tu_needs
from linux_bug_analyze.kernel_facts import BUNDLE_SCHEMA, _macro_trace, query

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


if __name__ == "__main__":
    unittest.main()
