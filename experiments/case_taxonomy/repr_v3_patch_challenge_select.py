"""Deterministically select a small, patch-informed parser challenge set.

This script intentionally sees fix patches to select matching syntax. Its
output is unsuitable for claims about blind discovery or defect prevalence.
It never reads the parent source file that the frozen checker will inspect.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


MAX_LOG_MATCHES = 300
MAX_TARGETS = 3
EXCLUDED_FIX_PREFIXES = (
    "09f688f",  # PWM development
    "b802a8c",  # idpf development
    "faa4dde",  # fsl_raid development
    "89aba9c",  # dw-axi development
    "41f0200",  # Tegra241 development
    "ef488e4",  # gs_usb prior holdout
    "9cefd6e",  # lpfc prior holdout
    "0493e73",  # v3 title holdout
    "2bbdfcc",  # v3 title holdout
    "82697cc",  # v3 title holdout
    "0aae2c7",  # v3 title holdout
    "355f388",  # v3 scope control
)
ADDED_COMPOUND_CONVERSION = re.compile(
    r"^\+(?!\+).*\|=\s*cpu_to_(?:le|be)(?:32|64)\s*\("
)
REMOVED_UNCONVERTED_COMPOUND = re.compile(
    r"^-(?!-).*\|=\s*(?!cpu_to_(?:le|be)(?:32|64)\s*\()"
)


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True, encoding="utf-8", errors="replace", capture_output=True,
        check=check,
    )


def select(repo: Path) -> dict:
    commits = git(
        repo, "log", "--all", "--no-merges", "--since=2020-01-01",
        "--until=2026-09-28", f"--max-count={MAX_LOG_MATCHES}",
        "--format=%H", "-G", r"cpu_to_(le|be)(32|64)\(", "--", "drivers",
    ).stdout.splitlines()
    selected: list[dict] = []
    examined = 0
    used_directories: set[str] = set()
    for commit in commits:
        examined += 1
        if any(commit.startswith(prefix) for prefix in EXCLUDED_FIX_PREFIXES):
            continue
        paths = git(
            repo, "diff-tree", "--no-commit-id", "--name-only", "-r",
            commit, "--", "drivers",
        ).stdout.splitlines()
        for source_path in paths:
            if not source_path.startswith("drivers/") or not source_path.endswith(".c"):
                continue
            directory = str(Path(source_path).parent)
            if directory in used_directories:
                continue
            patch = git(
                repo, "show", "--format=", "--unified=0", "--no-ext-diff",
                commit, "--", source_path,
            ).stdout.splitlines()
            if not any(ADDED_COMPOUND_CONVERSION.search(line) for line in patch):
                continue
            if not any(REMOVED_UNCONVERTED_COMPOUND.search(line) for line in patch):
                continue
            parent = git(repo, "rev-parse", f"{commit}^").stdout.strip()
            exists = git(repo, "cat-file", "-e", f"{parent}:{source_path}", check=False)
            if exists.returncode != 0:
                continue
            subject = git(repo, "show", "-s", "--format=%s", commit).stdout.strip()
            selected.append({
                "fix_commit": commit,
                "old_revision": parent,
                "source_path": source_path,
                "subject": subject,
                "selection_evidence": "same changed C file has added |= cpu_to_le/be32/64(...) and removed unconverted |= line",
            })
            used_directories.add(directory)
            break
        if len(selected) >= MAX_TARGETS:
            break
    return {
        "stage": "patch-informed selection before any parent-source checker run",
        "selected_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "query_cap_matching_commits": MAX_LOG_MATCHES,
        "examined_matching_commits": examined,
        "max_targets": MAX_TARGETS,
        "selection_rule": "latest Git log order; exact added/removed compound-conversion lines in one changed C file; first eligible in each distinct driver directory; fixed exclusions",
        "interpretation_limit": "Fix patches are used to select challenges. This tests source-parser transfer on syntax-matched historical revisions, not blind discovery, prevalence, or end-to-end accuracy.",
        "targets": selected,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = select(args.repo)
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")


if __name__ == "__main__":
    main()
