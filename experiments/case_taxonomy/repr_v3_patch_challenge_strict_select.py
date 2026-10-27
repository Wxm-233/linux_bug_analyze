"""Select at most two exact before/after compound-conversion patch pairs.

Fix diffs are intentionally read for this diagnostic selection; it is not a
blind source-only evaluation. The parent source is left for the frozen checker.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


MAX_LOG_MATCHES = 600
MAX_TARGETS = 2
EXCLUDED = (
    "09f688f", "b802a8c", "faa4dde", "89aba9c", "41f0200",
    "ef488e4", "9cefd6e", "0493e73", "2bbdfcc", "82697cc",
    "0aae2c7", "355f388", "eae6460", "f99d3b4", "d11c05d",
)
REMOVED = re.compile(r"^-(?!-)(?P<lhs>[^;\n]+?)\s*\|=\s*(?P<rhs>[^;\n]+);\s*$")
ADDED = re.compile(
    r"^\+(?!\+)(?P<lhs>[^;\n]+?)\s*\|=\s*"
    r"cpu_to_(?P<order>le|be)(?P<bits>16|32|64)\s*\((?P<rhs>.+)\);\s*$"
)


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True, encoding="utf-8", errors="replace", capture_output=True,
        check=check,
    )


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def exact_pairs(patch_lines: list[str]) -> list[dict]:
    removed = set()
    for line in patch_lines:
        match = REMOVED.match(line)
        if match and not re.match(r"cpu_to_(?:le|be)(?:16|32|64)\s*\(",
                                  match.group("rhs").strip()):
            removed.add((compact(match.group("lhs")), compact(match.group("rhs"))))
    pairs = []
    for line in patch_lines:
        match = ADDED.match(line)
        if match and (compact(match.group("lhs")), compact(match.group("rhs"))) in removed:
            pairs.append({
                "lhs": compact(match.group("lhs")),
                "rhs": compact(match.group("rhs")),
                "conversion": f"cpu_to_{match.group('order')}{match.group('bits')}",
            })
    return pairs


def select(repo: Path) -> dict:
    commits = git(
        repo, "log", "--all", "--no-merges", "--since=2018-01-01",
        "--until=2026-09-28", f"--max-count={MAX_LOG_MATCHES}",
        "--format=%H", "-G", r"cpu_to_(le|be)(16|32|64)\(", "--", "drivers",
    ).stdout.splitlines()
    selected = []
    used_directories = set()
    examined = 0
    for commit in commits:
        examined += 1
        if any(commit.startswith(prefix) for prefix in EXCLUDED):
            continue
        paths = git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r",
                    commit, "--", "drivers").stdout.splitlines()
        for path in paths:
            if not path.startswith("drivers/") or not path.endswith(".c"):
                continue
            directory = str(Path(path).parent)
            if directory in used_directories:
                continue
            patch = git(repo, "show", "--format=", "--unified=0", "--no-ext-diff",
                        commit, "--", path).stdout.splitlines()
            pairs = exact_pairs(patch)
            if not pairs:
                continue
            parent = git(repo, "rev-parse", f"{commit}^").stdout.strip()
            if git(repo, "cat-file", "-e", f"{parent}:{path}", check=False).returncode:
                continue
            selected.append({
                "fix_commit": commit,
                "old_revision": parent,
                "source_path": path,
                "subject": git(repo, "show", "-s", "--format=%s", commit).stdout.strip(),
                "matched_same_lhs_rhs_pairs": pairs,
            })
            used_directories.add(directory)
            break
        if len(selected) >= MAX_TARGETS:
            break
    return {
        "stage": "strict patch-informed selection before parent-source checker run",
        "selected_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "query_cap_matching_commits": MAX_LOG_MATCHES,
        "examined_matching_commits": examined,
        "max_targets": MAX_TARGETS,
        "selection_rule": "same C file has complete -lhs |= rhs; and +lhs |= cpu_to_le/be16/32/64(rhs); lines, with whitespace-normalized identical lhs/rhs; first two distinct driver directories in Git log order",
        "interpretation_limit": "Fix diff informed selection and expected conversion; this challenges frozen source parser only, not blind issue discovery or prevalence.",
        "targets": selected,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(select(args.repo), indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")


if __name__ == "__main__":
    main()
