from types import SimpleNamespace
from unittest import TestCase

from linux_bug_analyze.llm import ChatAnalyzer, LLMError, is_retryable_error


VALID_OUTPUT = """<<<LBA_METADATA_V1>>>
{"schema_version":1,"relevance":"unrelated","categories":[],"confidence":"high"}
<<<LBA_REPORT_V1>>>
## 提交概述
overview

## 判定理由
reason

## 语义卡片
card

## 证据审计
evidence"""


class _Completions:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.calls = 0

    def create(self, **_kwargs):
        self.calls += 1
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        content, finish_reason = (
            outcome if isinstance(outcome, tuple) else (outcome, "stop")
        )
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=content),
                    finish_reason=finish_reason,
                )
            ]
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
        client, completions = _client([error, VALID_OUTPUT])
        waits = []
        analyzer = ChatAnalyzer(client, "model", max_retries=1, sleep=waits.append)
        result = analyzer.analyze("prompt")
        self.assertEqual(result.classification.relevance, "unrelated")
        self.assertEqual(result.model, "model")
        self.assertEqual(completions.calls, 2)
        self.assertEqual(waits, [1])

    def test_permanent_error_becomes_domain_error(self) -> None:
        client, _ = _client([RuntimeError("bad request")])
        with self.assertRaises(LLMError):
            ChatAnalyzer(client, "model", max_retries=0).analyze("prompt")

    def test_retries_invalid_format_once(self) -> None:
        client, completions = _client(["plain markdown", VALID_OUTPUT])
        result = ChatAnalyzer(
            client,
            "model",
            max_retries=0,
            format_retries=1,
        ).analyze("prompt")
        self.assertEqual(result.classification.confidence, "high")
        self.assertEqual(completions.calls, 2)

    def test_reports_repeated_format_failure(self) -> None:
        client, _ = _client(["bad", "still bad"])
        with self.assertRaisesRegex(LLMError, "输出格式校验失败"):
            ChatAnalyzer(
                client,
                "model",
                max_retries=0,
                format_retries=1,
            ).analyze("prompt")

    def test_retries_truncated_response(self) -> None:
        client, completions = _client([("partial", "length"), VALID_OUTPUT])
        ChatAnalyzer(
            client,
            "model",
            max_retries=0,
            format_retries=1,
        ).analyze("prompt")
        self.assertEqual(completions.calls, 2)
