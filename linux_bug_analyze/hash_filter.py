"""基于 Git 提交事实筛选候选 commit hash。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from collections.abc import Iterable, Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Pattern

from .git_repository import GitRepository
from .models import CommitInfo


VALID_FIELDS = ("subject", "body", "files", "diff")


class HashFilterError(ValueError):
    """筛选规则无效。"""


@dataclass(frozen=True, slots=True)
class FilterRules:
    """已编译、可并发复用的筛选规则。"""

    include: tuple[Pattern[str], ...]
    exclude: tuple[Pattern[str], ...]
    fields: tuple[str, ...]
    match_all: bool


@dataclass(frozen=True, slots=True)
class PatternMatch:
    pattern: str
    fields: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {"pattern": self.pattern, "fields": list(self.fields)}


@dataclass(frozen=True, slots=True)
class FilterDecision:
    """单个提交的筛选决定及其审计信息。"""

    index: int
    requested_hash: str
    hash: str
    subject: str
    status: str
    reason: str
    include_matches: tuple[PatternMatch, ...] = ()
    exclude_matches: tuple[PatternMatch, ...] = ()
    diff_truncated: bool = False
    original_diff_chars: int = 0
    error: str = ""

    @property
    def selected(self) -> bool:
        return self.status == "selected"

    def to_dict(self) -> dict[str, object]:
        return {
            "input_index": self.index,
            "requested_hash": self.requested_hash,
            "hash": self.hash,
            "subject": self.subject,
            "status": self.status,
            "reason": self.reason,
            "include_matches": [match.to_dict() for match in self.include_matches],
            "exclude_matches": [match.to_dict() for match in self.exclude_matches],
            "diff_truncated": self.diff_truncated,
            "original_diff_chars": self.original_diff_chars,
            "error": self.error,
        }


def compile_rules(
    include: Iterable[str],
    exclude: Iterable[str],
    fields: Iterable[str],
    *,
    match: str = "any",
    case_sensitive: bool = False,
) -> FilterRules:
    """校验字段并编译正则表达式；普通关键词也可直接作为正则使用。"""

    selected_fields = tuple(dict.fromkeys(fields))
    invalid_fields = set(selected_fields) - set(VALID_FIELDS)
    if not selected_fields or invalid_fields:
        names = ", ".join(sorted(invalid_fields)) or "（空）"
        raise HashFilterError(f"无效筛选字段：{names}")
    if match not in {"any", "all"}:
        raise HashFilterError("match 必须是 any 或 all。")

    flags = 0 if case_sensitive else re.IGNORECASE

    def compile_many(patterns: Iterable[str], label: str) -> tuple[Pattern[str], ...]:
        compiled: list[Pattern[str]] = []
        for value in patterns:
            try:
                compiled.append(re.compile(value, flags))
            except re.error as exc:
                raise HashFilterError(f"{label} 正则无效 {value!r}: {exc}") from exc
        return tuple(compiled)

    return FilterRules(
        include=compile_many(include, "include"),
        exclude=compile_many(exclude, "exclude"),
        fields=selected_fields,
        match_all=match == "all",
    )


def _field_values(commit: CommitInfo, fields: tuple[str, ...]) -> dict[str, tuple[str, ...]]:
    values: dict[str, tuple[str, ...]] = {}
    if "subject" in fields:
        values["subject"] = (commit.subject,)
    if "body" in fields:
        values["body"] = (commit.body,)
    if "files" in fields:
        values["files"] = commit.files
    if "diff" in fields:
        values["diff"] = (commit.diff,)
    return values


def _matches(
    patterns: tuple[Pattern[str], ...],
    values: dict[str, tuple[str, ...]],
) -> tuple[PatternMatch, ...]:
    matches: list[PatternMatch] = []
    for pattern in patterns:
        matched_fields = tuple(
            field
            for field, field_values in values.items()
            if any(pattern.search(value) for value in field_values)
        )
        if matched_fields:
            matches.append(PatternMatch(pattern.pattern, matched_fields))
    return tuple(matches)


def evaluate_commit(index: int, commit: CommitInfo, rules: FilterRules) -> FilterDecision:
    """根据规则判断一个已经提取的提交。"""

    values = _field_values(commit, rules.fields)
    include_matches = _matches(rules.include, values)
    exclude_matches = _matches(rules.exclude, values)
    include_satisfied = not rules.include or (
        len(include_matches) == len(rules.include)
        if rules.match_all
        else bool(include_matches)
    )

    if exclude_matches:
        status = "excluded"
        reason = "命中 exclude 规则"
    elif include_satisfied:
        status = "selected"
        reason = "未配置 include，默认保留" if not rules.include else "命中 include 规则"
    else:
        status = "not_matched"
        reason = "未满足全部 include 规则" if rules.match_all else "未命中 include 规则"

    return FilterDecision(
        index=index,
        requested_hash=commit.requested_hash,
        hash=commit.hash,
        subject=commit.subject,
        status=status,
        reason=reason,
        include_matches=include_matches,
        exclude_matches=exclude_matches,
        diff_truncated=commit.diff_truncated,
        original_diff_chars=commit.original_diff_chars,
    )


def _filter_one(
    repository: GitRepository,
    index: int,
    commit_hash: str,
    rules: FilterRules,
    max_diff_chars: int,
) -> FilterDecision:
    try:
        commit = repository.get_commit(
            commit_hash,
            max_diff_chars,
            include_diff="diff" in rules.fields,
        )
        return evaluate_commit(index, commit, rules)
    except Exception as exc:
        return FilterDecision(
            index=index,
            requested_hash=commit_hash,
            hash=commit_hash,
            subject="",
            status="error",
            reason="无法读取或筛选提交",
            error=str(exc),
        )


def iter_filter_candidates(
    repository: GitRepository,
    hashes: Iterable[str],
    rules: FilterRules,
    *,
    workers: int,
    max_diff_chars: int,
) -> Iterator[FilterDecision]:
    """并发筛选，并按任务完成顺序返回决定。"""

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                _filter_one,
                repository,
                index,
                commit_hash,
                rules,
                max_diff_chars,
            )
            for index, commit_hash in enumerate(hashes)
        ]
        for future in as_completed(futures):
            yield future.result()
