import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
from unittest import TestCase

from linux_bug_analyze.models import CommitInfo
from linux_bug_analyze.screening import ScreenRunner, StopRun, parse_screen


def response(relevance="unrelated", quote="fix dma", usage=30, ids=None):
    return NS(choices=[NS(finish_reason="stop", message=NS(content=json.dumps({
        "relevance": relevance, "reason": "reason", "evidence_ids": ids if ids is not None else [2 if quote == 'fix dma' else 999999],
        "vertical": "absent", "horizontal": "absent", "exclusion_basis": "ordinary_bug",
        "needs_review": relevance != "unrelated"})))], usage=NS(total_tokens=usage, prompt_tokens=20, completion_tokens=10))


def saved_response(quote):
    return json.dumps(dict(relevance='unrelated', reason='reason', evidence=[quote], needs_review=False))


class ScreeningTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.commit = CommitInfo("abcd", "abcd", "fix dma", "a", "d", "body", ("a.c",), "diff")
        self.calls = []

    def runner(self, outcomes, **kwargs):
        it = iter(outcomes)
        def create(**request):
            self.calls.append(request)
            value = next(it)
            if isinstance(value, Exception):
                raise value
            return value
        return ScreenRunner(NS(chat=NS(completions=NS(create=create))), self.path,
            model="deepseek-v4-flash", max_requests=kwargs.pop("max_requests", 5),
            token_budget=kwargs.pop("token_budget", 100000), sleep=lambda _: None, **kwargs)

    def test_budget_blocks_before_call(self):
        runner = self.runner([], token_budget=1)
        with self.assertRaises(StopRun):
            runner.screen(self.commit, "")
        self.assertEqual(self.calls, [])

    def test_retry_counts_and_usage_includes_invalid_response(self):
        runner = self.runner([response(quote="invented"), response()])
        runner.screen(self.commit, "")
        self.assertEqual(runner.requests, 2)
        self.assertEqual(runner.reported_tokens, 60)
        self.assertEqual(runner.charged_tokens, 60)

    def test_request_limit_applies_to_retry(self):
        runner = self.runner([response(quote="invented")], max_requests=1)
        with self.assertRaises(StopRun):
            runner.screen(self.commit, "")
        self.assertEqual(len(self.calls), 1)

    def test_unknown_usage_retains_reservation(self):
        runner = self.runner([response(usage=None)])
        runner.screen(self.commit, "")
        self.assertGreater(runner.charged_tokens, runner.max_tokens)

    def test_fatal_error_does_not_retry(self):
        error = RuntimeError("secret must not be written")
        error.status_code = 402
        runner = self.runner([error])
        with self.assertRaises(StopRun):
            runner.screen(self.commit, "")
        self.assertEqual(len(self.calls), 1)
        self.assertNotIn("secret", (self.path / "usage.json").read_text())

    def test_cache_uses_context_fingerprint(self):
        runner = self.runner([response(), response()])
        runner.screen(self.commit, "a")
        runner.screen(self.commit, "a")
        self.assertEqual(len(self.calls), 1)
        runner.screen(self.commit, "b")
        self.assertEqual(len(self.calls), 2)

    def test_truncated_negative_requires_review(self):
        from dataclasses import replace
        runner = self.runner([response()])
        result = runner.screen(replace(self.commit, diff_truncated=True), "")
        self.assertEqual(result["relevance"], "uncertain")
        self.assertTrue(result["needs_review"])

    def test_guarded_result_preserves_model_audit_and_resumes_without_call(self):
        value = response()
        data = json.loads(value.choices[0].message.content)
        data['vertical'] = 'unknown'
        value.choices[0].message.content = json.dumps(data)
        runner = self.runner([value])
        decision = runner.screen(self.commit, '')
        self.assertEqual(decision['relevance'], 'uncertain')
        saved = json.loads((self.path/'results/abcd.json').read_text())
        self.assertEqual(saved['model_decision']['relevance'], 'unrelated')
        self.assertIn('boundary_not_ruled_out', saved['guard_flags'])
        self.assertEqual(runner.screen(self.commit, ''), decision)
        self.assertEqual(len(self.calls), 1)

    def test_invalid_evidence_rejected(self):
        with self.assertRaises(ValueError):
            parse_screen(saved_response("made up"), "fix dma")

    def test_original_quotes_and_newlines_can_be_cited(self):
        from dataclasses import replace
        quote = 'if ("value") {\n\treturn 0;'
        runner = self.runner([response(ids=[9, 10])])
        result = runner.screen(replace(self.commit, diff=quote), "")
        self.assertEqual(result["evidence"], quote.splitlines())
        self.assertEqual(len(self.calls), 1)

    def test_line_wrapped_quote_is_accepted_but_paraphrase_is_not(self):
        parse_screen(saved_response("fix dma"), "fix\n    dma")
        with self.assertRaises(ValueError):
            parse_screen(saved_response("only fix dma"), "fix dma")
