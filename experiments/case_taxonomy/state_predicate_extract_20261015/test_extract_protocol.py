"""Protocol syntax boundaries only; accepted expressions are not semantic labels."""
import copy
import json
import unittest

import run_model_checks as runner


def docs():
    document = {"id": "SOURCE", "kind": "source", "path": "kernel/example.c",
                "start_line": 100, "end_line": 130,
                "text": "\n".join(f"{i}: source line {i}" for i in range(100, 131))}
    return {"SOURCE": {"document": document, "lines": runner.base.document_lines(document)}}


def ref():
    return {"document": "SOURCE", "start_line": 100, "end_line": 130}


def proposal(predicate=None):
    return {"scope": "local_candidate", "checks": [{
        "id": "generic", "title": "Generic structured condition", "providers": [], "configuration": [],
        "consumer": {"function": "consumer", "event": "first_read", "anchor": "read_value", "evidence": [ref()]},
        "predicate": predicate, "polarity": "must_hold", "authority_status": "insufficient",
        "basis": "Source-only candidate; syntax does not decide truth", "evidence": [ref()], "unknown": []}], "unknown": []}


def parse(value):
    return runner.parse_proposal(json.dumps(value), docs())


class ProtocolTests(unittest.TestCase):
    def test_accepts_varied_generic_predicates(self):
        symbol, literal = {"symbol": "unrelated_buffer_extent"}, {"literal": 10}
        expressions = [
            {"op": "nonempty", "args": [symbol]},
            {"op": "contains", "args": [{"symbol": "arbitrary_set"}, {"literal": "item"}]},
            {"op": "le", "args": [symbol, literal]},
            {"op": "precedes", "args": [{"symbol": "prepare_event"}, {"symbol": "use_event"}]},
            {"op": "and", "args": [{"literal": True}, {"op": "not", "args": [{"literal": False}]}]},
        ]
        for expression in expressions:
            with self.subTest(expression=expression):
                self.assertEqual(parse(proposal(expression))["checks"][0]["predicate"], expression)

    def test_null_predicate_and_zero_checks_valid(self):
        self.assertIsNone(parse(proposal())["checks"][0]["predicate"])
        self.assertEqual(parse({"scope": "insufficient", "checks": [], "unknown": []})["checks"], [])

    def test_contiguous_reference_longer_than_twenty_lines(self):
        result = parse(proposal())
        extracted = result["checks"][0]["program_extracted_evidence"][0]
        self.assertEqual(len(extracted["source_text"].splitlines()), 31)
        self.assertTrue(extracted["source_text"].startswith("100: source line 100"))

    def test_no_fence_duplicate_or_trailing_json_repair(self):
        for raw in ('```json\n{}\n```', '{"scope":"insufficient","scope":"local_candidate","checks":[],"unknown":[]}', '{} {}'):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    runner.parse_proposal(raw, docs())

    def test_invalid_ast_shape_operator_and_arity(self):
        cases = [{"op": "eval", "args": [{"literal": "code"}]}, {"op": "eq", "args": [{"literal": 1}]},
                 {"symbol": "a", "literal": 1}, {"symbol": ""}, {"op": "not", "args": [], "extra": True}]
        for expression in cases:
            with self.subTest(expression=expression):
                with self.assertRaises(ValueError):
                    parse(proposal(expression))

    def test_ast_depth_and_node_caps(self):
        deep = {"symbol": "value"}
        for _ in range(5):
            deep = {"op": "not", "args": [deep]}
        broad = {"op": "and", "args": [{"op": "and", "args": [
            {"op": "and", "args": [{"literal": True} for _ in range(4)]} for _ in range(4)]} for _ in range(4)]}
        for expression in (deep, broad):
            with self.assertRaises(ValueError):
                parse(proposal(expression))

    def test_nonfinite_and_invalid_literals(self):
        for literal in (float("nan"), float("inf"), None, [1], {"x": 1}, "x" * 101):
            with self.subTest(literal=repr(literal)):
                with self.assertRaises(ValueError):
                    parse(proposal({"literal": literal}))

    def test_bad_reference_document_range_and_bool(self):
        for field, value in (("document", "MISSING"), ("start_line", 99), ("end_line", 131), ("start_line", True)):
            with self.subTest(field=field, value=value):
                item = proposal()
                item["checks"][0]["evidence"][0][field] = value
                with self.assertRaises(ValueError):
                    parse(item)

    def test_counts_enums_and_lengths(self):
        for field, value in (("id", "x" * 33), ("polarity", "infer_it"), ("authority_status", "proved"),
                             ("providers", [{}, {}, {}]), ("configuration", [{}, {}, {}]),
                             ("unknown", ["a", "b", "c", "d"])):
            with self.subTest(field=field):
                item = proposal()
                item["checks"][0][field] = value
                with self.assertRaises(ValueError):
                    parse(item)
        item = proposal()
        item["checks"] *= 2
        with self.assertRaises(ValueError):
            parse(item)

    def test_provider_config_consumer_references(self):
        item = proposal()
        item["checks"][0]["providers"] = [{"architecture": "unseen_arch", "value": "source_value", "eligibility": "unknown", "evidence": [ref()]}]
        item["checks"][0]["configuration"] = [{"architecture": "unseen_arch", "requires": ["CONFIG_EXAMPLE=y"], "evidence": [ref()]}]
        accepted = parse(item)["checks"][0]
        self.assertEqual(accepted["providers"][0]["architecture"], "unseen_arch")
        for section in ("providers", "configuration"):
            changed = copy.deepcopy(item)
            changed["checks"][0][section][0]["evidence"] = []
            with self.assertRaises(ValueError):
                parse(changed)

    def test_carryover_frozen_accounting_and_budget(self):
        manifest = {"overall_budget_tokens": 1000000, "carryover": [
            {"ledger": path, "accounted_tokens": charge, "sha256": runner.base.digest((runner.HERE / path).read_bytes())}
            for path, charge, _ in runner.PRIOR]}
        result = runner.load_carryover(manifest, {"max_total_tokens": 889048})
        self.assertEqual(result["accounted_tokens"], 110952)
        with self.assertRaises(ValueError):
            runner.load_carryover(manifest, {"max_total_tokens": 889049})
        changed = copy.deepcopy(manifest)
        changed["carryover"][0]["sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            runner.load_carryover(changed, {"max_total_tokens": 889048})


if __name__ == "__main__":
    unittest.main()
