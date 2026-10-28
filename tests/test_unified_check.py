import json
import tempfile
import unittest
from pathlib import Path

from linux_bug_analyze import unified_check as uc


def sym(n): return {"symbol": n}
def op(name, *args): return {"op": name, "args": list(args)}


class UnifiedCheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "policy.md").write_text("# policy\n", encoding="utf-8")
        (self.root / "rows.json").write_text(json.dumps({"diagnostics": [
            {"request": 2048, "effective": 2048, "disk_sector_size": 65536},
            {"request": 8192, "effective": 4096, "disk_sector_size": 65536}]}), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def case(self, **overrides):
        base = {"schema": "unified_case_v1", "case": "t", "revision": "r", "basis": "archived_runtime",
                "authority_kind": "consumer_inferred", "policy": "policy.md", "adapter": "btrfs_min",
                "config_symbols": ["request"],
                "inputs": [{"id": "a", "json": "rows.json", "select": ["diagnostics", 0]},
                           {"id": "b", "json": "rows.json", "select": ["diagnostics", 1]}],
                "relations": [{"name": "min", "scope": op("ge", sym("request"), {"literal": 0}),
                               "relation": op("eq", sym("effective"), op("min", sym("request"), sym("geometry")))}],
                "expected": {"a": {"min": "satisfied"}, "b": {"min": "violated"}}}
        base.update(overrides)
        return base

    def test_judged_and_expected(self):
        r = uc.run_case(self.case(), self.root / "out", self.root)
        self.assertEqual(r["expected_matched"], 2)
        self.assertEqual(r["decision_counts"], {"satisfied": 1, "violated": 1})
        evidence = json.loads((self.root / "out/evidence/t/a.json").read_text(encoding="utf-8"))
        self.assertEqual(evidence["adapter"], "btrfs_min")
        self.assertIn("source_sha256", evidence["provenance"])

    def test_unregistered_adapter_is_unsupported(self):
        r = uc.run_case(self.case(adapter="nope"), self.root / "out", self.root)
        self.assertEqual(r["status"], {"unsupported": 2})
        self.assertEqual(r["decision_counts"], {})

    def test_adapter_failure_and_missing_fact(self):
        bad = self.case(inputs=[{"id": "x", "json": "rows.json", "select": ["diagnostics", 5]}])
        self.assertEqual(uc.run_case(bad, self.root / "o1", self.root)["status"], {"adapter_failed": 1})
        rel = [{"name": "m", "scope": op("ge", sym("request"), {"literal": 0}), "relation": op("eq", sym("not_provided"), {"literal": 1})}]
        r = uc.run_case(self.case(relations=rel, expected=None), self.root / "o2", self.root)
        self.assertEqual(r["decision_counts"], {"insufficient": 2})

    def test_schema_required(self):
        with self.assertRaises(ValueError):
            uc.run_case(self.case(schema="other"), self.root / "o3", self.root)


if __name__ == "__main__":
    unittest.main()
