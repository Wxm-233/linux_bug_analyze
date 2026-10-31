import tempfile
import unittest
from pathlib import Path

from linux_bug_analyze.candidate_bridge import (build_queries, enclosing, evaluate_candidate, formalization_prompt,
                                                function_spans, identifiers, parse_formalizations)
from linux_bug_analyze.contract_envelope import document
from linux_bug_analyze.kernel_facts import _top_level_functions

SRC = """static int helper(int a)
{
\treturn a + nr_cpu_ids;
}

void consumer(void)
{
\tint x = helper(2);
\tif (x > 1)
\t\tuse_value(x);
}
"""


LONG = """int done;
/*
 * Handle {get,set}_context operations
 */
static pte_t get_clear_contig(struct mm_struct *mm,
\t\t\t     unsigned long addr,
\t\t\t     pte_t *ptep,
\t\t\t     unsigned long pgsize,
\t\t\t     unsigned long ncontig)
{
\treturn 0;
}
int foo(int a, /* count */
\tint b)
{
\treturn a;
}
"""


class BridgeTest(unittest.TestCase):
    def test_long_header_and_comments(self):
        self.assertEqual([h for _, _, h in function_spans(LONG) if h], ["get_clear_contig", "foo"])
        # the fixed four-line window of earlier rounds drops the long header
        self.assertEqual([h for _, _, h in function_spans(LONG, window=4) if h], ["foo"])

    def test_spans_and_identifiers(self):
        spans = function_spans(SRC)
        self.assertEqual(enclosing(spans, 3), "helper")
        self.assertEqual(enclosing(spans, 9), "consumer")
        self.assertIsNone(enclosing(spans, 5))
        self.assertEqual(identifiers("\treturn a + nr_cpu_ids; // CONFIG_X"), ["nr_cpu_ids"])

    def test_queries_and_prompt_are_value_blind(self):
        cands = [{"provider": {"file": "a.c", "line": 3}, "consumer": {"file": "a.c", "line": 10},
                  "requirement": "consumer needs nr_cpu_ids set", "conditions": "when CONFIG_SMP=y"}]
        br = build_queries(cands, {"a.c": SRC})
        names = {q["name"] for q in br[0]["queries"]}
        self.assertIn("provider_may_ref_nr_cpu_ids", names)
        self.assertIn("consumer_may_ref_use_value", names)
        self.assertIn("config_smp", names)
        prompt = formalization_prompt(cands, br, {0: {"config_smp": "bool"}})
        self.assertIn('"type": "unavailable"', prompt)
        self.assertNotIn('"value"', prompt)

    def test_evaluation_respects_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "e.json").write_text("{}\n", encoding="utf-8")
            docs = {"evidence": document(root / "e.json", root, "r")}
            formal = parse_formalizations('{"formalizations":[{"candidate":0,"expressible":true,"config_symbols":["config_smp"],'
                                          '"scope":{"symbol":"config_smp"},"relation":{"symbol":"provider_may_ref_nr_cpu_ids"}}]}')[0]
            facts = {"config_smp": True, "provider_may_ref_nr_cpu_ids": False}
            kw = dict(context="c", revision="r", basis="compiled_object", documents=docs)
            self.assertEqual(evaluate_candidate(formal, facts, reviewed=False, **kw)["relation_at_observation"], "insufficient")
            self.assertEqual(evaluate_candidate(formal, facts, reviewed=True, **kw)["relation_at_observation"], "violated")
            self.assertEqual(evaluate_candidate(formal, {"config_smp": True}, reviewed=True, **kw)["status"], "facts_unavailable")
            bad = dict(formal, relation={"op": "plus", "args": []})
            self.assertEqual(evaluate_candidate(bad, facts, reviewed=True, **kw)["status"], "invalid_formalization")
            self.assertEqual(evaluate_candidate({"expressible": False, "reason": "x"}, facts, reviewed=True, **kw)["status"], "not_expressible")

    def test_top_level_functions_for_callers(self):
        tops = _top_level_functions(SRC.replace("\t", " ") + "struct s { int a; };\nint arr[] = { 1, 2 };\n")
        self.assertEqual(sorted(tops), ["consumer", "helper"])
        self.assertIn("helper(2)", tops["consumer"])


if __name__ == "__main__":
    unittest.main()
