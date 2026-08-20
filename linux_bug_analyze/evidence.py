"""读取人工收集的逐提交补充证据。"""

from __future__ import annotations

from pathlib import Path


def read_supplemental_evidence(evidence_dir: Path | None, commit_hash: str) -> str:
    """读取 ``<hash>.md`` 或 ``<hash>.txt``；未配置时返回空文本。"""

    if evidence_dir is None:
        return ""
    for suffix in (".md", ".txt"):
        candidate = evidence_dir / f"{commit_hash}{suffix}"
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    return ""
