"""Diagnose the over-broad 'used' exclusion (Windows Python). Prints file-level metadata only: never prints late-side ids or content.

    python used_diag.py
"""
import io
import json
import os
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parent.parent
tok = re.compile(r"\b[0-9a-f]{12}")
late = {c["commit"] for c in json.load(open(HERE / "sealed_late/late.json", encoding="utf-8"))}  # only the kept one
cands_late_all = None
# recompute late_total ids from mine output is not stored; rebuild from design/late split: late.json has kept only.
design = {c["commit"] for c in json.load(open(HERE / "design.json", encoding="utf-8"))}


def main():
    rows = []
    for root, dirs, files in os.walk(EXP):
        if "effsupply_20261120" in root or "__pycache__" in root:
            continue
        for fn in files:
            if not fn.endswith((".md", ".json", ".txt", ".log", ".py", ".sh", ".csv")):
                continue
            p = os.path.join(root, fn)
            try:
                s = io.open(p, encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            t = set(tok.findall(s))
            rows.append((os.path.relpath(p, EXP).replace("\\", "/"), len(t), t))
    json.dump([(r[0], r[1]) for r in rows], open(HERE / "used_diag_files.json", "w"), indent=0)
    big = Counter()
    for p, n, t in rows:
        big[n // 100 * 100 if n < 1000 else 1000] += 1
    print("files scanned:", len(rows), "| distinct-token histogram (bucket:files):", sorted(big.items()))
    hits = Counter()
    for p, n, t in rows:
        k = len(design & t)
        if k:
            hits[(p, n)] = k
    print("design-side: files mentioning >=1 design candidate, top 25 (file, distinct tokens in file, design hits):")
    for (p, n), k in hits.most_common(25):
        print(f"  {k:3d}  {n:7d}  {p}")


if __name__ == "__main__":
    main()
