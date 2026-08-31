"""为单个提交收集可在本地获得的补充证据。"""

from __future__ import annotations

import re
from collections.abc import Iterable
from email import policy
from email.message import Message
from email.parser import BytesParser
from pathlib import Path
from urllib.parse import unquote, urlparse

from .cve_source import read_cve_records
from .git_repository import GitRepository
from .models import CommitInfo
from .public_inbox import iter_inbox_messages


FIXES_RE = re.compile(r"^Fixes:\s*([0-9a-f]{7,64})\b", re.IGNORECASE | re.MULTILINE)
LORE_URL_RE = re.compile(
    r"^\s*(?:Link|Closes):\s*(https?://lore\.kernel\.org/\S+)",
    re.IGNORECASE | re.MULTILINE,
)


def read_supplemental_evidence(evidence_dir: Path | None, commit_hash: str) -> str:
    """读取 ``<hash>.md`` 或 ``<hash>.txt``；未配置时返回空文本。"""

    if evidence_dir is None:
        return ""
    for suffix in (".md", ".txt"):
        candidate = evidence_dir / f"{commit_hash}{suffix}"
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    return ""


def _message_body(message: Message) -> str:
    parts: list[str] = []
    candidates = message.walk() if message.is_multipart() else (message,)
    for part in candidates:
        if part.get_content_type() != "text/plain":
            continue
        if part.get_content_disposition() == "attachment":
            continue
        try:
            parts.append(str(part.get_content()))
        except (LookupError, UnicodeDecodeError):
            payload = part.get_payload(decode=True) or b""
            parts.append(payload.decode("utf-8", errors="replace"))
    return "\n".join(parts).strip()


def _parse_message(raw: bytes) -> tuple[str, str, str]:
    if raw.startswith(b"From "):
        raw = raw.split(b"\n", 1)[1] if b"\n" in raw else b""
    message = BytesParser(policy=policy.default).parsebytes(raw)
    message_id = str(message.get("Message-ID", "")).strip().strip("<>").lower()
    return message_id, str(message.get("Subject", "")), _message_body(message)


def linked_message_ids(commit_body: str) -> tuple[str, ...]:
    """从 Link/Closes trailer 的 lore URL 提取 Message-ID。"""

    message_ids: list[str] = []
    for url in LORE_URL_RE.findall(commit_body):
        path_parts = [part for part in urlparse(url).path.split("/") if part]
        if not path_parts:
            continue
        candidate = unquote(path_parts[-1]).strip("<>").lower()
        if candidate == "raw" and len(path_parts) > 1:
            candidate = unquote(path_parts[-2]).strip("<>").lower()
        if "@" in candidate and candidate not in message_ids:
            message_ids.append(candidate)
    return tuple(message_ids)


