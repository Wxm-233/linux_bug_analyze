"""分析流程使用的领域对象。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CommitInfo:
    """从 Git 仓库提取的单个提交信息。"""

    requested_hash: str
    hash: str
    subject: str
    author: str
    date: str
    body: str
    files: tuple[str, ...]
    diff: str
    diff_truncated: bool = False
    original_diff_chars: int = 0


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """一个提交的成功分析或可重试失败。"""

    requested_hash: str
    hash: str
    subject: str
    author: str
    date: str
    analysis: str = ""
    error: str = ""

    @property
    def succeeded(self) -> bool:
        return not self.error

    @classmethod
    def success(cls, commit: CommitInfo, analysis: str) -> "AnalysisResult":
        return cls(
            requested_hash=commit.requested_hash,
            hash=commit.hash,
            subject=commit.subject,
            author=commit.author,
            date=commit.date,
            analysis=analysis,
        )

    @classmethod
    def failure(
        cls,
        requested_hash: str,
        error: Exception | str,
        *,
        canonical_hash: str = "",
    ) -> "AnalysisResult":
        return cls(
            requested_hash=requested_hash,
            hash=canonical_hash or requested_hash,
            subject="（处理失败）",
            author="",
            date="",
            error=str(error),
        )
