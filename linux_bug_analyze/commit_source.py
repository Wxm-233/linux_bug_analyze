"""直接从 Linux 主线 Git 历史流式读取候选提交。"""

from __future__ import annotations

import subprocess
from collections.abc import Iterator, Sequence
from pathlib import Path

from .models import CommitInfo


RECORD_SEPARATOR = "\x1e"
FIELD_SEPARATOR = "\x1f"
METADATA_END = "\x1d"


class CommitSourceError(RuntimeError):
    """Linux Git 历史无法读取或解析。"""


def _git_log_args(
    ref: str,
    *,
    since: str,
    until: str,
    no_merges: bool,
    reverse: bool,
    max_count: int,
) -> list[str]:
    pretty = "%x1e%H%x1f%an%x1f%aI%x1f%s%x1f%b%x1d"
    args = [
        "log",
        ref,
        f"--format={pretty}",
        "--name-only",
        "--no-renames",
    ]
    if since:
        args.append(f"--since={since}")
    if until:
        args.append(f"--until={until}")
    if no_merges:
        args.append("--no-merges")
    if reverse:
        args.append("--reverse")
    if max_count:
        args.append(f"--max-count={max_count}")
    return args


def _parse_record(record: str) -> CommitInfo | None:
    metadata, separator, file_text = record.partition(METADATA_END)
    if not separator:
        if not record.strip():
            return None
        raise CommitSourceError("git log 记录缺少元数据结束标记。")
    fields = metadata.lstrip("\r\n").split(FIELD_SEPARATOR, 4)
    if len(fields) != 5:
        raise CommitSourceError("git log 记录字段数量无效。")
    commit_hash, author, date, subject, body = fields
    files = tuple(
        line.strip()
        for line in file_text.replace("\r\n", "\n").splitlines()
        if line.strip()
    )
    return CommitInfo(
        requested_hash=commit_hash,
        hash=commit_hash,
        subject=subject.strip(),
        author=author.strip(),
        date=date.strip(),
        body=body.strip(),
        files=files,
        diff="",
    )


def iter_mainline_commits(
    linux_dir: Path,
    ref: str = "HEAD",
    *,
    since: str = "5 years ago",
    until: str = "",
    no_merges: bool = True,
    reverse: bool = True,
    max_count: int = 0,
) -> Iterator[CommitInfo]:
    """以常量级额外内存流式读取一个 ref 可达的非合并提交。"""

    args: Sequence[str] = _git_log_args(
        ref,
        since=since,
        until=until,
        no_merges=no_merges,
        reverse=reverse,
        max_count=max_count,
    )
    try:
        process = subprocess.Popen(
            ["git", *args],
            cwd=linux_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (FileNotFoundError, OSError) as exc:
        raise CommitSourceError(f"无法启动 git log：{exc}") from exc
    assert process.stdout is not None
    assert process.stderr is not None

    buffer = ""
    try:
        while chunk := process.stdout.read(64 * 1024):
            buffer += chunk
            records = buffer.split(RECORD_SEPARATOR)
            buffer = records.pop()
            for raw_record in records:
                commit = _parse_record(raw_record)
                if commit is not None:
                    yield commit
        commit = _parse_record(buffer)
        if commit is not None:
            yield commit
    except BaseException:
        if process.poll() is None:
            process.terminate()
        process.wait()
        process.stderr.close()
        raise
    finally:
        process.stdout.close()

    stderr = process.stderr.read().strip()
    process.stderr.close()
    return_code = process.wait()
    if return_code:
        raise CommitSourceError(
            f"git {' '.join(args)} 执行失败：{stderr or return_code}"
        )
