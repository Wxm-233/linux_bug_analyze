"""amendment 1: calibration set = round-2 day-1 bound + round-1 day-1 bound + evcard-reviewed WT (covered). WSL.
    python3 calib.py build   -> calib_set.json ; then rng.py run calib_set.json calib_rng.json
"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(HERE))
import bind2 as B2
B = B2.B
rows = {r["id"]: r for r in B.unreviewed()}
items = json.loads((CT / "evcard_20261121/review/items.json").read_text(encoding="utf-8"))
ids = [i["id"] for i in items if i["id"].startswith("WT:")]
r1 = [r["id"] for r in json.loads((CT / "wtrange_20261121/day1_bind.json").read_text(encoding="utf-8")) if r["status"] == "找到"]
d2 = [r["id"] for r in json.loads((HERE / "day1_bind.json").read_text(encoding="utf-8")) if r["status"] == "找到"] if (HERE / "day1_bind.json").exists() else []
out, seen = [], set()
for src, lst in (("round2_day1", d2), ("round1_day1", r1), ("evcard_reviewed", ids)):
    for i in lst:
        if i in seen or i not in rows:
            continue
        seen.add(i)
        x = B2.bind_one(rows[i])
        x["calib_source"] = src
        out.append(x)
        print(src, i, x["status"], [b for b, _ in x["units"]], flush=True)
(HERE / "calib_set.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
