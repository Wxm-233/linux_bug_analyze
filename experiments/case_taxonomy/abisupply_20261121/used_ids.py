"""criteria 四.4: 'used' ids = 12-hex tokens in experiments/ files with <= 1000 distinct tokens (effsupply amendment 2 convention).
Skips this directory and every directory/file whose path contains 'sealed' (those are compared separately, counts only). Windows Python.

    python used_ids.py  -> used_ids.json (sorted id list; nothing per-commit printed)
"""
import io
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parent.parent
SKIP = {"case_taxonomy/heldout_commit_20261117/pool.json", "case_taxonomy/depmine_20261115/candidates.json"}
tok = re.compile(r"\b[0-9a-f]{12}")
out, n_files, n_big = set(), 0, 0
for root, dirs, files in os.walk(EXP):
    if HERE.name in root or "__pycache__" in root or "sealed" in root:
        continue
    for fn in files:
        p = os.path.relpath(os.path.join(root, fn), EXP).replace("\\", "/")
        if p in SKIP or "sealed" in fn or not fn.endswith((".md", ".json", ".txt", ".log", ".py", ".sh", ".csv", ".jsonl")):
            continue
        try:
            t = set(tok.findall(io.open(os.path.join(root, fn), encoding="utf-8", errors="ignore").read()))
        except Exception:
            continue
        n_files += 1
        if len(t) > 1000:
            n_big += 1
            continue
        out |= t
json.dump(sorted(out), open(HERE / "used_ids.json", "w"))
print("files", n_files, "global lists skipped", n_big, "used ids", len(out))
