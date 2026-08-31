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
class AnalysisClassification:
    """模型给出的、可机器验证的研究分类。"""

    relevance: str
    categories: tuple[str, ...]
    confidence: str
    related_architectures: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ModelAnalysis:
    """已通过协议校验的模型输出。"""

    classification: AnalysisClassification
    markdown: str
    model: str = ""


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """一个提交的成功分析或可重试失败。"""

    requested_hash: str
    hash: str
    subject: str
    author: str
    date: str
    analysis: str = ""
    classification: AnalysisClassification | None = None
    model: str = ""
    error: str = ""

    @property
    def succeeded(self) -> bool:
        return not self.error

    @classmethod
    def success(cls, commit: CommitInfo, analysis: ModelAnalysis) -> "AnalysisResult":
        return cls(
            requested_hash=commit.requested_hash,
            hash=commit.hash,
            subject=commit.subject,
            author=commit.author,
            date=commit.date,
            analysis=analysis.markdown,
            classification=analysis.classification,
            model=analysis.model,
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
