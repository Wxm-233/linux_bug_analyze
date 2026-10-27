"""v2 source-edit candidates: compare complete C statements and function context.

This is a candidate extractor, not a defect classifier. It does not infer
provider/consumer roles, data flow, configuration reachability or failure paths.
"""

import argparse
import bisect
import hashlib
import json
import re
import subprocess
from pathlib import Path


HEX40 = re.compile(r"\b[0-9a-f]{40}\b")
NONCODE = re.compile(r"//[^\n]*|/\*.*?\*/|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'", re.DOTALL)
HUNK = re.compile(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*)")
CALL = re.compile(r"([A-Za-z_]\w*)\s*\(.*\)\s*;", re.DOTALL)
ASSIGN = re.compile(r"[A-Za-z_][\w.>\-\[\]]*\s*=\s*[^;{}]+;", re.DOTALL)
CONTROL = {"if", "for", "while", "switch", "return", "sizeof"}


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args],
                            text=True, encoding="utf-8", errors="replace", capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mask(code: str) -> str:
    masked = NONCODE.sub(lambda m: re.sub(r"[^\n]", " ", m.group()), code)
    lines = masked.splitlines(keepends=True)
    original_lines = code.splitlines(keepends=True)
    in_macro = False
    for i, line in enumerate(lines):
        original = original_lines[i]
        if in_macro or line.lstrip().startswith("#"):
            lines[i] = re.sub(r"[^\n]", " ", line)
            in_macro = original.rstrip().endswith("\\")
    return "".join(lines)


def balanced_parens(text: str) -> bool:
    depth = 0
    for char in text:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def classify(statement_masked: str) -> str | None:
    statement_masked = statement_masked.strip()
    if not balanced_parens(statement_masked):
        return None
    call = CALL.fullmatch(statement_masked)
    if call and call.group(1) not in CONTROL:
        return "direct_call"
    if ASSIGN.fullmatch(statement_masked):
        return "assignment"
    return None


def statements(code: str) -> list[dict]:
    masked = mask(code)
    newline_offsets = [i for i, char in enumerate(code) if char == "\n"]
    found = []
    start = 0
    parens = 0
    for i, char in enumerate(masked):
        if char == "(":
            parens += 1
        elif char == ")":
            parens -= 1
        elif char in "{}" and parens == 0:
            start = i + 1
        elif char == ";" and parens == 0:
            raw_fragment = code[start:i + 1]
            masked_fragment = masked[start:i + 1]
            kind = classify(masked_fragment)
            if kind:
                first = bisect.bisect_right(newline_offsets, start) + 1
                last = bisect.bisect_right(newline_offsets, i) + 1
                found.append({"first": first, "last": last, "kind": kind,
                              "text": re.sub(r"\s+", "", raw_fragment.strip())})
            start = i + 1
    return found


def context(header: str) -> str | None:
    calls = re.findall(r"\b([A-Za-z_]\w*)\s*\(", header)
    if not calls or calls[-1].startswith(("DEFINE_", "EXPORT_")):
        return None
    return calls[-1]


def changed_lines(patch: str) -> dict:
    files = {}
    path = None
    old_line = new_line = None
    current_context = None
    for line in patch.splitlines():
        if line.startswith("diff --git a/"):
            match = re.match(r"diff --git a/(.+) b/(.+)$", line)
            path = match.group(2) if match and match.group(2).endswith(".c") else None
            if path:
                files[path] = {"old": {}, "new": {}}
            continue
        match = HUNK.match(line)
        if match:
            old_line, new_line = int(match.group(1)), int(match.group(2))
            current_context = context(match.group(3))
            continue
        if path is None or old_line is None or line.startswith(("+++", "---")):
            continue
        if line.startswith("-"):
            files[path]["old"][old_line] = current_context
            old_line += 1
        elif line.startswith("+"):
            files[path]["new"][new_line] = current_context
            new_line += 1
        elif line.startswith(" "):
            old_line += 1
            new_line += 1
    return files


def touched_statements(code: str, line_contexts: dict[int, str | None]) -> dict:
    found = {}
    for item in statements(code):
        contexts = {line_contexts[n] for n in range(item["first"], item["last"] + 1)
                    if n in line_contexts}
        if not contexts:
            continue
        key = (item["kind"], item["text"])
        found.setdefault(key, []).append({"first": item["first"], "last": item["last"],
                                            "contexts": sorted(x for x in contexts if x)})
    return found


