import tempfile
import unittest
from pathlib import Path

from linux_bug_analyze.contract_envelope import build_envelope, document, symbol_type, symbols_used, whole
from linux_bug_analyze.contract_protocol import CLAIM_ROLES
from linux_bug_analyze.contract_protocol_v2 import evaluate_contract


def sym(n): return {"symbol": n}
def lit(v): return {"literal": v}
def op(name, *args): return {"op": name, "args": list(args)}


class V2Test(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "e.json").write_text("{}\n", encoding="utf-8")
        self.root = root

    def tearDown(self):
        self.tmp.cleanup()

    def run_case(self, relation, values, config=("enabled",), scope=None, qualification=None, basis="archived_runtime",
                 schema="architecture_contract_v2", mutate=None, types=None):
        scope = scope or sym("enabled")
        values = dict({"enabled": True}, **values)
        docs = {"e": document(self.root / "e.json", self.root, "r")}
        names = symbols_used(scope, relation, *([qualification] if qualification else []))
        symbols = {n: {"type": (types or {}).get(n) or symbol_type(values[n]), "role": "configuration" if n in config else "observation"} for n in sorted(names)}
        spec = {"schema": schema, "contract_id": "t", "revision": "r", "basis": basis, "context_id": "c", "object_id": "c.o",
                "sample_event": "c.s", "deadline_event": "c.d", "authority_kind": "consumer_inferred", "symbols": symbols,
                "scope": scope, "relation": relation, "documents": docs,
                "role_claims": {r: {"statement": "s", "references": whole(docs, "e")} for r in CLAIM_ROLES},
                "observation_claim": {"statement": "s", "references": whole(docs, "e")},
                "facts": {n: {"value": values[n], "statement": "s", "references": whole(docs, "e")} for n in symbols}}
        if qualification is not None:
            spec["observation_qualification"] = qualification
        item = build_envelope(spec)
        if mutate:
            mutate(item)
        return evaluate_contract(item["contract"], item["ledger"], item["record"])["relation_at_observation"]

    def test_arithmetic(self):
        rel = op("and", op("eq", op("floor_to", sym("x"), sym("g")), lit(64)), op("eq", op("ceil_to", sym("x"), sym("g")), lit(128)),
                 op("eq", op("min", sym("x"), lit(70)), sym("x")), op("eq", op("max", sym("x"), lit(1), lit(2)), sym("x")))
        self.assertEqual(self.run_case(rel, {"x": 65, "g": 64}), "satisfied")
        self.assertEqual(self.run_case(rel, {"x": 64, "g": 64}), "violated")
        self.assertEqual(self.run_case(op("eq", op("floor_to", sym("x"), sym("g")), lit(0)), {"x": 1, "g": 0}), "insufficient")
        self.assertEqual(self.run_case(op("eq", op("floor_to", sym("x"), sym("g")), lit(-64)), {"x": -1, "g": 64}), "satisfied")

    def test_event_operators(self):
        good = [["a", "o", 1], ["b", "o", 1], ["c", "o", 1], ["a", "o", 2], ["b", "o", 2]]
        ev = sym("ev")
        rel = op("and", op("ordered_within", ev, lit("a"), lit("b"), lit("c")), op("complete_within", ev, lit("c"), lit("a"), lit("b")),
                 op("exclusive_within", ev, lit("c"), lit("x")), op("at_most_once_within", ev, lit("a"), lit("b")),
                 op("generations_disjoint", ev), op("eq", op("count_kind", ev, lit("a"), lit("c")), lit(3)))
        self.assertEqual(self.run_case(rel, {"ev": good}), "satisfied")
        swapped = [good[1], good[0]] + good[2:]
        self.assertEqual(self.run_case(rel, {"ev": swapped}), "violated")
        overlap = good[:2] + [["a", "o", 2], ["c", "o", 1], ["b", "o", 2]]
        self.assertEqual(self.run_case(rel, {"ev": overlap}), "violated")
        incomplete = [["c", "o", 1]]
        self.assertEqual(self.run_case(op("complete_within", ev, lit("c"), lit("a")), {"ev": incomplete}), "violated")
        self.assertEqual(self.run_case(op("generations_disjoint", ev), {"ev": []}), "insufficient")  # [] alone types as int_set
        self.assertEqual(self.run_case(op("generations_disjoint", ev), {"ev": []}, types={"ev": "event_seq"}), "satisfied")

    def test_qualification_gives_insufficient_not_violated(self):
        q = op("eq", sym("anomalies"), lit(0))
        rel = op("eq", sym("bad"), lit(0))
        self.assertEqual(self.run_case(rel, {"bad": 1, "anomalies": 0}, qualification=q), "violated")
        self.assertEqual(self.run_case(rel, {"bad": 1, "anomalies": 2}, qualification=q), "insufficient")

        def unreviewed(item):
            item["ledger"]["claims"]["review.observation"]["qualification"] = lit(True)
        self.assertEqual(self.run_case(rel, {"bad": 0, "anomalies": 0}, qualification=q, mutate=unreviewed), "insufficient")

    def test_compiled_object_and_new_ops_are_v2_only(self):
        rel = op("eq", sym("v"), lit(1))
        self.assertEqual(self.run_case(rel, {"v": 1}, basis="compiled_object"), "satisfied")
        self.assertEqual(self.run_case(rel, {"v": 1}, basis="compiled_object", schema="architecture_contract_v1"), "insufficient")
        self.assertEqual(self.run_case(op("eq", op("min", sym("v"), lit(2)), lit(1)), {"v": 1}, schema="architecture_contract_v1"), "insufficient")

    def test_event_kinds_must_be_literals(self):
        rel = op("ordered_within", sym("ev"), sym("k"), lit("b"))
        self.assertEqual(self.run_case(rel, {"ev": [["a", "o", 1]], "k": "a"}), "insufficient")


if __name__ == "__main__":
    unittest.main()
