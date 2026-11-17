"""contract criteria 三.2: mine on each fix's parent, hit = deviation inside the fix's old hunk range. WSL.

    python3 evaluate.py      -> samples.json, samples.txt
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import contract as K  # noqa: E402

CT = HERE.parent
P1_BASE = {"26e7888a0c89", "43e7f189769c", "bd1f2b2ace84", "65529295607f"}


def hunks(commit, path):
    out, cur = [], None
    for line in K.C.git("show", "-U0", "--format=", commit, "--", path).split("\n"):
        m = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
        if m:
            cur = {"old": [int(m.group(1)), int(m.group(2) or 1)], "plus": []}
            out.append(cur)
        elif cur is not None and line.startswith("+") and not line.startswith("+++"):
            cur["plus"].append(line[1:])
    return out


def missing_name(item):
    m = item["missing"]
    if item["kind"] == "K1":
        return re.match(r"!?(\w+)\(", m).group(1)
    if item["kind"] == "K3":
        return m.split(" after ")[0]
    return None


def main():
    adj = json.loads((CT / "depmine_20261115/adjudication.json").read_text(encoding="utf-8"))
    samples = [r for r in adj["rows"] if r["final"] == "是"]
    iface = K.ifaces()
    rows, L = [], []
    for s in samples:
        c = s["commit"]
        files = [p for p in K.C.git("show", "--name-only", "--format=", c).split("\n") if p]
        common = [p for p in files if p.endswith((".c", ".h")) and not p.startswith(("arch/", "drivers/", "tools/"))]
        if not common:
            rows.append({"commit": c, "pattern": s["pattern"], "in_scope": False, "files": files})
            L.append(f"{c} {s['pattern']} 不在检查范围（只改 {sorted({p.split('/')[0] + '/' + p.split('/')[1] for p in files if '/' in p})}）")
            continue
        extra = tuple(sorted({p.rsplit("/", 1)[0] + "/" for p in common if p.endswith(".c") and not K.in_scope(p)}))
        res = K.mine_tree(f"{c}^", extra, iface)
        hit, strong, found = False, False, []
        for p in common:
            for h in hunks(c, p):
                lo, n = h["old"]
                hi = lo + max(n, 1) - 1
                plus = "\n".join(h["plus"])
                for d in res["deviations"]:
                    if d["file"] != p or not (lo - 3 <= d["line"] <= hi + 3):
                        continue
                    hit = True
                    st = False
                    for it in d["items"]:
                        name = missing_name(it)
                        if name and re.search(rf"\b{re.escape(name)}\s*\(", plus):
                            st = True
                        if it["kind"] == "K2" and re.search(rf"\b(if|while)\b.*\b{re.escape(d['A'])}\b|\b{re.escape(d['A'])}\b.*(&&|\|\||\?)", plus):
                            st = True
                    strong |= st
                    found.append({"file": p, "line": d["line"], "func": d["func"], "A": d["A"], "items": d["items"], "strong": st})
        rows.append({"commit": c, "pattern": s["pattern"], "in_scope": True, "hit": hit, "strong": strong, "p1_baseline": c in P1_BASE,
                     "contracts": len(res["contracts"]), "deviations": len(res["deviations"]), "found": found, "extra": list(extra)})
        L.append(f"{c} {s['pattern']} hit={hit} strong={strong} p1={c in P1_BASE} contracts={len(res['contracts'])} devs={len(res['deviations'])} "
                 + "; ".join(f"{x['func']}:{x['line']} {x['A']} {[i['missing'] for i in x['items']]}" for x in found[:4]))
        print(L[-1], flush=True)
    ins = [r for r in rows if r["in_scope"]]
    summ = {"samples": len(rows), "in_scope": len(ins), "hit": sum(r["hit"] for r in ins), "strong": sum(r["strong"] for r in ins),
            "hit_or_p1": sum(r.get("hit", False) or r["commit"] in P1_BASE for r in rows), "p1_baseline": len(P1_BASE)}
    L.append(json.dumps(summ, ensure_ascii=False))
    (HERE / "samples.json").write_text(json.dumps({"summary": summ, "rows": rows}, indent=1, ensure_ascii=False), encoding="utf-8")
    (HERE / "samples.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(L[-1])


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    main()
