import unittest

from linux_bug_analyze.kernel_facts import BUNDLE_SCHEMA, _macro_trace, query
from linux_bug_analyze.variation_points import arch_names, covers, enumerate_sites, fix_ranges, select_sites

SRC = """#include <linux/mm.h>
#ifdef __HAVE_ARCH_STRNCMP
#define X 1
#endif
int f(int order)
{
	if (order > MAX_ORDER)
		return 0;
	if (IS_ENABLED(CONFIG_S390))
		hook();
	return topology_die_id(order) + local(1);
}
static int local(int a)
{
	return a;
}
#if BITS_PER_LONG < 64
int g(void)
{
	return 0;
}
#endif
"""
X86 = '# 1 "/s/arch/x86/include/asm/topology.h" 1\n#define topology_die_id(cpu) (cpu)\n# 1 "/s/include/linux/mmzone.h" 1\n#define MAX_ORDER 10\n'
S390 = '# 1 "/s/include/linux/topology.h" 1\n#define topology_die_id(cpu) (-1)\n# 1 "/s/include/linux/mmzone.h" 1\n#define MAX_ORDER 10\n'


class VariationPointsTest(unittest.TestCase):
    def test_sites(self):
        traces = {"x86_64": _macro_trace(X86, None, ["/s"]), "s390": _macro_trace(S390, None, ["/s"])}
        tu = {"x86_64": {"hook": "arch/x86/kernel/hook.c"}, "s390": {"hook": "include/linux/hook.h"}}
        sites = enumerate_sites(SRC, traces, tu, arch_names(["x86", "s390", "arm64"]))
        by = {(s["type"], s["key"]) for s in sites}
        self.assertIn(("V2", "2:__HAVE_ARCH_STRNCMP"), by)
        self.assertIn(("V2", "17:BITS_PER_LONG"), by)
        self.assertIn(("V5", "9:CONFIG_S390"), by)
        self.assertIn(("V4", "7:MAX_ORDER"), by)
        self.assertIn(("V3", "hook"), by)
        self.assertIn(("V1", "topology_die_id"), by)
        self.assertNotIn(("V3", "local"), by)          # defined in this file
        v2 = next(s for s in sites if s["key"] == "17:BITS_PER_LONG")
        self.assertEqual((v2["lines"][0], v2["lines"][-1]), (17, 22))
        sel = select_sites(sites, cap=3)
        self.assertEqual([s["type"] for s in sel], ["V2", "V2", "V5"])

    def test_pasted_macro_lines(self):
        src = ("#define show(name) \\\nint name##_show(void) \\\n{ \\\n\treturn topology_##name(0); \\\n}\n"
               "#define other(x) \\\n\tx##_y\n"
               "show(die_id);\nshow(core_id);\n")
        traces = {"x86_64": _macro_trace(X86, None, ["/s"]), "s390": _macro_trace(S390, None, ["/s"])}
        sites = enumerate_sites(src, traces, {}, arch_names(["x86", "s390"]))
        v1 = next(s for s in sites if s["type"] == "V1" and s["key"] == "topology_die_id")
        self.assertEqual(v1["lines"], [8])

    def test_coverage_and_ranges(self):
        self.assertEqual(fix_ranges("@@ -10,2 +10,3 @@\n@@ -40,0 +41,4 @@\n"), [(10, 11), (40, 40)])
        self.assertTrue(covers({"lines": [16]}, [(10, 11)]))
        self.assertFalse(covers({"lines": [17]}, [(10, 11)]))

    def test_expr_value_query(self):
        b = {"schema": BUNDLE_SCHEMA, "revision": "r", "config": {}, "files": {"a.c": {"expr_values": {
            "IS_ENABLED(CONFIG_S390)": {"answered": True, "value": 0}, "x + y": {"answered": False, "reason": "not_an_integer_constant"}}}}}
        self.assertEqual(query(b, {"kind": "expr_value", "expr": "IS_ENABLED(CONFIG_S390)"}), (True, 0))
        self.assertEqual(query(b, {"kind": "expr_value", "expr": "x + y"}), (False, "not_an_integer_constant"))


if __name__ == "__main__":
    unittest.main()
