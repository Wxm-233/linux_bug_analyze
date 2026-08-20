from types import SimpleNamespace
from unittest import TestCase

from linux_bug_analyze.llm import ChatAnalyzer, LLMError, is_retryable_error


class _Completions:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.calls = 0

    def create(self, **_kwargs):
        self.calls += 1
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=outcome))]
        )


def _client(outcomes):
    completions = _Completions(outcomes)
    return SimpleNamespace(chat=SimpleNamespace(completions=completions)), completions


class ChatAnalyzerTests(TestCase):
    def test_all_server_errors_are_retryable(self) -> None:
        error = RuntimeError("server failure")
        error.status_code = 501
        self.assertTrue(is_retryable_error(error))

    def test_retries_temporary_error(self) -> None:
        error = RuntimeError("HTTP 503")
        client, completions = _client([error, "answer"])
        waits = []
        analyzer = ChatAnalyzer(client, "model", max_retries=1, sleep=waits.append)
        self.assertEqual(analyzer.analyze("prompt"), "answer")
        self.assertEqual(completions.calls, 2)
        self.assertEqual(waits, [1])

    def test_permanent_error_becomes_domain_error(self) -> None:
        client, _ = _client([RuntimeError("bad request")])
        with self.assertRaises(LLMError):
            ChatAnalyzer(client, "model", max_retries=0).analyze("prompt")
