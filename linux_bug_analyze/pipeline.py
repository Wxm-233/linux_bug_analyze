"""并发提交分析流程。"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Protocol

from .evidence import read_supplemental_evidence
from .git_repository import GitRepository
from .models import AnalysisResult, ModelAnalysis
from .prompting import build_prompt


class Analyzer(Protocol):
    def analyze(self, prompt: str) -> ModelAnalysis: ...


def _analyze_one(
    repository: GitRepository,
    requested_hash: str,
    research_context: str,
    analyzer: Analyzer,
    max_diff_chars: int,
    evidence_dir: Path | None,
) -> AnalysisResult:
    canonical_hash = ""
    try:
        commit = repository.get_commit(requested_hash, max_diff_chars)
        canonical_hash = commit.hash
        evidence = read_supplemental_evidence(evidence_dir, commit.hash)
        prompt = build_prompt(commit, research_context, evidence)
        return AnalysisResult.success(commit, analyzer.analyze(prompt))
    except Exception as exc:
        return AnalysisResult.failure(
            requested_hash,
            exc,
            canonical_hash=canonical_hash,
        )


def analyze_commits(
    repository: GitRepository,
    hashes: Iterable[str],
    research_context: str,
    analyzer: Analyzer,
    *,
    workers: int,
    max_diff_chars: int,
    evidence_dir: Path | None = None,
) -> Iterator[AnalysisResult]:
    """并发分析并按完成顺序产出结果；单条失败不会终止批次。"""

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                _analyze_one,
                repository,
                commit_hash,
                research_context,
                analyzer,
                max_diff_chars,
                evidence_dir,
            )
            for commit_hash in hashes
        ]
        for future in as_completed(futures):
            yield future.result()
