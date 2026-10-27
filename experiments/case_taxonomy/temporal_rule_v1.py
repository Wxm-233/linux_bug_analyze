"""Frozen v1: find moved statements, then check manually annotated P-before-C edges.

The scanner only proposes edits to review. The order checker requires a human
to identify P, C and the activation condition, and checks one C function body.
It cannot establish data flow, callback reachability or an actual kernel fault.
"""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


HEX40 = re.compile(r"\b[0-9a-f]{40}\b")
NONCODE = re.compile(r"//[^\n]*|/\*.*?\*/|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'", re.DOTALL)
CALL = re.compile(r"[A-Za-z_]\w*\s*\([^;{}]*\)\s*;")
ASSIGN = re.compile(r"[A-Za-z_][\w.>\-\[\]]*\s*=\s*[^;{}]+;")


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True, encoding="utf-8", capture_output=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def statement(line: str) -> tuple[str, str] | None:
    line = line.strip()
    if CALL.fullmatch(line):
        kind = "direct_call"
    elif ASSIGN.fullmatch(line):
        kind = "assignment"
    else:
        return None
    return kind, re.sub(r"\s+", "", line)


def moved_statements(root: Path, commit: str) -> dict:
    parents = git(root, "rev-list", "--parents", "-n", "1", commit).split()
    if len(parents) != 2:
        return {"status": "insufficient", "reason": "not a single-parent commit", "moves": []}
    patch = git(root, "show", "--format=", "--unified=0", "--no-ext-diff", commit)
    added, removed = {}, {}
    path = None
    for line in patch.splitlines():
        if line.startswith("diff --git a/"):
            match = re.match(r"diff --git a/(.+) b/(.+)$", line)
            path = match.group(2) if match else None
            continue
        if not path or line.startswith(("+++", "---")) or line[:1] not in ("+", "-"):
            continue
        candidate = statement(line[1:])
        if candidate is None:
            continue
        key = (path, candidate[0], candidate[1])
        target = added if line[0] == "+" else removed
        target[key] = target.get(key, 0) + 1
    moves = [
        {"file": path, "kind": kind, "statement": stmt,
         "paired_occurrences": min(added[(path, kind, stmt)], removed[(path, kind, stmt)])}
        for path, kind, stmt in sorted(added.keys() & removed.keys())
    ]
    return {"status": "flagged" if moves else "not_flagged", "moves": moves}


def mask_noncode(code: str) -> str:
    return NONCODE.sub(lambda m: re.sub(r"[^\n]", " ", m.group()), code)


def function_body(code: str, name: str) -> str:
    masked = mask_noncode(code)
    pattern = re.compile(r"\b" + re.escape(name) + r"\s*\([^;{}]*\)\s*\{")
    matches = list(pattern.finditer(masked))
    if len(matches) != 1:
        raise ValueError(f"{name} has {len(matches)} parseable definitions")
    opening = matches[0].end() - 1
    depth = 0
    for pos in range(opening, len(masked)):
        if masked[pos] == "{":
            depth += 1
        elif masked[pos] == "}":
            depth -= 1
            if depth == 0:
                return masked[opening + 1:pos]
    raise ValueError(f"{name} has unbalanced braces")


def order_at(root: Path, revision: str, contract: dict) -> dict:
    try:
        code = git(root, "show", f"{revision}:{contract['file']}")
        body = function_body(code, contract["function"])
        producer = list(re.finditer(contract["producer_regex"], body))
        consumer = list(re.finditer(contract["consumer_regex"], body))
        if len(producer) != 1 or len(consumer) != 1:
            raise ValueError(f"P matches={len(producer)}, C matches={len(consumer)}")
    except (RuntimeError, ValueError, re.error) as exc:
        return {"revision": revision, "A_true_order": "insufficient",
                "A_false_order": "not_applicable", "reason": str(exc)}
    relation = "P_before_C" if producer[0].start() < consumer[0].start() else "C_before_P"
    return {"revision": revision, "A_true_order": "ordered" if relation == "P_before_C" else "violation",
            "A_false_order": "not_applicable", "source_relation": relation,
            "P_offset": producer[0].start(), "C_offset": consumer[0].start()}


def evaluate_contract(root: Path, contract: dict) -> dict:
    fix = contract["fix_commit"]
    return {
        "id": contract["id"], "condition_A_human_annotation": contract["condition_A"],
        "failure_handling_human_annotation": contract["failure_handling"],
        "old": order_at(root, f"{fix}^", contract),
        "fixed": order_at(root, fix, contract),
        "scope": "lexical order inside one function; activation/data flow/failure are not automatically proven",
    }


def write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_training(args: argparse.Namespace) -> None:
    config = json.loads(args.config.read_text(encoding="utf-8"))
    candidate_checks = []
    for row in config["known_candidate_commits"]:
        actual = moved_statements(args.linux_dir, row["hash"])
        candidate_checks.append({"id": row["id"], "hash": row["hash"], **actual,
                                 "matches_expected": actual["status"] == row["expected"]})
    contracts = [evaluate_contract(args.linux_dir, c) for c in config["known_order_contracts"]]
    result = {"rule_version": 1, "candidate_checks": candidate_checks, "order_checks": contracts}
    write_json(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not all(row["matches_expected"] for row in candidate_checks):
        raise SystemExit("training candidate expectations failed")


def run_selection(args: argparse.Namespace) -> None:
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    exclusions = set()
    for path in args.exclude:
        exclusions.update(HEX40.findall(path.read_text(encoding="utf-8")))
    pool = [row for row in manifest["samples"]
            if row["stratum"] == "lifecycle" and row["hash"] not in exclusions]
    buckets = {"flagged": [], "not_flagged": [], "insufficient": []}
    for row in pool:
        probe = moved_statements(args.linux_dir, row["hash"])
        rank = hashlib.sha256(f"{args.seed}:{row['hash']}".encode()).hexdigest()
        buckets[probe["status"]].append({**row, "rule_status": probe["status"],
                                          "moves": probe["moves"], "rank": rank})
    for rows in buckets.values():
        rows.sort(key=lambda row: row["rank"])
    selected = buckets["flagged"][:2] + buckets["not_flagged"][:2]
    result = {
        "rule_version": 1,
        "policy": "lifecycle-only; exclude prior reviewed hashes; SHA256(seed:hash) rank; first 2 flagged plus first 2 not_flagged",
        "seed": args.seed,
        "script_sha256_before_source_review": checksum(Path(__file__)),
        "config_sha256": checksum(args.config),
        "manifest_sha256": checksum(args.manifest),
        "exclusion_files": [{"path": str(path), "sha256": checksum(path)} for path in args.exclude],
        "pool_count": len(pool),
        "bucket_counts": {key: len(value) for key, value in buckets.items()},
        "selected": selected,
        "selection_shortfall": len(selected) < 4,
        "source_reviewed_before_selection": False,
    }
    write_json(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("train", "select", "check"))
    parser.add_argument("--linux-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("temporal_rule_v1_contracts.json"))
    parser.add_argument("--contracts", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--exclude", type=Path, nargs="*", default=[])
    parser.add_argument("--seed", type=int, default=20260926)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "train":
        run_training(args)
    elif args.command == "select":
        if args.manifest is None:
            parser.error("select requires --manifest")
        run_selection(args)
    else:
        if args.contracts is None:
            parser.error("check requires --contracts")
        contracts = json.loads(args.contracts.read_text(encoding="utf-8"))
        result = {"rule_version": 1, "script_sha256": checksum(Path(__file__)),
                  "checks": [evaluate_contract(args.linux_dir, row) for row in contracts["contracts"]]}
        write_json(args.output, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