def inspect_commit(root: Path, commit: str) -> dict:
    try:
        parents = git(root, "rev-list", "--parents", "-n", "1", commit).split()
        if len(parents) != 2:
            return {"status": "insufficient", "reason": "not a single-parent commit", "moves": []}
        patch = git(root, "show", "--format=", "--unified=0", "--no-ext-diff", commit)
        files = changed_lines(patch)
        moves = []
        for path, changed in files.items():
            if not changed["old"] or not changed["new"]:
                continue
            old = touched_statements(git(root, "show", f"{commit}^:{path}"), changed["old"])
            new = touched_statements(git(root, "show", f"{commit}:{path}"), changed["new"])
            for kind, statement in sorted(old.keys() & new.keys()):
                old_ctx = sorted({c for item in old[(kind, statement)] for c in item["contexts"]})
                new_ctx = sorted({c for item in new[(kind, statement)] for c in item["contexts"]})
                if len(old_ctx) == len(new_ctx) == 1:
                    category = "same_function" if old_ctx[0] == new_ctx[0] else "cross_function"
                else:
                    category = "context_insufficient"
                moves.append({"file": path, "kind": kind, "statement": statement,
                              "old_context": old_ctx, "new_context": new_ctx, "category": category})
        categories = {row["category"] for row in moves}
        if "same_function" in categories:
            status = "same_function_candidate"
        elif "cross_function" in categories:
            status = "cross_function_candidate"
        elif "context_insufficient" in categories:
            status = "insufficient"
        else:
            status = "not_flagged"
        return {"status": status, "moves": moves}
    except RuntimeError as exc:
        return {"status": "insufficient", "reason": str(exc), "moves": []}


def save(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def train(args: argparse.Namespace) -> None:
    config = json.loads(args.config.read_text(encoding="utf-8"))
    rows = []
    for row in config["known"]:
        actual = inspect_commit(args.linux_dir, row["hash"])
        rows.append({"id": row["id"], "hash": row["hash"], "expected": row["expected"],
                     **actual, "matches_expected": actual["status"] == row["expected"]})
    result = {"rule_version": 2, "rows": rows}
    save(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not all(row["matches_expected"] for row in rows):
        raise SystemExit("known-case expectations failed")


def select(args: argparse.Namespace) -> None:
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    excluded = set()
    for path in args.exclude:
        excluded.update(HEX40.findall(path.read_text(encoding="utf-8")))
    pool = [row for row in manifest["samples"]
            if row["stratum"] == "lifecycle" and row["hash"] not in excluded]
    buckets = {name: [] for name in ("same_function_candidate", "cross_function_candidate", "not_flagged", "insufficient")}
    for row in pool:
        probe = inspect_commit(args.linux_dir, row["hash"])
        rank = hashlib.sha256(f"{args.seed}:{row['hash']}".encode()).hexdigest()
        buckets[probe["status"]].append({**row, "rank": rank, **probe})
    for rows in buckets.values():
        rows.sort(key=lambda row: row["rank"])
    chosen = (buckets["same_function_candidate"][:1] +
              buckets["cross_function_candidate"][:1] + buckets["not_flagged"][:2])
    result = {"rule_version": 2, "policy": "lifecycle, excluded known, SHA rank: 1 same, 1 cross, 2 unflagged",
              "seed": args.seed, "script_sha256": sha(Path(__file__)), "config_sha256": sha(args.config),
              "manifest_sha256": sha(args.manifest),
              "exclusion_files": [{"path": str(path), "sha256": sha(path)} for path in args.exclude],
              "pool_count": len(pool), "bucket_counts": {k: len(v) for k, v in buckets.items()},
              "selected": chosen, "selection_shortfall": len(chosen) < 4}
    save(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("train", "select"))
    parser.add_argument("--linux-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("temporal_rule_v2_known.json"))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--exclude", type=Path, nargs="*", default=[])
    parser.add_argument("--seed", default="20260926-v2")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "train":
        train(args)
    else:
        if args.manifest is None:
            parser.error("select requires --manifest")
        select(args)


if __name__ == "__main__":
    main()
