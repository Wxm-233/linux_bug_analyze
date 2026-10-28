import unittest

from linux_bug_analyze.candidate_bridge import arch_needs, build_arch_queries
from linux_bug_analyze.kernel_facts import TREE_SCHEMA, _int_value, tree_query

TREE = {"schema": TREE_SCHEMA, "arches": ["alpha", "x86"], "facts": {
    "alpha": {"kconfig_selects": {"ARCH_SUPPORTS_MEMORY_FAILURE": []},
              "uapi": {"asm/mman.h": {"returncode": 0, "macros": {"MADV_HWPOISON": {"defined": False, "text": None, "value": None},
                                                                   "MADV_DONTNEED": {"defined": True, "text": "6", "value": 6}}}}},
    "x86": {"kconfig_selects": {"ARCH_SUPPORTS_MEMORY_FAILURE": ["select ARCH_SUPPORTS_MEMORY_FAILURE if X86_MCE"]},
            "uapi": {"asm/mman.h": {"returncode": 1, "macros": {}}}}}}


class ArchFactsTest(unittest.TestCase):
    def test_int_value(self):
        self.assertEqual(_int_value("(0x10UL)"), 16)
        self.assertEqual(_int_value(" 100 "), 100)
        self.assertIsNone(_int_value("FOO + 1"))

    def test_tree_query(self):
        self.assertEqual(tree_query(TREE, "x86", {"kind": "kconfig_selects", "symbol": "ARCH_SUPPORTS_MEMORY_FAILURE"}), (True, True))
        self.assertEqual(tree_query(TREE, "alpha", {"kind": "kconfig_selects", "symbol": "ARCH_SUPPORTS_MEMORY_FAILURE"}), (True, False))
        self.assertEqual(tree_query(TREE, "alpha", {"kind": "uapi_defined", "header": "asm/mman.h", "macro": "MADV_HWPOISON"}), (True, False))
        self.assertEqual(tree_query(TREE, "alpha", {"kind": "uapi_value", "header": "asm/mman.h", "macro": "MADV_DONTNEED"}), (True, 6))
        self.assertFalse(tree_query(TREE, "alpha", {"kind": "uapi_value", "header": "asm/mman.h", "macro": "MADV_HWPOISON"})[0])
        self.assertEqual(tree_query(TREE, "x86", {"kind": "uapi_defined", "header": "asm/mman.h", "macro": "MADV_HWPOISON"})[1], "uapi_preprocess_failed")
        self.assertFalse(tree_query(TREE, "mips", {"kind": "kconfig_selects", "symbol": "X"})[0])

    def test_needs_and_queries(self):
        sources = {"mm/madvise.c": "case MADV_HWPOISON:\n", "arch/alpha/include/uapi/asm/mman.h": "#define MADV_DONTNEED 6\n"}
        cands = [{"interface": "MADV_HWPOISON", "requirement": "provide MADV_HWPOISON when CONFIG_MEMORY_FAILURE",
                  "consumer": {"file": "mm/madvise.c", "line": 1}}]
        needs = arch_needs(cands, sources)
        self.assertEqual(needs["headers"], ["asm/mman.h"])
        self.assertIn("MADV_HWPOISON", needs["macros"])
        self.assertEqual(needs["config_symbols"], ["MEMORY_FAILURE"])
        br = build_arch_queries(cands, sources, needs, {"MEMORY_FAILURE": ["depends on ARCH_SUPPORTS_MEMORY_FAILURE"]}, "mm/madvise.c")
        names = {q["name"] for q in br[0]["queries"]}
        self.assertTrue({"build_context", "defines_MADV_HWPOISON", "arch_selects_ARCH_SUPPORTS_MEMORY_FAILURE", "config_memory_failure", "builds_ok"} <= names)
        both = arch_needs(cands, dict(sources, **{"include/uapi/asm-generic/mman-common.h": ""}))
        self.assertEqual(both["headers"], ["asm/mman.h", "asm/mman-common.h"])  # arch-overridable entry header first
        q = {x["name"]: x for x in build_arch_queries(cands, sources, both, {}, None)[0]["queries"]}
        self.assertEqual(q["defines_MADV_HWPOISON"]["header"], "asm/mman.h")


if __name__ == "__main__":
    unittest.main()
