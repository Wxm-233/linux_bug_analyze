"""Freeze a bounded Bluetooth/HCI title/path pool without reading patches or source.

Only Git commit metadata and changed path names are requested. Existing research
files are scanned solely for candidate SHA prefixes, to avoid reusing read cases.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


LINUX = Path("/root/repos/linux")
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "metadata_pool.json"
SINCE = "2016-01-01"
UNTIL = "2022-12-31"
LIMIT = 60
SCOPES = (
    ("hci_core_first", ("net/bluetooth/hci_core.c",)),
    ("net_bluetooth", ("net/bluetooth",)),
    ("include_net_bluetooth", ("include/net/bluetooth",)),
    ("drivers_bluetooth", ("drivers/bluetooth",)),
)
PATHS = ("net/bluetooth", "include/net/bluetooth", "drivers/bluetooth")
TITLE = re.compile(r"endian|byte[ -]?order|convert|cpu_to|le16|le32", re.I)
TEXT_SUFFIXES = {".md", ".json", ".tsv", ".txt", ".py", ".csv"}


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(LINUX), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout


def prior_mentions(records: list[dict]) -> None:
    # Eight hex digits are enough here for a conservative exclusion search.
    prefixes = {item["revision"][:8]: item for item in records}
    pattern = re.compile(b"|".join(key.encode() for key in prefixes), re.I)
    for item in records:
        item["prior_sha_prefix_mentions"] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if "contract_authority_20261001" in path.parts:
            continue
        relative = path.relative_to(ROOT).as_posix()
        with path.open("rb") as handle:
            overlap = b""
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                for match in pattern.finditer(overlap + chunk):
                    name = relative
                    hits = prefixes[match.group().decode().lower()]["prior_sha_prefix_mentions"]
                    if name not in hits:
                        hits.append(name)
                overlap = chunk[-7:]


def main() -> None:
    records: list[dict] = []
    seen: set[str] = set()
    scope_counts: dict[str, int] = {}
    for scope, paths in SCOPES:
        raw = git(
            "log", "--all", "--no-merges", f"--since={SINCE}",
            f"--until={UNTIL}", "--format=%H%x1f%P%x1f%cs%x1f%s",
            "--", *paths,
        )
        scope_counts[scope] = 0
        for line in raw.splitlines():
            parts = line.split("\x1f", 3)
            if len(parts) != 4:
                raise ValueError(f"unexpected Git metadata line: {line[:80]!r}")
            revision, parents, date, title = parts
            if not TITLE.search(title) or revision in seen:
                continue
            if len(records) >= LIMIT:
                break
            seen.add(revision)
            scope_counts[scope] += 1
            changed_paths = git(
                "diff-tree", "--no-commit-id", "--name-only", "-r",
                revision, "--", *PATHS,
            ).splitlines()
            records.append(
                {
                    "revision": revision,
                    "parent": parents,
                    "date": date,
                    "title": title,
                    "matched_scope": scope,
                    "paths": changed_paths,
                }
            )
        if len(records) >= LIMIT:
            break
    prior_mentions(records)
    output = {
        "stage": "metadata_only_before_any_target_patch_or_source_read",
        "repository": str(LINUX),
        "query": {
            "date_range": [SINCE, UNTIL],
            "git_log": "git -C /root/repos/linux log --all --no-merges --since=2016-01-01 --until=2022-12-31 --format=%H%x1f%P%x1f%cs%x1f%s -- <scope>",
            "scopes_in_priority_order": [dict(name=name, paths=list(paths)) for name, paths in SCOPES],
            "subject_regex": TITLE.pattern,
            "changed_paths": "git -C /root/repos/linux diff-tree --no-commit-id --name-only -r <revision> -- net/bluetooth include/net/bluetooth drivers/bluetooth",
            "prior_mentions": "literal first 8 hex digits of candidate revision in case_taxonomy text files, excluding this selection directory",
            "limit": LIMIT,
        },
        "counts_by_first_matching_scope": scope_counts,
        "pool_count": len(records),
        "pool": records,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(records)} metadata-only records to {OUT}")


if __name__ == "__main__":
    main()
