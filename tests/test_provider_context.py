import unittest
from collections import Counter

from linux_bug_analyze.kernel_facts import _macro_trace
from linux_bug_analyze.provider_context import consumed, guard_configs, pasted_names, render, select, sparse_sources

TOPOLOGY_C = """
#define define_id_show_func(name) \\
static ssize_t name##_show(struct device *dev, char *buf) \\
{ return sysfs_emit(buf, "%d\\n", topology_##name(dev->id)); }
define_id_show_func(die_id);
define_id_show_func(core_id);
#ifdef CONFIG_SCHED_BOOK
#endif
#if defined(CONFIG_SCHED_BOOK) && defined(CONFIG_X)
#endif
"""

X86 = """# 1 "/s/arch/x86/include/asm/topology.h" 1
#define topology_die_id(cpu) (cpu_data(cpu).cpu_die_id)
# 10 "/s/include/linux/topology.h" 1
#define topology_core_id(cpu) ((void)(cpu), 0)
"""
S390 = """# 10 "/s/include/linux/topology.h" 1
#define topology_core_id(cpu) ((void)(cpu), 0)
# 30 "/s/include/linux/topology.h"
#define topology_die_id(cpu) ((void)(cpu), -1)
"""


class ProviderContextTest(unittest.TestCase):
    def test_trace_lines(self):
        t = _macro_trace(X86, None, ["/s"])
        self.assertEqual((t["topology_die_id"]["origin"], t["topology_die_id"]["line"]), ("arch/x86/include/asm/topology.h", 1))
        self.assertEqual(t["topology_core_id"]["line"], 10)
        self.assertEqual(_macro_trace(S390, None, ["/s"])["topology_die_id"]["line"], 30)

    def test_paste_and_guards(self):
        self.assertEqual(set(pasted_names(TOPOLOGY_C)), {"topology_die_id", "topology_core_id", "die_id_show", "core_id_show"})
        self.assertEqual(guard_configs(TOPOLOGY_C), ["SCHED_BOOK", "X"])
        self.assertEqual(consumed(TOPOLOGY_C)["topology_die_id"], 1)

    def test_select_render(self):
        traces = {"x86_64": _macro_trace(X86, None, ["/s"]), "s390": _macro_trace(S390, None, ["/s"])}
        sel = select(traces, Counter({"topology_die_id": 1, "topology_core_id": 1}))
        self.assertEqual([s["macro"] for s in sel], ["topology_die_id"])  # core_id: same generic text everywhere
        text, stats = render(sel, traces, {})
        self.assertIn("x86_64: arch/x86/include/asm/topology.h:1", text)
        self.assertIn("s390: include/linux/topology.h:30", text)
        shown, _ = render(sel, traces, {"include/linux/topology.h": "\n" * 40})
        self.assertIn("(shown in the sources above)", shown)
        sparse = sparse_sources(sel, traces)
        self.assertEqual(sparse["arch/x86/include/asm/topology.h"].splitlines()[0], "#define topology_die_id(cpu) (cpu_data(cpu).cpu_die_id)")

    def test_chain(self):
        a = '# 1 "/s/include/linux/huge_mm.h" 1\n#define HPAGE_PMD_ORDER (HPAGE_PMD_SHIFT-PAGE_SHIFT)\n#define HPAGE_PMD_SHIFT PMD_SHIFT\n'
        x = '# 1 "/s/arch/x86/include/asm/pgtable_64_types.h" 1\n#define PMD_SHIFT 21\n#define PAGE_SHIFT 12\n' + a
        y = '# 1 "/s/arch/arm64/include/asm/pgtable-hwdef.h" 1\n#define PMD_SHIFT 21\n#define PAGE_SHIFT 12\n' + a
        traces = {"x86_64": _macro_trace(x, None, ["/s"]), "arm64": _macro_trace(y, None, ["/s"])}
        sel = select(traces, Counter({"HPAGE_PMD_ORDER": 2}))
        self.assertEqual(sel[0]["macro"], "HPAGE_PMD_ORDER")
        self.assertEqual(set(sel[0]["chain"]), {"PMD_SHIFT", "PAGE_SHIFT"})


if __name__ == "__main__":
    unittest.main()
