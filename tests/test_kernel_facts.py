import json
import tempfile
import unittest
from pathlib import Path

from linux_bug_analyze.kernel_facts import BUNDLE_SCHEMA, _cfg_record, _function_body, _split_objdump, query

OBJDUMP = """
0000000000000000 <f>:
   0:	sethi  %hi(0), %o1
			0: R_SPARC_HI22	nr_cpu_ids
   4:	call  4 <f+0x4>
			4: R_SPARC_WDISP30	__bitmap_weight
0000000000000040 <g>:
  40:	retl
"""

PRE = """int x;
static int helper(int a);
static int helper(int a)
{
 if (a) { return (nr_cpu_ids); }
 return 0;
}
void other(void) { helper(1); }
"""


def bundle():
    return {"schema": BUNDLE_SCHEMA, "revision": "r", "spec": {"arch": "sparc64"}, "config": {"CONFIG_NR_CPUS": 4096, "CONFIG_SMP": True},
            "config_sha256": "0" * 64,
            "files": {"a.c": {"functions": _split_objdump(OBJDUMP), "bodies": {"helper": _function_body(PRE, "helper"), "missing": None},
                              "cfg_records": {}}}}


class KernelFactsTest(unittest.TestCase):
    def test_helpers(self):
        funcs = _split_objdump(OBJDUMP)
        self.assertEqual(sorted(funcs), ["f", "g"])
        body = _function_body(PRE, "helper")
        self.assertTrue(body.startswith("static int helper(int a)\n{") and body.endswith("}"))
        self.assertIsNone(_function_body(PRE, "absent"))
        dump = ";; Function a (a, funcdef_no=1)\nA\n;; Function b (b, funcdef_no=2)\nB\n"
        self.assertEqual(_cfg_record(dump, "b"), ";; Function b (b, funcdef_no=2)\nB\n")

    def test_queries_answer_or_omit(self):
        b = bundle()
        self.assertEqual(query(b, {"kind": "config", "option": "CONFIG_NR_CPUS"}), (True, 4096))
        self.assertEqual(query(b, {"kind": "config", "option": "CONFIG_X"})[0], False)
        self.assertEqual(query(b, {"kind": "config", "option": "CONFIG_X", "absent_is_false": True}), (True, False))
        self.assertEqual(query(b, {"kind": "defined", "function": "g"}), (True, True))
        self.assertEqual(query(b, {"kind": "references", "function": "f", "symbol": "nr_cpu_ids"}), (True, True))
        self.assertEqual(query(b, {"kind": "references", "function": "g", "symbol": "nr_cpu_ids"}), (True, False))
        self.assertEqual(query(b, {"kind": "references", "function": "inlined", "symbol": "x"})[0], False)
        self.assertEqual(query(b, {"kind": "expansion_contains", "function": "helper", "text": "(nr_cpu_ids)"}), (True, True))
        self.assertEqual(query(b, {"kind": "expansion_contains", "function": "missing", "text": "x"})[0], False)
        self.assertEqual(query(b, {"kind": "direct_write", "function": "f", "target": "x"})[0], False)
        self.assertEqual(query(b, {"kind": "guess"})[0], False)

    def test_adapter_omits_unanswered(self):
        from linux_bug_analyze.adapters import kernel_source
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bundle.json"
            path.write_text(json.dumps(bundle()), encoding="utf-8")
            old = kernel_source.ROOT
            kernel_source.ROOT = Path(tmp)
            try:
                out = kernel_source.adapt({"bundle": "bundle.json", "queries": [
                    {"name": "nr", "kind": "config", "option": "CONFIG_NR_CPUS"},
                    {"name": "refs", "kind": "references", "function": "inlined", "symbol": "x"}]})
            finally:
                kernel_source.ROOT = old
        self.assertEqual(out["values"], {"nr": 4096})
        self.assertEqual(out["observation"]["unanswered"], {"refs": "function_not_in_object"})


if __name__ == "__main__":
    unittest.main()
