"""从 linux-cve-announce 邮件中提取候选修复提交。"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from email import policy
from email.message import Message
from email.parser import BytesParser
from pathlib import Path
from urllib.parse import quote

from .public_inbox import InboxMessage, iter_inbox_messages


CVE_RE = re.compile(r"\bCVE-\d{4}-\d{4,}\b", re.IGNORECASE)
FIXED_RE = re.compile(
    r"\bFixed\s+in\s+([^\s,;]+)\s+with\s+commit\s+([0-9a-f]{7,64})\b",
    re.IGNORECASE,
)
COMMIT_URL_PATTERNS = (
    re.compile(
        r"https?://git\.kernel\.org/(?:stable/c/|linus/)([0-9a-f]{7,64})\b",
        re.I,
    ),
    re.compile(r"https?://git\.kernel\.org/[^\s]*[?&]id=([0-9a-f]{7,64})\b", re.I),
)


class CveSourceError(RuntimeError):
    """CVE 邮件或主线仓库无法处理。"""


@dataclass(slots=True)
class FixReference:
    reported_hash: str
    versions: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    in_linux_repo: bool = False
    canonical_hash: str = ""
    selected: bool = False
    emitted: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "reported_hash": self.reported_hash,
            "versions": self.versions,
            "sources": self.sources,
            "in_linux_repo": self.in_linux_repo,
            "canonical_hash": self.canonical_hash,
            "selected": self.selected,
            "emitted": self.emitted,
        }


@dataclass(slots=True)
class CveMailRecord:
    epoch: int
    storage_commit: str
    message_id: str
    subject: str
    date: str
    cve_ids: list[str]
    fixes: list[FixReference]
    status: str = "pending"
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        clean_message_id = self.message_id.strip("<>")
        permalink = (
            f"https://lore.kernel.org/r/{quote(clean_message_id, safe='@._+-')}"
            if clean_message_id
            else ""
        )
        return {
            "epoch": self.epoch,
            "storage_commit": self.storage_commit,
            "message_id": self.message_id,
            "permalink": permalink,
            "subject": self.subject,
            "date": self.date,
            "cve_ids": self.cve_ids,
            "status": self.status,
            "reason": self.reason,
            "fixes": [fix.to_dict() for fix in self.fixes],
        }


def _message_body(message: Message) -> str:
    parts: list[str] = []
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() != "text/plain":
                continue
            if part.get_content_disposition() == "attachment":
                continue
            try:
                parts.append(part.get_content())
            except (LookupError, UnicodeDecodeError):
                payload = part.get_payload(decode=True) or b""
                parts.append(payload.decode("utf-8", errors="replace"))
    else:
        try:
            parts.append(message.get_content())
        except (LookupError, UnicodeDecodeError):
            payload = message.get_payload(decode=True) or b""
            parts.append(payload.decode("utf-8", errors="replace"))
    return "\n".join(str(part) for part in parts)


def parse_cve_message(inbox_message: InboxMessage) -> CveMailRecord:
    """解析邮件头并提取结构化修复引用。"""

    raw = inbox_message.raw_message
    if raw.startswith(b"From "):
        raw = raw.split(b"\n", 1)[1] if b"\n" in raw else b""
    message = BytesParser(policy=policy.default).parsebytes(raw)
    subject = str(message.get("Subject", ""))
    body = _message_body(message)
    combined = f"{subject}\n{body}"
    cve_ids = list(dict.fromkeys(match.upper() for match in CVE_RE.findall(combined)))

    references: dict[str, FixReference] = {}
    for version, commit_hash in FIXED_RE.findall(body):
        normalized = commit_hash.lower()
        reference = references.setdefault(normalized, FixReference(normalized))
        if version not in reference.versions:
            reference.versions.append(version)
        if "fixed-line" not in reference.sources:
            reference.sources.append("fixed-line")
    for pattern in COMMIT_URL_PATTERNS:
        for commit_hash in pattern.findall(body):
            normalized = commit_hash.lower()
            reference = references.setdefault(normalized, FixReference(normalized))
            if "git.kernel.org-url" not in reference.sources:
                reference.sources.append("git.kernel.org-url")

    return CveMailRecord(
        epoch=inbox_message.epoch,
        storage_commit=inbox_message.storage_commit,
        message_id=str(message.get("Message-ID", "")),
        subject=subject,
        date=str(message.get("Date", "")),
        cve_ids=cve_ids,
        fixes=list(references.values()),
    )


def read_cve_records(inbox_dir: Path) -> list[CveMailRecord]:
    """读取镜像并按 Message-ID 去重；没有 Message-ID 时按存储 commit 区分。"""

    records: list[CveMailRecord] = []
    seen: set[str] = set()
    for inbox_message in iter_inbox_messages(inbox_dir):
        record = parse_cve_message(inbox_message)
        identity = record.message_id.lower() or f"git:{record.epoch}:{record.storage_commit}"
        if identity in seen:
            continue
        seen.add(identity)
        records.append(record)
    return records


def resolve_linux_commits(linux_dir: Path, hashes: list[str]) -> dict[str, str]:
    """用单个 ``git cat-file --batch-check`` 判断引用是否存在于主线仓库。"""

    unique_hashes = list(dict.fromkeys(commit_hash.lower() for commit_hash in hashes))
    if not unique_hashes:
        return {}
    try:
        process = subprocess.Popen(
            ["git", "cat-file", "--batch-check=%(objectname) %(objecttype)"],
            cwd=linux_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (FileNotFoundError, OSError) as exc:
        raise CveSourceError(f"无法检查 Linux Git 对象：{exc}") from exc
    assert process.stdin is not None
    assert process.stdout is not None
    assert process.stderr is not None

    resolved: dict[str, str] = {}
    queries = "".join(f"{commit_hash}^{{commit}}\n" for commit_hash in unique_hashes)
    stdout, stderr = process.communicate(queries)
    for commit_hash, line in zip(unique_hashes, stdout.splitlines()):
        parts = line.split()
        if len(parts) == 2 and parts[1] == "commit":
            resolved[commit_hash] = parts[0]
    if process.returncode != 0:
        raise CveSourceError(f"git cat-file 检查失败：{stderr.strip() or process.returncode}")
    return resolved


def select_candidates(
    records: list[CveMailRecord],
    linux_dir: Path | None,
    *,
    prefer_mainline: bool,
    fallback_to_all: bool,
) -> list[str]:
    """选择候选 hash，并在每条邮件记录中保留完整选择依据。"""

    if prefer_mainline and linux_dir is None:
        raise CveSourceError("prefer_mainline=true 时必须提供 linux_dir。")
    all_hashes = [fix.reported_hash for record in records for fix in record.fixes]
    resolved = (
        resolve_linux_commits(linux_dir, all_hashes)
        if prefer_mainline and linux_dir
        else {}
    )
    emitted: set[str] = set()
    candidates: list[str] = []

    for record in records:
        for fix in record.fixes:
            canonical = resolved.get(fix.reported_hash, "")
            fix.in_linux_repo = bool(canonical)
            fix.canonical_hash = canonical

        if not record.cve_ids:
            record.status = "ignored"
            record.reason = "邮件中未找到 CVE 编号"
            continue
        if not record.fixes:
            record.status = "no-fixes"
            record.reason = "未找到 Fixed in/commit URL 修复引用"
            continue

        selectable = (
            [fix for fix in record.fixes if fix.in_linux_repo]
            if prefer_mainline
            else list(record.fixes)
        )
        if prefer_mainline and not selectable and fallback_to_all:
            selectable = list(record.fixes)
            record.reason = "主线仓库未找到引用，按配置回退到全部修复"
        elif prefer_mainline and not selectable:
            record.status = "unresolved"
            record.reason = "修复引用均不在 linux_dir 指向的仓库中"
            continue
        else:
            record.reason = (
                "选择 linux_dir 中存在的主线提交"
                if prefer_mainline
                else "选择全部修复引用"
            )

        record.status = "selected"
        for fix in selectable:
            fix.selected = True
            output_hash = fix.canonical_hash or fix.reported_hash
            if output_hash not in emitted:
                emitted.add(output_hash)
                fix.emitted = True
                candidates.append(output_hash)
    return candidates
