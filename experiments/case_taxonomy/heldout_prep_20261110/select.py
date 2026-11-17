"""Mechanical candidate selection for the LoongArch held-out set (heldout_prep criteria 二). Runs in WSL.

    python3 select.py -> candidates.json   (commit ids and counts only; subjects and diffs are never printed)
"""
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
K = "/root/repos/linux"
EXCL = re.compile(r"(^|/)(Kconfig[^/]*|Makefile[^/]*)$|\.dts|\.lds|^Documentation/|\.S$")
OWN = re.compile(r"^arch/loongarch/|loongarch|loongson")
FUNC = re.compile(r"([A-Za-z_]\w*)\s*\(")
DEFINE = re.compile(r"^-\s*#\s*define\s+([A-Za-z_]\w*)")


def git(*a):
    return subprocess.run(["git", "-C", K, *a], capture_output=True, text=True, check=True).stdout


def main():
    commits = git("log", "--no-merges", "--since=2022-06-01", "-E", "--grep=^Fixes:", "--format=%H",
                  "HEAD", "--", "arch/loongarch").split()
    stats = {"fixes_touching_loongarch": len(commits), "not_loongarch_only": 0, "build_or_doc_only": 0,
             "no_cross_name": 0, "candidates": 0}
    out = []
    for c in commits:
        files = [f for f in git("show", "--name-only", "--format=", c).split("\n") if f]
        if not all(OWN.search(f) for f in files):
            stats["not_loongarch_only"] += 1
            continue
        if all(EXCL.search(f) for f in files):
            stats["build_or_doc_only"] += 1
            continue
        diff = git("diff", "-U0", f"{c}^", c, "--", *[f for f in files if not EXCL.search(f)])
        names = set()
        for line in diff.splitlines():
            if line.startswith("@@"):
                ctx = line.split("@@", 2)[-1]
                m = FUNC.findall(ctx)
                if m:
                    names.add(m[-1] if m[-1] not in ("if", "for", "while", "switch", "sizeof") else m[0])
            m = DEFINE.match(line)
            if m:
                names.add(m.group(1))
        hits = {}
        for n in sorted(names):
            if len(n) < 3:
                continue
            r = subprocess.run(["git", "-C", K, "grep", "-w", "-l", n, f"{c}^", "--", "*.c", "*.h", ":!arch"],
                               capture_output=True, text=True)
            k = len([x for x in r.stdout.splitlines() if x])
            if k:
                hits[n] = k
        if not hits:
            stats["no_cross_name"] += 1
            continue
        stats["candidates"] += 1
        out.append({"commit": c[:12], "parent": git("rev-parse", "--short=12", f"{c}^").strip(),
                    "names_touched": len(names), "names_with_public_refs": len(hits),
                    "public_ref_files": sum(hits.values()),
                    "date": git("show", "-s", "--format=%cs", c).strip()})
    (HERE / "candidates.json").write_text(json.dumps({"rules": "criteria.md 二", "stats": stats,
                                                      "candidates": out}, indent=1))
    print(json.dumps(stats))
    years = {}
    for x in out:
        years[x["date"][:4]] = years.get(x["date"][:4], 0) + 1
    print("by year", years)


if __name__ == "__main__":
    main()