class EvidenceCollector:
    """组合人工证据、引入提交、CVE 公告和本地邮件讨论。"""

    def __init__(
        self,
        repository: GitRepository,
        *,
        evidence_dir: Path | None = None,
        cve_inbox_dir: Path | None = None,
        mail_inbox_dirs: Iterable[Path] = (),
        include_fixes_commit: bool = True,
        max_chars_per_source: int = 12_000,
        max_total_chars: int = 36_000,
    ):
        self.repository = repository
        self.evidence_dir = evidence_dir
        self.cve_inbox_dir = cve_inbox_dir
        self.mail_inbox_dirs = tuple(mail_inbox_dirs)
        self.include_fixes_commit = include_fixes_commit
        self.max_chars_per_source = max_chars_per_source
        self.max_total_chars = max_total_chars
        self._automatic: dict[str, list[tuple[str, str]]] = {}

    def prepare(self, hashes: Iterable[str]) -> None:
        """为一批提交一次性建立本地邮件索引，避免逐提交扫描镜像。"""

        if self.cve_inbox_dir is None and not self.mail_inbox_dirs:
            return
        commits: dict[str, CommitInfo] = {}
        message_to_commits: dict[str, set[str]] = {}
        for commit_hash in hashes:
            try:
                commit = self.repository.get_commit(commit_hash, 0, include_diff=False)
            except Exception:
                continue
            commits[commit.hash] = commit
            for message_id in linked_message_ids(commit.body):
                message_to_commits.setdefault(message_id, set()).add(commit.hash)

        if self.cve_inbox_dir is not None:
            cve_read_failed = False
            try:
                records = read_cve_records(self.cve_inbox_dir)
            except Exception as exc:
                cve_read_failed = True
                for full_hash in commits:
                    self._add(
                        full_hash,
                        "证据采集状态",
                        f"CVE 公告镜像读取失败：{exc}",
                    )
                records = []
            matched_cve_hashes: set[str] = set()
            for record in records:
                matching = {
                    full_hash
                    for full_hash in commits
                    if any(
                        full_hash.startswith(fix.reported_hash.lower())
                        for fix in record.fixes
                    )
                }
                if not matching:
                    continue
                content = (
                    f"主题：{record.subject}\nMessage-ID：{record.message_id}\n"
                    f"CVE：{', '.join(record.cve_ids) or '未知'}\n\n{record.body}"
                )
                for full_hash in matching:
                    self._add(full_hash, "linux-cve-announce 公告", content)
                    matched_cve_hashes.add(full_hash)
            if not cve_read_failed:
                for full_hash in set(commits) - matched_cve_hashes:
                    self._add(
                        full_hash,
                        "证据采集状态",
                        "已检索 CVE 公告镜像，但未匹配到该主线提交。",
                    )

        if message_to_commits:
            wanted = set(message_to_commits)
            found: set[str] = set()
            for inbox_dir in self.mail_inbox_dirs:
                try:
                    messages = iter_inbox_messages(inbox_dir)
                    for inbox_message in messages:
                        message_id, subject, body = _parse_message(
                            inbox_message.raw_message
                        )
                        if message_id not in wanted:
                            continue
                        found.add(message_id)
                        content = (
                            f"主题：{subject}\nMessage-ID：<{message_id}>\n\n{body}"
                        )
                        for full_hash in message_to_commits[message_id]:
                            self._add(full_hash, "本地邮件讨论", content)
                except Exception as exc:
                    for full_hash in commits:
                        self._add(
                            full_hash,
                            "证据采集状态",
                            f"邮件镜像 {inbox_dir} 读取失败：{exc}",
                        )
            for message_id in wanted - found:
                for full_hash in message_to_commits[message_id]:
                    self._add(
                        full_hash,
                        "证据采集状态",
                        f"已配置的邮件镜像中未找到 Message-ID <{message_id}>。",
                    )

    def _add(self, commit_hash: str, label: str, content: str) -> None:
        clipped = content.strip()[: self.max_chars_per_source]
        if clipped:
            self._automatic.setdefault(commit_hash, []).append((label, clipped))

    def _fixes_evidence(self, commit: CommitInfo) -> list[tuple[str, str]]:
        if not self.include_fixes_commit:
            return []
        sections: list[tuple[str, str]] = []
        for fixes_hash in dict.fromkeys(FIXES_RE.findall(commit.body)):
            try:
                fixed = self.repository.get_commit(fixes_hash, self.max_chars_per_source)
            except Exception as exc:
                sections.append(("Fixes 引入提交", f"{fixes_hash} 无法读取：{exc}"))
                continue
            files = "\n".join(fixed.files) or "（无）"
            content = (
                f"哈希：{fixed.hash}\n标题：{fixed.subject}\n"
                f"提交说明：\n{fixed.body or '（无）'}\n"
                f"变更文件：\n{files}\n代码差异：\n{fixed.diff or '（无）'}"
            )
            sections.append(("Fixes 引入提交", content))
        return sections

    def collect(self, commit: CommitInfo) -> str:
        sections = list(self._automatic.get(commit.hash, ()))
        linked_ids = linked_message_ids(commit.body)
        if linked_ids and not self.mail_inbox_dirs:
            sections.append(
                (
                    "证据采集状态",
                    "提交含 lore Link/Closes，但未配置 [evidence].mail_inbox_dirs；"
                    "邮件讨论尚未检索。",
                )
            )
        sections.extend(self._fixes_evidence(commit))
        manual = read_supplemental_evidence(self.evidence_dir, commit.hash).strip()
        if manual:
            sections.append(("人工补充材料", manual))

        rendered: list[str] = []
        used = 0
        for label, content in sections:
            block = f"===== {label} =====\n{content.strip()}"
            remaining = self.max_total_chars - used
            if remaining <= 0:
                break
            block = block[:remaining]
            rendered.append(block)
            used += len(block)
        return "\n\n".join(rendered)
