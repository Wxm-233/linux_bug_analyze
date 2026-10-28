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

    def test_m2b_switches(self):
        direct_c = TOPOLOGY_C + "void f(void)\n{\n\tg(topology_die_id(0));\n}\n"
        self.assertIn("direct", {i["kind"] for i in f1_instances(direct_c, traces(X86, S390))})
        self.assertEqual({i["kind"] for i in f1_instances(direct_c, traces(X86, S390), direct=False)}, {"pasted"})
        x86 = '# 1 "/s/arch/x86/include/asm/pgtable_64_types.h" 1\n#define PMD_SHIFT 21\n#define PAGE_SHIFT 12\n' + HUGE
        arm = '# 1 "/s/arch/arm64/include/asm/pgtable-hwdef.h" 1\n#define PMD_SHIFT 29\n#define PAGE_SHIFT 16\n' + HUGE
        side = '#define MAX_OTHER_ORDER (PAGE_SHIFT + 1)\n'
        loose = {(i["geometry"], i["limit"]) for i in f2_instances(SHMEM_C, traces(x86 + side, arm + side))}
        tight = {(i["geometry"], i["limit"]) for i in f2_instances(SHMEM_C, traces(x86 + side, arm + side), limit_contains_g=True)}
        self.assertIn(("HPAGE_PMD_ORDER", "MAX_OTHER_ORDER"), loose)  # chains meet only at PAGE_SHIFT
        self.assertNotIn(("HPAGE_PMD_ORDER", "MAX_OTHER_ORDER"), tight)
        self.assertIn(("HPAGE_PMD_ORDER", "MAX_PAGECACHE_ORDER"), tight)

    def test_m2c_fallback_criterion(self):
        from linux_bug_analyze.kernel_facts import annotate_fallbacks, is_fallback_definition
        header = ["#ifndef topology_die_id", "#define topology_die_id(cpu) ((void)(cpu), -1)", "#endif",
                  "#ifndef topology_x", "#define topology_x 1", "#define topology_y 2", "#endif"]
        self.assertTrue(is_fallback_definition(header, 2, "topology_die_id"))
        self.assertTrue(is_fallback_definition(header, 5, "topology_x"))
        self.assertFalse(is_fallback_definition(header, 6, "topology_y"))  # guard names another macro
        import tempfile, os
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "include/linux"))
            with open(os.path.join(root, "include/linux/topology.h"), "w") as fh:
                fh.write("\n" * 28 + "#ifndef topology_die_id\n#define topology_die_id(cpu) ((void)(cpu), -1)\n#endif\n")
            with open(os.path.join(root, "include/linux/arch_topology.h"), "w") as fh:
                fh.write("#ifdef CONFIG_GENERIC_ARCH_TOPOLOGY\n#define topology_die_id(cpu) (cpu_topology[cpu].die_id)\n#endif\n")
            gen = _macro_trace(S390, None, ["/s"])  # final definition at include/linux/topology.h:30
            shared = _macro_trace('# 1 "/s/include/linux/arch_topology.h" 1\n\n#define topology_die_id(cpu) (cpu_topology[cpu].die_id)\n', None, ["/s"])
            annotate_fallbacks(gen, [root])
            annotate_fallbacks(shared, [root])
        self.assertTrue(gen["topology_die_id"]["fallback"])
        self.assertFalse(shared["topology_die_id"]["fallback"])
        tr = {"a": gen, "b": shared}
        self.assertTrue(f1_instances(TOPOLOGY_C, tr, direct=False, provided="fallback"))   # fallback vs shared provider
        self.assertFalse(f1_instances(TOPOLOGY_C, {"a": shared, "b": shared}, direct=False, provided="fallback"))
        inst = f1_instances(TOPOLOGY_C, tr, direct=False, provided="fallback")[0]
        self.assertEqual({q["kind"] for q in queries(inst)} - {"constant", "object_defines_token"}, {"macro_provided"})

    def test_m3_f3_and_f1d(self):
        from linux_bug_analyze.check_families import f1d_instances, f3_instances, placeholder_fallback
        src = ("#ifndef __HAVE_ARCH_STRNCMP\n/* local */\nint strncmp(const char *a, const char *b, size_t n)\n{\n\treturn 0;\n}\n#endif\n"
               "#ifndef FOO_H\nint notfeature(void)\n{\n\treturn 1;\n}\n#endif\n"
               "#ifndef __HAVE_ARCH_STRSTR\n#else\nchar *strstr(const char *a, const char *b)\n{\n\treturn 0;\n}\n#endif\n")
        inst = f3_instances(src, "drivers/firmware/efi/libstub/string.c")
        self.assertEqual([(i["macro"], i["functions"], i["isolated"]) for i in inst], [("__HAVE_ARCH_STRNCMP", ["strncmp"], True)])
        c = contract(inst[0])
        kw = dict(context="t", revision="r", basis="compiled_object", documents=DOCS, reviewed=True)
        self.assertEqual(evaluate_candidate(c, {"build_context": True, "defined___HAVE_ARCH_STRNCMP": True, "emits_strncmp": False}, **kw)["relation_at_observation"], "violated")
        self.assertEqual(evaluate_candidate(c, {"build_context": True, "defined___HAVE_ARCH_STRNCMP": True, "emits_strncmp": True}, **kw)["relation_at_observation"], "satisfied")
        self.assertEqual(evaluate_candidate(c, {"build_context": True, "defined___HAVE_ARCH_STRNCMP": False, "emits_strncmp": False}, **kw)["relation_at_observation"], "satisfied")
        self.assertEqual({q["kind"] for q in queries(inst[0])}, {"constant", "macro_defined", "object_defines_token"})
        ph = {"a": {"topology_die_id": {"defined": True, "fallback": True, "text": "(cpu) ((void)(cpu), -1)", "define": "#define topology_die_id(cpu) ((void)(cpu), -1)"},
                    "flush_x": {"defined": True, "fallback": True, "text": "(p) do { } while (0)", "define": "#define flush_x(p) do { } while (0)"},
                    "mask_x": {"defined": True, "fallback": True, "text": "(cpu) cpumask_of(cpu)", "define": "#define mask_x(cpu) cpumask_of(cpu)"}},
              "b": {"topology_die_id": {"defined": True, "fallback": False}, "flush_x": {"defined": True, "fallback": False}, "mask_x": {"defined": True, "fallback": False}}}
        self.assertTrue(placeholder_fallback("topology_die_id", ph))
        self.assertFalse(placeholder_fallback("flush_x", ph))
        self.assertFalse(placeholder_fallback("mask_x", ph))
        body = "int show(int cpu)\n{\n\treturn topology_die_id(cpu) + mask_x(cpu) + flush_x(0);\n}\n"
        self.assertEqual([(i["site"], i["macros"]) for i in f1d_instances(body, ph)], [("show", ["topology_die_id"])])

    def test_many_gates_stay_within_core_arity(self):
        gates = ["f%d" % n for n in range(17)]
        c = contract({"family": "F2", "geometry": "G_SIZE", "limit": "MAX_G_SIZE", "gates": gates})
        facts = dict({"build_context": True, "value_G_SIZE": 4, "value_MAX_G_SIZE": 2}, **{g + "_returns_only_zero": False for g in gates})
        kw = dict(context="t", revision="r", basis="compiled_object", documents=DOCS, reviewed=True)
        self.assertEqual(evaluate_candidate(c, facts, **kw)["relation_at_observation"], "violated")
        self.assertEqual(evaluate_candidate(c, dict(facts, f16_returns_only_zero=True), **kw)["relation_at_observation"], "satisfied")


if __name__ == "__main__":
    unittest.main()
