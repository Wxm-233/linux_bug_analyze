"""Git 仓库访问与提交信息提取。"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Sequence

from .models import CommitInfo


HASH_PATTERN = re.compile(r"^[0-9a-fA-F]{4,64}$")


class GitRepositoryError(RuntimeError):
    """Git 命令无法完成请求。"""


def read_hashes(path: Path) -> list[str]:
    """读取、校验并按首次出现顺序去重 commit hash。"""

    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise GitRepositoryError(f"无法读取 hash 文件 {path}: {exc}") from exc

    hashes: list[str] = []
    seen: set[str] = set()
    for line_number, raw_line in enumerate(lines, start=1):
        value = raw_line.strip()
        if not value or value.startswith("#"):
            continue
        if not HASH_PATTERN.fullmatch(value):
            raise GitRepositoryError(
                f"{path} 第 {line_number} 行不是合法的十六进制 commit hash: {value!r}"
            )
        normalized = value.lower()
        if normalized not in seen:
            hashes.append(value)
            seen.add(normalized)
    if not hashes:
        raise GitRepositoryError(f"hash 文件为空：{path}")
    return hashes


def truncate_diff(diff: str, max_chars: int) -> tuple[str, bool]:
    """在明确标注的情况下保留 diff 首尾；0 表示不截断。"""

    if max_chars == 0 or len(diff) <= max_chars:
        return diff, False
    marker = (
        f"\n\n... [diff 已截断：原始 {len(diff)} 字符；"
        "保留开头与结尾，可用 --max-diff-chars 0 禁用截断] ...\n\n"
    )
    if max_chars <= len(marker):
        return marker[:max_chars], True
    available = max(0, max_chars - len(marker))
    head_size = available * 2 // 3
    tail_size = available - head_size
    tail = diff[-tail_size:] if tail_size else ""
    return diff[:head_size] + marker + tail, True


class GitRepository:
    """只负责从本地 Git 仓库读取提交事实。"""

    def __init__(self, path: Path):
        self.path = path.resolve()

    def _run(self, args: Sequence[str]) -> str:
        try:
            proc = subprocess.run(
                ["git", *args],
                cwd=self.path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=True,
            )
        except FileNotFoundError as exc:
            raise GitRepositoryError("未找到 git 可执行程序。") from exc
        except (OSError, subprocess.CalledProcessError) as exc:
            stderr = getattr(exc, "stderr", "") or ""
            detail = stderr.strip() or str(exc)
            raise GitRepositoryError(f"git {' '.join(args)} 执行失败：{detail}") from exc
        return proc.stdout

    def validate(self) -> None:
        if not self.path.is_dir():
            raise GitRepositoryError(f"Linux 源码目录不存在：{self.path}")
        if self._run(["rev-parse", "--is-inside-work-tree"]).strip() != "true":
            raise GitRepositoryError(f"不是 Git 工作树：{self.path}")

    def resolve_hash(self, commit_hash: str) -> str:
        if not HASH_PATTERN.fullmatch(commit_hash):
            raise GitRepositoryError(f"不是合法的十六进制 commit hash：{commit_hash!r}")
        return self._run(
            ["rev-parse", "--verify", f"{commit_hash}^{{commit}}"]
        ).strip()

    def get_commit(
        self,
        requested_hash: str,
        max_diff_chars: int,
        *,
        include_diff: bool = True,
    ) -> CommitInfo:
        canonical_hash = self.resolve_hash(requested_hash)
        metadata = self._run(
            [
                "show",
                "-s",
                "--date=short",
                "--format=%H%x00%an%x00%ad%x00%B",
                canonical_hash,
            ]
        )
        parts = metadata.split("\x00", 3)
        if len(parts) != 4:
            raise GitRepositoryError(f"无法解析提交元数据：{requested_hash}")
        full_message = parts[3].strip()
        message_lines = full_message.splitlines()
        subject = message_lines[0].strip() if message_lines else ""
        body = "\n".join(message_lines[1:]).strip()

        files_raw = self._run(
            ["show", "--name-only", "--format=", "--no-ext-diff", canonical_hash]
        )
        files = tuple(line.strip() for line in files_raw.splitlines() if line.strip())
        full_diff = ""
        if include_diff:
            full_diff = self._run(
                [
                    "show",
                    "--format=",
                    "--find-renames",
                    "--find-copies",
                    "--unified=3",
                    "--no-ext-diff",
                    canonical_hash,
                ]
            ).strip()
        diff, truncated = truncate_diff(full_diff, max_diff_chars)
        return CommitInfo(
            requested_hash=requested_hash,
            hash=parts[0].strip(),
            author=parts[1].strip(),
            date=parts[2].strip(),
            subject=subject,
            body=body,
            files=files,
            diff=diff,
            diff_truncated=truncated,
            original_diff_chars=len(full_diff),
        )
