"""new top-30 entries not reviewed before (reach criteria 五.4) -> review_new.txt, new_review.json. WSL."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; CT = HERE.parent
sys.path.insert(0, str(CT / "p1check_20261115")); import p1check as C
h = json.loads((HERE / "head.json").read_text()); tab = json.loads((CT / "encrank_20261115/table.json").read_text())["table"]
seen = set()
for x in json.loads((CT / "p1check_20261115/o1_adjudication.json").read_text(encoding="utf-8"))["rows"]:
    f, l = x["loc"].rsplit(":", 1); seen.add((f, int(l)))
for x in json.loads((CT / "contract_20261115/top30.json").read_text(encoding="utf-8")): seen.add((x["file"], x["line"]))
for x in json.loads((CT / "encrank_20261115/new_adjudication.json").read_text(encoding="utf-8"))["rows"]:
    f, l = x["loc"].rsplit(":", 1); seen.add((f, int(l)))
top = h["ranked"][:30]
new, s2 = [], set()
for i, r in enumerate(top, 1):
    k = (r["file"], r["line"])
    if k in seen or k in s2: continue
    s2.add(k); new.append({**r, "rank": i, "M": tab.get(r["A"], {}).get("M", [])})
for i in (35, 36):  # extra, not counted (MGLRU look-around paths, same family as B-2)
    r = h["ranked"][i - 1]
    if (r["file"], r["line"]) not in seen: new.append({**r, "rank": i, "M": tab.get(r["A"], {}).get("M", []), "extra": True})
blobs = C.cat_files("df2908090cda", sorted({d["file"] for d in new}))
L = []
for k, d in enumerate(new, 1):
    src = blobs[d["file"]].split("\n"); a, b = max(1, d["line"] - 30), min(len(src), d["line"] + 8)
    L += ["=" * 90, f"[{k}] {d['file']}:{d['line']}  函数 {d['func']}  接口 {d['A']}  编码表：在 {', '.join(d['M'])} 上对某些非 present 项读错" + ("（附加，不计入）" if d.get("extra") else "")]
    L += [f"{'>>' if i == d['line'] else '  '}{i:5d} {src[i - 1]}" for i in range(a, b + 1)]
(HERE / "review_new.txt").write_text("\n".join(L) + "\n")
(HERE / "new_review.json").write_text(json.dumps(new, indent=1, ensure_ascii=False))
print("top30", len(top), "already reviewed", len(top) - len(new), "new", len(new))
for k, d in enumerate(new, 1): print(k, d["rank"], d["file"], d["line"], d["func"], d["A"])
