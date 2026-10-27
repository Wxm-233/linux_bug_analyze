import json
import tempfile
import unittest
from pathlib import Path

from linux_bug_analyze.contract_envelope import (build_envelope, document, envelope_spec, symbol_type,
                                                 symbols_used, whole)
from linux_bug_analyze.contract_protocol import CLAIM_ROLES, evaluate_contract


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


class EnvelopeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "evidence.json").write_text('{"x": 1}\n', encoding="utf-8")
        (root / "policy.md").write_text("# policy\nline\n", encoding="utf-8")
        self.root = root
        self.docs = {"evidence": document(root / "evidence.json", root, "r1", source_revision="r1"),
                     "policy": document(root / "policy.md", root, "r1", source_revision="r1")}

    def tearDown(self):
        self.tmp.cleanup()

    def spec(self, observed):
        scope = {"symbol": "enabled"}
        relation = {"op": "eq", "args": [{"symbol": "missing"}, {"literal": []}]}
        values = {"enabled": True, "missing": observed}
        symbols = {n: {"type": symbol_type(values[n]), "role": "configuration" if n == "enabled" else "observation"}
                   for n in sorted(symbols_used(scope, relation))}
        roles = {r: {"statement": "reviewed " + r,
                     "references": whole(self.docs, "policy" if r in ("authority", "consumer_requirement") else "evidence")}
                 for r in CLAIM_ROLES}
        return {"contract_id": "t.c", "revision": "r1", "basis": "archived_runtime", "context_id": "ctx",
                "object_id": "ctx.obj", "sample_event": "ctx.sample", "deadline_event": "ctx.deadline",
                "authority_kind": "consumer_inferred", "symbols": symbols, "scope": scope, "relation": relation,
                "documents": self.docs, "role_claims": roles,
                "observation_claim": {"statement": "sample", "references": whole(self.docs, "evidence")},
                "facts": {n: {"value": values[n], "statement": "projected", "references": whole(self.docs, "evidence")}
                          for n in symbols}}

    def test_builder_output_is_judged_by_core(self):
        ok = build_envelope(self.spec([]))
        bad = build_envelope(self.spec([3]))
        self.assertEqual(evaluate_contract(ok["contract"], ok["ledger"], ok["record"])["relation_at_observation"], "satisfied")
        self.assertEqual(evaluate_contract(bad["contract"], bad["ledger"], bad["record"])["relation_at_observation"], "violated")

    def test_spec_roundtrip_is_exact(self):
        item = build_envelope(self.spec([3]))
        self.assertEqual(canonical(build_envelope(envelope_spec(item))), canonical(item))

    def test_unexpressible_structure_is_reported(self):
        item = build_envelope(self.spec([]))
        item["ledger"]["claims"]["review.object_binding"]["object_id"] = "other"
        rebuilt = build_envelope(envelope_spec(item))
        self.assertNotEqual(canonical(rebuilt), canonical(item))
        item = build_envelope(self.spec([]))
        item["contract"]["required_claims"]["interface"] = "odd"
        with self.assertRaises(ValueError):
            envelope_spec(item)

    def test_unknown_status_is_preserved(self):
        spec = self.spec([])
        spec["role_claims"]["provider_binding"]["status"] = "unknown"
        item = build_envelope(spec)
        self.assertEqual(item["ledger"]["claims"]["review.provider_binding"]["status"], "unknown")
        self.assertEqual(evaluate_contract(item["contract"], item["ledger"], item["record"])["relation_at_observation"], "insufficient")
        self.assertEqual(canonical(build_envelope(envelope_spec(item))), canonical(item))

    def test_builder_adds_no_approval(self):
        spec = self.spec([])
        spec["facts"]["missing"]["origin"] = "model_proposal"
        item = build_envelope(spec)
        self.assertEqual(evaluate_contract(item["contract"], item["ledger"], item["record"])["relation_at_observation"], "insufficient")


if __name__ == "__main__":
    unittest.main()
