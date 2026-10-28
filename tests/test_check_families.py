import unittest

from linux_bug_analyze.candidate_bridge import evaluate_candidate
from linux_bug_analyze.check_families import contract, f1_instances, f2_instances, queries
from linux_bug_analyze.kernel_facts import _macro_trace

TOPOLOGY_C = """#define define_id_show_func(name) \\
static ssize_t name##_show(struct device *dev, char *buf) \\
{ return sysfs_emit(buf, "%d\\n", topology_##name(dev->id)); }
define_id_show_func(die_id);
#define define_siblings_read_func(name, mask) \\
static ssize_t name##_read(struct file *f) \\
{ return cpumap_print(topology_##mask(0)); }
define_siblings_read_func(die_cpus, die_cpumask);
define_id_show_func(book_id);
"""
X86 = ('# 1 "/s/arch/x86/include/asm/topology.h" 1\n#define topology_die_id(cpu) (cpu_data(cpu).cpu_die_id)\n'
       '#define topology_die_cpumask(cpu) (per_cpu(cpu_die_map, cpu))\n')
S390 = ('# 1 "/s/arch/s390/include/asm/topology.h" 1\n#define topology_book_id(cpu) (cpu_topology[cpu].book_id)\n'
        '# 30 "/s/include/linux/topology.h"\n#define topology_die_id(cpu) ((void)(cpu), -1)\n#define topology_die_cpumask(cpu) cpumask_of(cpu)\n')

SHMEM_C = """bool shmem_is_huge(int i)
{
\treturn i < HPAGE_PMD_NR;
}
void shmem_alloc(void)
{
\talloc(HPAGE_PMD_ORDER);
}
"""
HUGE = ('# 1 "/s/include/linux/huge_mm.h" 1\n#define HPAGE_PMD_ORDER (HPAGE_PMD_SHIFT-PAGE_SHIFT)\n#define HPAGE_PMD_NR (1<<HPAGE_PMD_ORDER)\n'
        '#define HPAGE_PMD_SHIFT PMD_SHIFT\n# 1 "/s/include/linux/pagemap.h" 1\n#define PREFERRED_MAX_PAGECACHE_ORDER HPAGE_PMD_ORDER\n'
        '#define MAX_XAS_ORDER 11\n#define MAX_PAGECACHE_ORDER min(MAX_XAS_ORDER, PREFERRED_MAX_PAGECACHE_ORDER)\n')


DOCS = {"evidence": {"context_revision": "r", "path": "bundle.json", "start_line": 1, "end_line": 1, "sha256": "0" * 64}}


def traces(*texts):
    return {"c%d" % i: _macro_trace(t, None, ["/s"]) for i, t in enumerate(texts)}


class CheckFamiliesTest(unittest.TestCase):
    def test_f1(self):
        inst = f1_instances(TOPOLOGY_C, traces(X86, S390))
        sites = {i["site"]: i for i in inst}
        self.assertEqual(sites["define_id_show_func(die_id)"]["entities"], ["die_id"])
        self.assertEqual(sites["define_siblings_read_func(die_cpus, die_cpumask)"]["entities"], ["die_cpus"])
        self.assertNotIn("define_id_show_func(book_id)", sites)  # s390-only, no generic fallback
        c = contract(sites["define_id_show_func(die_id)"])
        names = {q["name"] for q in queries(sites["define_id_show_func(die_id)"])}
        self.assertEqual(names, {"build_context", "emits_die_id", "arch_provides_topology_die_id"})
        kw = dict(context="t", revision="r", basis="compiled_object", documents=DOCS, reviewed=True)
        self.assertEqual(evaluate_candidate(c, {"build_context": True, "emits_die_id": True, "arch_provides_topology_die_id": False}, **kw)["relation_at_observation"], "violated")
        self.assertEqual(evaluate_candidate(c, {"build_context": True, "emits_die_id": False, "arch_provides_topology_die_id": False}, **kw)["relation_at_observation"], "satisfied")

    def test_f2(self):
        x86 = '# 1 "/s/arch/x86/include/asm/pgtable_64_types.h" 1\n#define PMD_SHIFT 21\n#define PAGE_SHIFT 12\n' + HUGE
        arm = '# 1 "/s/arch/arm64/include/asm/pgtable-hwdef.h" 1\n#define PMD_SHIFT 29\n#define PAGE_SHIFT 16\n' + HUGE
        inst = f2_instances(SHMEM_C, traces(x86, arm))
        pair = [i for i in inst if (i["geometry"], i["limit"]) == ("HPAGE_PMD_ORDER", "MAX_PAGECACHE_ORDER")]
        self.assertEqual(len(pair), 1)
        self.assertEqual(pair[0]["gates"], ["shmem_alloc", "shmem_is_huge"])
        c = contract(pair[0])
        kw = dict(context="t", revision="r", basis="compiled_object", documents=DOCS, reviewed=True)
        facts = {"build_context": True, "value_HPAGE_PMD_ORDER": 13, "value_MAX_PAGECACHE_ORDER": 11,
                 "shmem_alloc_returns_only_zero": False, "shmem_is_huge_returns_only_zero": False}
        self.assertEqual(evaluate_candidate(c, facts, **kw)["relation_at_observation"], "violated")
        self.assertEqual(evaluate_candidate(c, dict(facts, shmem_is_huge_returns_only_zero=True), **kw)["relation_at_observation"], "satisfied")

    def test_many_gates_stay_within_core_arity(self):
        gates = ["f%d" % n for n in range(17)]
        c = contract({"family": "F2", "geometry": "G_SIZE", "limit": "MAX_G_SIZE", "gates": gates})
        facts = dict({"build_context": True, "value_G_SIZE": 4, "value_MAX_G_SIZE": 2}, **{g + "_returns_only_zero": False for g in gates})
        kw = dict(context="t", revision="r", basis="compiled_object", documents=DOCS, reviewed=True)
        self.assertEqual(evaluate_candidate(c, facts, **kw)["relation_at_observation"], "violated")
        self.assertEqual(evaluate_candidate(c, dict(facts, f16_returns_only_zero=True), **kw)["relation_at_observation"], "satisfied")


if __name__ == "__main__":
    unittest.main()
