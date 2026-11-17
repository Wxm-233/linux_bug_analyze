"""restblind criteria 一、三.1: unreviewed reachable candidates -> review.txt, review.json. WSL."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "p1check_20261115"))
import p1check as C  # noqa: E402


def L(p):
    return json.loads((CT / p).read_text(encoding="utf-8"))


seen = set()
for x in L("p1check_20261115/o1_adjudication.json")["rows"]:
    f, l = x["loc"].rsplit(":", 1)
    seen.add((f, int(l)))
for x in L("contract_20261115/top30.json"):
    seen.add((x["file"], x["line"]))
for x in L("encrank_20261115/new_adjudication.json")["rows"]:
    f, l = x["loc"].rsplit(":", 1)
    seen.add((f, int(l)))
na = L("reach_20261115/new_adjudication.json")
for x in (na["rows"] if isinstance(na, dict) else na):
    f, l = x["loc"].rsplit(":", 1)
    for part in l.split("-"):
        seen.add((f, int(part)))
for x in L("reachf4_20261116/changes_judgement.json")["rows"]:
    f, l = x["loc"].rsplit(":", 1)
    seen.add((f, int(l)))
tab = L("encrank_20261115/table.json")["table"]
ranked = L("reachdead_20261116/head.json")["ranked"]
new = []
for i, r in enumerate(ranked, 1):
    if (r["file"], r["line"]) in seen:
        continue
    new.append({"k": len(new) + 1, "rank": i, "file": r["file"], "line": r["line"], "func": r["func"], "A": r["A"],
                "origin": r["origin"], "M": tab.get(r["A"], {}).get("M", []),
                "not_blind_for_claude": (r["file"], r["line"]) == ("mm/huge_memory.c", 1609)})
blobs = C.cat_files("df2908090cda", sorted({d["file"] for d in new}))
out = []
for d in new:
    src = blobs[d["file"]].split("\n")
    a, b = max(1, d["line"] - 30), min(len(src), d["line"] + 8)
    out += ["=" * 90,
            f"[{d['k']}] {d['file']}:{d['line']}  函数 {d['func']}  接口 {d['A']}  来源 {d['origin']}  "
            f"编码表：在 {', '.join(d['M']) or '（无）'} 上对某些非 present 项读错"]
    out += [f"{'>>' if i == d['line'] else '  '}{i:5d} {src[i - 1]}" for i in range(a, b + 1)]
(HERE / "review.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
(HERE / "review.json").write_text(json.dumps(new, indent=1, ensure_ascii=False), encoding="utf-8")
print("kept", len(ranked), "unreviewed", len(new))
for d in new:
    print(d["k"], d["rank"], d["file"], d["line"], d["func"], d["A"], d["M"])
