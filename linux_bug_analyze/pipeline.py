"""并发提交分析流程。"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Protocol

from .evidence import EvidenceCollector
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
    evidence_collector: EvidenceCollector,
) -> AnalysisResult:
    canonical_hash = ""
    try:
        commit = repository.get_commit(requested_hash, max_diff_chars)
        canonical_hash = commit.hash
        evidence = evidence_collector.collect(commit)
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
    cve_inbox_dir: Path | None = None,
    mail_inbox_dirs: tuple[Path, ...] = (),
    include_fixes_commit: bool = True,
    max_evidence_chars_per_source: int = 12_000,
    max_evidence_chars: int = 36_000,
) -> Iterator[AnalysisResult]:
    """并发分析并按完成顺序产出结果；单条失败不会终止批次。"""

    hash_list = list(hashes)
    evidence_collector = EvidenceCollector(
        repository,
        evidence_dir=evidence_dir,
        cve_inbox_dir=cve_inbox_dir,
        mail_inbox_dirs=mail_inbox_dirs,
        include_fixes_commit=include_fixes_commit,
        max_chars_per_source=max_evidence_chars_per_source,
        max_total_chars=max_evidence_chars,
    )
    evidence_collector.prepare(hash_list)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                _analyze_one,
                repository,
                commit_hash,
                research_context,
                analyzer,
                max_diff_chars,
                evidence_collector,
            )
            for commit_hash in hash_list
        ]
        for future in as_completed(futures):
            yield future.result()
