from unittest import TestCase

from linux_bug_analyze.hash_filter import HashFilterError, compile_rules, evaluate_commit
from linux_bug_analyze.models import CommitInfo


def _commit(*, subject="RISC-V fix", body="", files=("arch/riscv/mm.c",)):
    return CommitInfo(
        requested_hash="abcd",
        hash="a" * 40,
        subject=subject,
        author="author",
        date="date",
        body=body,
        files=files,
        diff="",
    )


class HashFilterTests(TestCase):
    def test_any_include_selects_and_records_matching_fields(self) -> None:
        rules = compile_rules(
            ["risc-?v", "powerpc"],
            [],
            ["subject", "files"],
        )
        decision = evaluate_commit(0, _commit(), rules)
        self.assertTrue(decision.selected)
        self.assertEqual(decision.include_matches[0].pattern, "risc-?v")
        self.assertEqual(decision.include_matches[0].fields, ("subject", "files"))

    def test_all_requires_every_include(self) -> None:
        rules = compile_rules(
            ["riscv", "powerpc"],
            [],
            ["subject", "files"],
            match="all",
        )
        self.assertEqual(evaluate_commit(0, _commit(), rules).status, "not_matched")

    def test_exclude_has_priority(self) -> None:
        rules = compile_rules(["riscv"], ["revert"], ["subject", "body"])
        decision = evaluate_commit(0, _commit(body="This reverts an old change"), rules)
        self.assertEqual(decision.status, "excluded")
        self.assertEqual(decision.exclude_matches[0].pattern, "revert")

    def test_no_include_keeps_non_excluded_commit(self) -> None:
        rules = compile_rules([], [], ["subject"])
        self.assertTrue(evaluate_commit(0, _commit(), rules).selected)

    def test_invalid_regex_is_rejected(self) -> None:
        with self.assertRaises(HashFilterError):
            compile_rules(["["], [], ["subject"])
