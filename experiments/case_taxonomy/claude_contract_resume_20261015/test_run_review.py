"""Offline transport/accounting tests. No credentials or actual HTTP clients."""
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE = Path(__file__).with_name("run_review.py")
spec = importlib.util.spec_from_file_location("contract_resume_runner", MODULE)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


def final_response(content="A useful final", finish="stop", model=r.MODEL, usage=None):
    return {"model": model, "choices": [{"index": 0, "message": {"content": content}, "finish_reason": finish}],
            "usage": usage or {"prompt_tokens": 8, "completion_tokens": 2, "total_tokens": 10}}


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.here = Path(self.tmp.name)
        self.patch = patch.multiple(r, HERE=self.here, LEDGER=self.here / "ledger.json")
        self.patch.start()
        self.addCleanup(self.patch.stop)
        (self.here / "prompt.txt").write_text("研究", encoding="utf-8")
        (self.here / "material.txt").write_text("source", encoding="utf-8")
        self.prepared = {"key_path": self.here / "never-read-key", "plan": {"requests": [
            {"id": "diagnostic", "prompt_file": "prompt.txt", "material_file": "material.txt",
             "max_tokens": 100, "stream": False, "timeout_seconds": 30},
            {"id": "review", "prompt_file": "prompt.txt", "material_file": "material.txt",
             "max_tokens": 300, "stream": True, "timeout_seconds": 30,
             "depends_on_previous_final": ["diagnostic"]},
            {"id": "independent", "prompt_file": "prompt.txt", "material_file": "material.txt",
             "max_tokens": 100, "stream": False, "timeout_seconds": 30}]},
                         "fingerprint": "test", "bindings": {"test": True}}
        self.ledger = r.load_ledger(self.prepared)

    def test_precharge_is_utf8_bytes_plus_reserves(self):
        req, state = r.request_for(self.prepared, self.ledger, "diagnostic")
        self.assertEqual(state, "ready")
        self.assertEqual(req["message_bytes"], len("研究source".encode("utf-8")))
        self.assertEqual(req["reserved_tokens"], req["message_bytes"] + 100 + 8192 + 512)

    def test_known_usage_releases_reservation_and_inconsistent_usage_does_not(self):
        self.assertEqual(r.charge({"total_tokens": 10, "prompt_tokens": 8, "completion_tokens": 2}, 300), (True, 10))
        self.assertEqual(r.charge(None, 300), (False, 300))
        self.assertEqual(r.charge({"total_tokens": 1, "prompt_tokens": 8, "completion_tokens": 2}, 300), (False, 300))

    def test_budget_checked_before_request(self):
        self.ledger["entries"].append({"id": "other", "charged_tokens": r.NEW})
        req, state = r.request_for(self.prepared, self.ledger, "diagnostic")
        self.assertIsNone(req)
        self.assertEqual(state, "budget_reservation_blocked")

    def test_started_id_not_repeated_but_independent_diagnostic_allowed(self):
        self.ledger["entries"].append({"id": "diagnostic", "status": "started", "charged_tokens": 100})
        self.assertEqual(r.request_for(self.prepared, self.ledger, "diagnostic")[1], "already_started_never_repeat")
        self.assertEqual(r.request_for(self.prepared, self.ledger, "independent")[1], "ready")
        self.assertIn("dependency_has_no_complete_final", r.request_for(self.prepared, self.ledger, "review")[1])

    def test_dependency_requires_stop_same_model_nonempty_final(self):
        text = r.artifact("final/diagnostic.md", b"Final content")
        e = {"id": "diagnostic", "status": "finished", "outcome": "complete_final", "charged_tokens": 10,
             "response_model": r.MODEL, "finish_reason": "stop", "final_text": text}
        self.ledger["entries"].append(e)
        req, state = r.request_for(self.prepared, self.ledger, "review")
        self.assertEqual(state, "ready")
        self.assertIn("Final content", req["messages"][-1]["content"])
        e["response_model"] = "other"
        self.assertIn("dependency_has_no_complete_final", r.request_for(self.prepared, self.ledger, "review")[1])
        e["response_model"] = r.MODEL
        e["finish_reason"] = "length"
        self.assertIn("dependency_has_no_complete_final", r.request_for(self.prepared, self.ledger, "review")[1])

    def test_empty_length_wrong_model_and_valid_final_classified(self):
        self.assertEqual(r.outcome(r.select_json(final_response()), 200), "complete_final")
        self.assertEqual(r.outcome(r.select_json(final_response("  ")), 200), "incomplete_empty_final")
        self.assertEqual(r.outcome(r.select_json(final_response(finish="length")), 200), "incomplete_finish_reason")
        self.assertEqual(r.outcome(r.select_json(final_response(model="other")), 200), "incomplete_model_mismatch")
        self.assertEqual(r.outcome(r.select_json(final_response()), 504), "http_error")

    def test_sse_tail_usage_and_content_only(self):
        rows = [
            {"model": r.MODEL, "choices": [{"index": 0, "delta": {"reasoning_content": "not final"}}]},
            {"model": r.MODEL, "choices": [{"index": 0, "delta": {"content": "Answer "}}]},
            {"model": r.MODEL, "choices": [{"index": 0, "delta": {"content": "here"}, "finish_reason": "stop"}]},
            {"model": r.MODEL, "choices": [], "usage": {"total_tokens": 23}}]
        raw = ("\n\n".join("data: " + json.dumps(x) for x in rows) + "\n\ndata: [DONE]\n\n").encode()
        selected = r.select_sse(raw)
        self.assertEqual(selected["content"], "Answer here")
        self.assertEqual(selected["usage"]["total_tokens"], 23)
        self.assertEqual(r.outcome(selected, 200), "complete_final")
        self.assertNotIn("not final", json.dumps(selected))
        self.assertEqual(r.outcome(r.select_sse(raw.replace(b"data: [DONE]", b"")), 200), "incomplete_transport_or_choices")

    def test_durable_precharge_before_http_and_redacted_artifacts(self):
        request, _ = r.request_for(self.prepared, self.ledger, "diagnostic")
        test_key = "synthetic-credential-for-offline-test"
        case = self

        class Response:
            status_code = 200
            headers = {"content-type": "application/json", "set-cookie": "hidden", "x-echo": test_key}
            def __enter__(self):
                return self
            def __exit__(self, *unused):
                return False
            def iter_bytes(self):
                yield json.dumps(final_response("Answer " + test_key)).encode()

        class Client:
            def __init__(self, **kwargs):
                case.assertFalse(kwargs["follow_redirects"])
            def __enter__(self):
                return self
            def __exit__(self, *unused):
                return False
            def stream(self, *args, **kwargs):
                durable = json.loads(r.LEDGER.read_text())
                case.assertEqual(durable["entries"][0]["status"], "started")
                case.assertEqual(durable["entries"][0]["charged_tokens"], request["reserved_tokens"])
                case.assertEqual(kwargs["headers"]["Authorization"], "Bearer " + test_key)
                return Response()

        metadata = r.perform(self.prepared, self.ledger, request, Client, lambda p: test_key)
        self.assertEqual(metadata["outcome"], "complete_final")
        self.assertEqual(metadata["charged_tokens"], 10)
        self.assertNotIn(test_key, json.dumps(metadata))
        for path in self.here.rglob("*"):
            if path.is_file():
                self.assertNotIn(test_key.encode(), path.read_bytes())
        headers = json.loads((self.here / "responses/diagnostic.headers.json").read_text())
        self.assertNotIn("set-cookie", headers)
        self.assertEqual(r.load_ledger(self.prepared)["entries"][0]["status"], "finished")

    def test_stdlib_default_construction_and_http_error_body_without_network(self):
        class OfflineOpener:
            def open(self, request, timeout):
                self.request, self.timeout = request, timeout
                raise r.urllib.error.HTTPError(request.full_url, 503, "unavailable", {"content-type": "text/plain"},
                                               io.BytesIO(b"upstream temporarily unavailable"))
        opener = OfflineOpener()
        with patch.object(r.urllib.request, "build_opener", return_value=opener) as build:
            with r.StdlibClient(timeout=31, follow_redirects=False) as client:
                with client.stream("POST", "https://offline.invalid/chat/completions", json={"stream": False},
                                   headers={"Content-Type": "application/json"}) as response:
                    self.assertEqual(response.status_code, 503)
                    self.assertEqual(b"".join(response.iter_bytes()), b"upstream temporarily unavailable")
                    self.assertEqual(response.headers["content-type"], "text/plain")
            self.assertIsInstance(build.call_args.args[0], r.NoRedirect)
        self.assertEqual(opener.timeout, 31)

    def test_no_redirect_and_preflight_error_phase(self):
        self.assertIsNone(r.NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://other.invalid"))
        request, _ = r.request_for(self.prepared, self.ledger, "diagnostic")
        def missing_key(path):
            raise FileNotFoundError("Never print sensitive exception text")
        result = r.perform(self.prepared, self.ledger, request, key_loader=missing_key)
        self.assertEqual(result["phase"], "credential_read")
        self.assertEqual(result["error_type"], "FileNotFoundError")
        self.assertEqual(result["api_calls"], 0)
        self.assertFalse(r.LEDGER.exists())

    def test_interrupted_http_keeps_unknown_reserve_and_never_repeats(self):
        request, _ = r.request_for(self.prepared, self.ledger, "diagnostic")
        class BrokenClient:
            def __init__(self, **kwargs):
                raise TimeoutError("This text is not printed")
        result = r.perform(self.prepared, self.ledger, request, BrokenClient, lambda p: "test-key")
        self.assertEqual(result["charged_tokens"], request["reserved_tokens"])
        self.assertFalse(result["usage_known"])
        self.assertEqual(result["status"], "started")
        self.assertEqual(r.request_for(self.prepared, self.ledger, "diagnostic")[1], "already_started_never_repeat")

    def test_all_seven_prior_ledgers_and_unknown_carry(self):
        with patch.object(r, "HERE", MODULE.parent):
            prior = r.prior_accounting()
        self.assertEqual(len(prior["ledgers"]), 7)
        self.assertEqual(prior["charged_tokens"], 221927)
        self.assertEqual(prior["unknown_reserved_tokens"], 98466)
        self.assertEqual(prior["charged_tokens"] - prior["unknown_reserved_tokens"], 123461)

    def test_prior_hash_tampering_rejected(self):
        with patch.object(r, "PROJECT", self.here.parent), patch.object(r, "PRIOR", [("prompt.txt", 1, "0" * 64)]):
            with self.assertRaisesRegex(ValueError, "SHA changed"):
                r.prior_accounting()

    def test_ledger_artifact_tampering_rejected(self):
        a = r.artifact("requests/example.json", b"original")
        self.ledger["entries"].append({"id": "diagnostic", "status": "started", "usage": None,
                                      "usage_known": False, "reserved_tokens": 10, "charged_tokens": 10,
                                      "request": a})
        r.atomic(r.LEDGER, r.encoded(self.ledger))
        (self.here / a["path"]).write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "artifact changed"):
            r.load_ledger(self.prepared)


if __name__ == "__main__":
    unittest.main(verbosity=2)
