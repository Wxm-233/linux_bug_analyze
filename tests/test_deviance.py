import unittest

from linux_bug_analyze.deviance import a1_integer_minority, a2_sibling_provenance, a3_condition_minority, evaluate, rank
from linux_bug_analyze.kernel_facts import _macro_trace


def tr(defs):
    t = _macro_trace('# 1 "/s/include/x.h" 1\n' + "".join("#define %s\n" % d for d in defs), None, ["/s"])
    return t


class DevianceTest(unittest.TestCase):
    def test_evaluate(self):
        t = tr(["PAGE_SHIFT 16", "PMD_SHIFT (PAGE_SHIFT + 13)", "HPAGE_PMD_ORDER (PMD_SHIFT-PAGE_SHIFT)", "MAX_XAS_ORDER (6 * 2 - 1)",
                "MAX_PAGECACHE_ORDER min(MAX_XAS_ORDER, HPAGE_PMD_ORDER)", "SZ 4096UL", "B BIT(3)", "F(x) (x)", "CAST ((unsigned long)8)"])
        self.assertEqual(evaluate("HPAGE_PMD_ORDER", t), 13)
        self.assertEqual(evaluate("MAX_PAGECACHE_ORDER", t), 11)
        self.assertEqual(evaluate("SZ / 2", t), 2048)
        self.assertEqual(evaluate("B", t), 8)
        self.assertEqual(evaluate("CAST", t), 8)
        self.assertIsNone(evaluate("F", t))
        self.assertIsNone(evaluate("UNKNOWN + 1", t))
        self.assertEqual(evaluate("defined(PAGE_SHIFT) && PAGE_SHIFT > 12", t, defined_only=True), 1)

    def test_a1_minority(self):
        src = "int f(void) { return HPAGE_PMD_ORDER + LIMIT_ORDER; }\n"
        traces = {"c%d" % i: tr(["HPAGE_PMD_ORDER %d" % (13 if i == 0 else 9), "LIMIT_ORDER 11"]) for i in range(6)}
        c = [x for x in a1_integer_minority(src, traces) if x["key"] == "HPAGE_PMD_ORDER?LIMIT_ORDER"][0]
        self.assertEqual((c["majority"], c["minority"], c["score"]), ("<", ["c0"], 4))

    def test_a1_p0b_switches(self):
        src = "int f(void) { return HPAGE_PMD_ORDER + EFAULT; }\n"
        defs = lambda o: ["PAGE_SHIFT %d" % (16 if o else 12), "HPAGE_PMD_ORDER %d" % (13 if o else 9), "EFAULT 11",
                          "PREFERRED_MAX_ORDER HPAGE_PMD_ORDER", "MAX_PC_ORDER min(11, PREFERRED_MAX_ORDER)"]
        traces = {"c%d" % i: tr(defs(i == 0)) for i in range(6)}
        plain = {x["key"] for x in a1_integer_minority(src, traces)}
        self.assertIn("EFAULT?HPAGE_PMD_ORDER", plain)                 # cross-unit noise in P0
        self.assertNotIn("HPAGE_PMD_ORDER?MAX_PC_ORDER", plain)        # limit not in the forward pool
        amended = {x["key"]: x for x in a1_integer_minority(src, traces, same_unit=True, reverse_limits=True)}
        self.assertNotIn("EFAULT?HPAGE_PMD_ORDER", amended)
        self.assertEqual(amended["HPAGE_PMD_ORDER?MAX_PC_ORDER"]["minority"], ["c0"])

    def test_a2_and_a3(self):
        src = ("#define show(name) \\\nint name##_show(void) { return topology_##name(0); }\n"
               "show(die_id);\nshow(core_id);\nshow(pkg_id);\n#ifndef __HAVE_ARCH_STRNCMP\nint strncmp(void);\n#endif\n")
        native = '# 1 "/s/arch/x/include/asm/topology.h" 1\n#define topology_core_id(c) 0\n#define topology_pkg_id(c) 0\n'
        fb = _macro_trace(native + '# 9 "/s/include/linux/topology.h"\n#define topology_die_id(c) (-1)\n', None, ["/s"])
        for rec in fb.values():
            rec["fallback"] = rec.get("origin", "").startswith("include/")
        good = _macro_trace(native + '#define topology_die_id(c) 1\n#define __HAVE_ARCH_STRNCMP 1\n', None, ["/s"])
        for rec in good.values():
            rec["fallback"] = False
        traces = {"a": fb, "b": good, "c": good}
        a2 = a2_sibling_provenance(src, traces)
        self.assertEqual([(x["key"], x["minority"], x["score"]) for x in a2], [("show(die_id)", ["a"], 2)])
        a3 = a3_condition_minority(src, traces, {"X"})
        self.assertEqual([(x["key"], x["minority"]) for x in a3], [("6:#ifndef __HAVE_ARCH_STRNCMP", ["a"])])
        self.assertEqual(rank(a2 + a3, top=1)[0]["family"], "A2")


if __name__ == "__main__":
    unittest.main()
