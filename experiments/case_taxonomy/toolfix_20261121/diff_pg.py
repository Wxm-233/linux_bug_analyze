"""toolfix criteria 四: compare the nine page-table configurations with pgassert_20261121/eval_*.json.
    python diff_pg.py -> diff_pg.json + summary (runs anywhere; reads JSON only)
"""
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "pgassert_20261121"
BUILDS = ["riscv64", "rv32_abi", "x86_64", "i386", "i386_allmod", "arm64", "arm64_16k", "arm64_64k", "arm64_pa48"]


def key(e):
    return (e.get("func"), e.get("line"), e.get("assert"))


def cst(e):
    return (e.get("constructed") or {}).get("status")


rows, summary = [], {}
for b in BUILDS:
    old = {key(e): e for e in json.loads((OLD / f"eval_{b}.json").read_text(encoding="utf-8"))}
    new = {key(e): e for e in json.loads((HERE / f"eval_{b}.json").read_text(encoding="utf-8"))}
    n = 0
    for k in sorted(set(old) | set(new), key=lambda k: (str(k[0]), k[1] or 0, str(k[2]))):
        o, f = old.get(k, {}), new.get(k, {})
        if o.get("status") != f.get("status") or cst(o) != cst(f):
            n += 1
            rows.append({"build": b, "func": k[0], "line": k[1], "assert": k[2], "old": o.get("status"), "fixed": f.get("status"),
                         "old_constructed": cst(o), "fixed_constructed": cst(f), "fixed_runtime": f.get("runtime"),
                         "fixed_notes": f.get("notes"), "fixed_why": f.get("why")})
    summary[b] = {"entries": len(new), "changed": n, "fixed_status": dict(Counter(e.get("status") for e in new.values()))}
(HERE / "diff_pg.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=1, ensure_ascii=False), encoding="utf-8")
for b, s in summary.items():
    print(b, s["entries"], "changed", s["changed"])
for r in rows:
    print(r["build"], r["line"], r["assert"], "|", r["old"], "->", r["fixed"], "|", r["old_constructed"], "->", r["fixed_constructed"])
