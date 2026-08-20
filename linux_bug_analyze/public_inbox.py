"""读取 public-inbox v2 本地 Git epoch 中的原始邮件。"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path


EPOCH_RE = re.compile(r"^(\d+)\.git$")


class PublicInboxError(RuntimeError):
    """public-inbox 镜像布局或 Git 数据不可读。"""


@dataclass(frozen=True, slots=True)
class InboxMessage:
    epoch: int
    storage_commit: str
    raw_message: bytes


def _is_bare_git_repository(path: Path) -> bool:
    return (path / "HEAD").is_file() and (path / "objects").is_dir()


def discover_epoch_repositories(inbox_dir: Path) -> list[tuple[int, Path]]:
    """接受 inbox 根目录、git 目录或单个 ``N.git`` epoch。"""

    root = inbox_dir.expanduser().resolve()
    if not root.is_dir():
        raise PublicInboxError(f"public-inbox 路径不存在：{root}")

    direct_match = EPOCH_RE.fullmatch(root.name)
    if direct_match and _is_bare_git_repository(root):
        return [(int(direct_match.group(1)), root)]

    search_root = root / "git" if (root / "git").is_dir() else root
    epochs: list[tuple[int, Path]] = []
    for candidate in search_root.iterdir():
        match = EPOCH_RE.fullmatch(candidate.name)
        if match and candidate.is_dir() and _is_bare_git_repository(candidate):
            epochs.append((int(match.group(1)), candidate.resolve()))
    if not epochs:
        raise PublicInboxError(
            f"未在 {root} 找到 public-inbox v2 epoch（预期 git/0.git 等目录）。"
        )
    return sorted(epochs, key=lambda item: item[0])


def _run_git(git_dir: Path, args: Sequence[str]) -> str:
    try:
        process = subprocess.run(
            ["git", f"--git-dir={git_dir}", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
    except FileNotFoundError as exc:
        raise PublicInboxError("未找到 git 可执行程序。") from exc
    except (OSError, subprocess.CalledProcessError) as exc:
        stderr = getattr(exc, "stderr", "") or ""
        raise PublicInboxError(
            f"无法读取 public-inbox epoch {git_dir}: {stderr.strip() or exc}"
        ) from exc
    return process.stdout


def _read_message_blobs(
    git_dir: Path,
    commits: Sequence[str],
) -> Iterator[tuple[str, bytes]]:
    """通过单个 cat-file 批处理进程读取每个 commit 的 ``m`` blob。"""

    try:
        process = subprocess.Popen(
            ["git", f"--git-dir={git_dir}", "cat-file", "--batch"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (FileNotFoundError, OSError) as exc:
        raise PublicInboxError(f"无法启动 git cat-file：{exc}") from exc
    assert process.stdin is not None
    assert process.stdout is not None
    assert process.stderr is not None

    try:
        for commit_hash in commits:
            process.stdin.write(f"{commit_hash}:m\n".encode("ascii"))
            process.stdin.flush()
            header = process.stdout.readline()
            if not header:
                detail = process.stderr.read().decode("utf-8", errors="replace").strip()
                raise PublicInboxError(f"git cat-file 提前退出：{detail or '无错误信息'}")
            if header.rstrip().endswith(b" missing"):
                continue
            parts = header.rstrip(b"\n").split()
            if len(parts) != 3 or parts[1] != b"blob":
                raise PublicInboxError(
                    f"无法解析 git cat-file 响应：{header.decode(errors='replace').strip()}"
                )
            try:
                size = int(parts[2])
            except ValueError as exc:
                raise PublicInboxError("git cat-file 返回了无效 blob 大小。") from exc
            raw_message = process.stdout.read(size)
            separator = process.stdout.read(1)
            if len(raw_message) != size or separator != b"\n":
                raise PublicInboxError("git cat-file 返回了不完整的邮件 blob。")
            yield commit_hash, raw_message
    finally:
        try:
            process.stdin.close()
        except OSError:
            pass
        if process.poll() is None:
            process.terminate()
        process.wait()
        process.stdout.close()
        process.stderr.close()


def iter_inbox_messages(inbox_dir: Path) -> Iterator[InboxMessage]:
    """按 epoch 和 epoch 内 Git 历史顺序读取有效 ``m`` 邮件。"""

    for epoch, git_dir in discover_epoch_repositories(inbox_dir):
        commits = tuple(
            line.strip()
            for line in _run_git(git_dir, ["rev-list", "--reverse", "--all"]).splitlines()
            if line.strip()
        )
        for storage_commit, raw_message in _read_message_blobs(git_dir, commits):
            yield InboxMessage(epoch, storage_commit, raw_message)
