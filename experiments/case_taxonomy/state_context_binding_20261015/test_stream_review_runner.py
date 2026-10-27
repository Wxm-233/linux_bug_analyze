"""Offline streaming/recovery boundaries. No actual credential/API is accessed."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import stream_review_runner as runner

MODEL = "AWS-Claude-Sonnet-5"


def chunk(content=None, finish=None, usage=None, model=MODEL, choices=None):
    return {"model": model, "choices": [{"index": 0, "delta": {"content": content,
            "reasoning_content": "OPAQUE_NOT_FINAL"}, "finish_reason": finish}] if choices is None else choices,
            "usage": usage}


def collect(items):
    state, saved = runner.StreamState(MODEL), []
    runner.consume_stream(items, state, saved.append)
    return state, saved


class StreamTests(unittest.TestCase):
    def test_six_frozen_ledgers_and_budget(self):
        prior = runner.prior_accounting()
        self.assertEqual(len(prior["ledgers"]), 6)
        self.assertEqual(prior["charged_tokens"], 203967)
        self.assertEqual(prior["unknown_usage_reserved_tokens"], 98466)
        self.assertEqual(prior["charged_tokens"] - prior["unknown_usage_reserved_tokens"], 105501)
        self.assertEqual(prior["charged_tokens"] + runner.NEW_BUDGET, 1000000)

    def test_content_combination_and_tail_usage(self):
        state, saved = collect([chunk("# Final\n"), chunk("Content"), chunk(finish="stop"),
                               chunk(choices=[], usage={"total_tokens": 123})])
        result = state.summary()
        self.assertTrue(result["complete_final_markdown"])
        self.assertEqual(result["assembled_final_content"], "# Final\nContent")
        self.assertEqual(runner.charge_from_usage(result["tail_usage"], 70000), (True, 123))
        self.assertEqual(len(saved), 4)
        self.assertNotIn("OPAQUE_NOT_FINAL", result["assembled_final_content"])

    def test_missing_or_nonfinal_usage_retains_reservation(self):
        for items in ([chunk("Final"), chunk(finish="stop")],
                      [chunk(choices=[], usage={"total_tokens": 123}), chunk("Final", finish="stop")]):
            state, _ = collect(items)
            self.assertEqual(runner.charge_from_usage(state.summary()["tail_usage"], 70000), (False, 70000))

    def test_length_is_incomplete(self):
        state, _ = collect([chunk("Partial", finish="length"), chunk(choices=[], usage={"total_tokens": 5})])
        self.assertFalse(state.summary()["complete_final_markdown"])
        self.assertEqual(state.summary()["assembled_final_content"], "Partial")

    def test_model_mismatch_multi_choice_or_content_after_finish(self):
        cases = [[chunk("Wrong", finish="stop", model="other")],
                 [chunk(choices=[{"index": 0}, {"index": 1}])],
                 [chunk("A", finish="stop"), chunk("B")]]
        for items in cases:
            state, _ = collect(items + [chunk(choices=[], usage={"total_tokens": 10})])
            self.assertFalse(state.summary()["complete_final_markdown"])
            self.assertTrue(state.summary()["protocol_errors"])

    def test_network_failure_retains_full_charge_and_partial_markdown(self):
        state = runner.StreamState(MODEL)
        def failing():
            yield chunk("Partial final text")
            raise RuntimeError("simulated network interruption")
        saved = []
        with self.assertRaises(RuntimeError):
            runner.consume_stream(failing(), state, saved.append)
        with tempfile.TemporaryDirectory() as tmp, patch.object(runner, "HERE", Path(tmp)):
            chunks_path = Path(tmp) / "chunks.jsonl"
            chunks_path.write_text("".join(json.dumps(raw) + "\n" for raw in saved), encoding="utf-8")
            entry = {"stage": "analysis", "status": "started", "reserved_tokens": 70000,
                     "charged_tokens": 10, "usage_known": True, "usage": {"total_tokens": 10}}
            result = runner.preserve_failed_stream(entry, state, chunks_path, "")
            self.assertFalse(result["complete_final_markdown"])
            self.assertEqual(entry["charged_tokens"], 70000)
            self.assertFalse(entry["usage_known"])
            final = runner.local(entry["final_markdown"]["path"])
            self.assertTrue(final.name.endswith(".incomplete.md"))
            self.assertEqual(final.read_text(encoding="utf-8"), "Partial final text")

    def test_started_request_never_automatically_repeated(self):
        ledger = {"stop_reason": None, "entries": [{"status": "started", "charged_tokens": 70000}]}
        request, status = runner.next_request({}, ledger)
        self.assertIsNone(request)
        self.assertEqual(status, "started_request_never_repeat")

    def test_stage_inputs_use_only_prior_final(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(runner, "HERE", Path(tmp)):
            file = Path(tmp) / "analysis.md"
            file.write_text("Analysis final", encoding="utf-8")
            prepared = {"packet": {"source": "known case"}, "prompts": {stage: stage for stage in runner.STAGES}}
            ledger = {"stop_reason": None, "entries": [{"stage": "analysis", "status": "finished",
                "outcome": "complete_final_markdown", "charged_tokens": 100,
                "final_markdown": {"path": file.name}}]}
            req, _ = runner.next_request(prepared, ledger)
            self.assertEqual(req["stage"], "critique")
            body = json.loads(req["messages"][1]["content"])
            self.assertEqual(body["prior_final_outputs"], {"analysis": "Analysis final"})


if __name__ == "__main__":
    unittest.main()
