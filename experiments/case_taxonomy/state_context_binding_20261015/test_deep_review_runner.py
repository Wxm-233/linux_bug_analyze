"""Offline lifecycle/accounting boundaries; no credential file or API is touched."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import deep_review_runner as runner


def prepared():
    return {"packet": {"source": "frozen source only"}, "prompts": {stage: "Prompt " + stage for stage in runner.STAGES}}


def ledger(entries=None):
    return {"entries": [] if entries is None else entries, "stop_reason": None}


def finished(stage, path, text):
    path.write_text(text, encoding="utf-8")
    return {"stage": stage, "status": "finished", "outcome": "complete_final_markdown", "charged_tokens": 100,
            "final_markdown": {"path": path.name, "sha256": runner.digest(path.read_bytes())}}


def response(finish="stop", content="# Final\nEvidence and limitations", model="AWS-Claude-Sonnet-5"):
    return {"model": model, "choices": [{"finish_reason": finish,
            "message": {"content": content, "reasoning_content": "NOT_A_FINAL_OUTPUT"}}]}


class ReviewRunnerTests(unittest.TestCase):
    def test_five_prior_ledgers_charge_and_unknown_reservation(self):
        prior = runner.prior_accounting()
        self.assertEqual(prior["charged_tokens"], 133703)
        self.assertEqual(prior["unknown_usage_reserved_tokens"], 28202)
        self.assertEqual(len(prior["ledgers"]), 5)
        self.assertEqual(prior["charged_tokens"] + runner.NEW_BUDGET, 1000000)

    def test_unknown_usage_is_full_reservation(self):
        self.assertEqual(runner.charge_from_usage({"total_tokens": 123}, 1000), (True, 123))
        for usage in (None, {}, {"total_tokens": True}, {"total_tokens": -1}):
            self.assertEqual(runner.charge_from_usage(usage, 1000), (False, 1000))

    def test_markdown_not_json_graded(self):
        content, reason, complete = runner.final_output(response(), "AWS-Claude-Sonnet-5")
        self.assertTrue(complete)
        self.assertEqual(reason, "stop")
        self.assertTrue(content.startswith("# Final"))
        self.assertNotIn("NOT_A_FINAL_OUTPUT", content)

    def test_length_and_missing_content_not_success(self):
        for raw in (response(finish="length"), response(content=None), response(content="  "), response(model="other")):
            self.assertFalse(runner.final_output(raw, "AWS-Claude-Sonnet-5")[2])

    def test_analysis_has_packet_only(self):
        req, state = runner.next_request(prepared(), ledger())
        self.assertEqual(state, "ready")
        self.assertEqual(req["stage"], "analysis")
        body = json.loads(req["messages"][1]["content"])
        self.assertEqual(set(body), {"source_packet"})
        self.assertEqual(req["reserved_tokens"], req["message_bytes"] + 24576 + 8192 + 512)

    def test_critique_and_synthesis_use_only_preceding_final_text(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(runner, "HERE", Path(tmp)):
            analysis = finished("analysis", Path(tmp) / "a.md", "Analysis final")
            req, state = runner.next_request(prepared(), ledger([analysis]))
            body = json.loads(req["messages"][1]["content"])
            self.assertEqual(req["stage"], "critique")
            self.assertEqual(body["prior_final_outputs"], {"analysis": "Analysis final"})
            critique = finished("critique", Path(tmp) / "c.md", "Critique final")
            req, _ = runner.next_request(prepared(), ledger([analysis, critique]))
            body = json.loads(req["messages"][1]["content"])
            self.assertEqual(req["stage"], "synthesis")
            self.assertEqual(body["prior_final_outputs"], {"analysis": "Analysis final", "critique": "Critique final"})

    def test_started_or_incomplete_never_repeated(self):
        for entry, expected in (({"status": "started", "charged_tokens": 100}, "started_request_never_repeat"),
                                ({"status": "finished", "outcome": "incomplete_final", "charged_tokens": 100}, "incomplete_prior_final_no_automatic_retry")):
            req, state = runner.next_request(prepared(), ledger([entry]))
            self.assertIsNone(req)
            self.assertEqual(state, expected)

    def test_budget_and_explicit_stop_prevent_next_call(self):
        huge = prepared()
        huge["packet"] = "x" * runner.NEW_BUDGET
        self.assertEqual(runner.next_request(huge, ledger())[1], "budget_reservation_blocked")
        stopped = ledger()
        stopped["stop_reason"] = "manual_review"
        self.assertEqual(runner.next_request(prepared(), stopped)[1], "stopped:manual_review")

    def test_frozen_ledger_input_changes_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(runner, "LEDGER", Path(tmp) / "ledger.json"):
            config = {"fingerprint": "a", "bindings": {"files": {"prompt": "sha"}}}
            initial = runner.load_ledger(config)
            runner.atomic_json(runner.LEDGER, initial)
            self.assertEqual(runner.load_ledger(config)["entries"], [])
            with self.assertRaises(ValueError):
                runner.load_ledger({"fingerprint": "b", "bindings": config["bindings"]})

    def test_artifact_exact_key_redaction(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(runner, "HERE", Path(tmp)):
            path = Path(tmp) / "example.md"
            item = runner.artifact(path, "Message DEMO_SECRET", "DEMO_SECRET", markdown=True)
            self.assertEqual(path.read_text(encoding="utf-8"), "Message [REDACTED]")
            self.assertEqual(item["sha256"], runner.digest(path.read_bytes()))


if __name__ == "__main__":
    unittest.main()
