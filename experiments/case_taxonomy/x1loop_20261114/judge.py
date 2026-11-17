"""Verdicts per run (x1loop criteria 四) -> judge.json, judge.txt"""
import json
import re
from pathlib import Path
HERE = Path(__file__).resolve().parent
rows, out = [], []
for f in sorted((HERE / "runs").glob("*.log")):
    m = re.match(r"(\w+?)_(pre|fix)_(plain|mte)\.run(\d)\.log", f.name)
    arch, ver, mode, i = m.groups()
    text = re.sub(r"\[\s*\d+\.\d+\][^\n]*\n", "", f.read_text(errors="replace"))  # kernel messages interleaved in a line
    js = [json.loads(l) for l in text.splitlines() if l.startswith("{")]
    setup = next((j for j in js if j.get("setup")), {})
    rounds = [j for j in js if "round" in j]
    alloc = sum(r["zero_alloc_delta"] for r in rounds)
    nz_rounds = [r for r in rounds if r["nonzero"] > 0]
    syscalls_ok = all(r["mmap_ok"] == 1 and r["madvise"] == 0 and r["munmap"] == 0 and r["dirty_ok"] == 1
                      and r["dirty_munmap"] == 0 and r["drop_caches"] == 0 for r in rounds)
    valid = alloc > 0 and len(rounds) == 8  # amendment 2: 8 rounds
    row = {"arch": arch, "version": ver, "mode": mode, "run": int(i), "rounds": len(rounds), "thp": setup.get("thp_enabled"),
           "use_zero_page": setup.get("use_zero_page"), "zero_alloc_total": alloc, "valid": valid,
           "violated": bool(nz_rounds), "violated_rounds": len(nz_rounds),
           "max_nonzero": max((r["nonzero"] for r in rounds), default=0),
           "first_vals": sorted({r["first_val"] for r in nz_rounds}), "syscalls_all_ok": syscalls_ok}
    rows.append(row)
(HERE / "judge.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
grp = {}
for r in rows:
    grp.setdefault((r["version"], r["arch"], r["mode"]), []).append(r)
for (v, a, m), rs in sorted(grp.items()):
    out.append(f"{v:3} {a:6} {m:5} valid {sum(r['valid'] for r in rs)}/3  violated {sum(r['violated'] for r in rs)}/3  "
               f"violated_rounds {[r['violated_rounds'] for r in rs]}  max_nonzero {[r['max_nonzero'] for r in rs]}  "
               f"first_vals {sorted({x for r in rs for x in r['first_vals']})}  zero_alloc {[r['zero_alloc_total'] for r in rs]}  "
               f"syscalls_ok {all(r['syscalls_all_ok'] for r in rs)}  thp '{rs[0]['thp']}' use_zero_page '{rs[0]['use_zero_page']}'")
(HERE / "judge.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))
