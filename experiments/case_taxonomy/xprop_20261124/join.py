"""xprop criteria 一.B: attach boundary resources (xres3 sites) to the whole-version scan table (outfmt_20261124/tables). WSL.

    python3 join.py    -> tables/df2908090cda.{csv,json}, join.json (B gate + counts)
"""
import csv
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
W = Path("/root/work/xprop")
BUILDS = ("riscv", "arm64", "x86_64")


def in_scope(f):
    return (f.startswith("mm/") and f.endswith(".c")) or f == "fs/proc/task_mmu.c"


def desc(r):
    s = r["cat"]
    if r["role"].startswith("入参"):
        s += f"（{r['role']}，{r.get('origin', '')}）"
    elif r["role"] == "返回":
        s += f"（返回，{r.get('use', '')}）"
    elif r["role"] == "全局":
        s += f"（全局 {r.get('name', '')}{'，写' if r.get('write') else ''}）"
    elif r["role"] == "常量":
        s += f"（常量 {r.get('name', '')}）"
    return s


def main():
    sites = [s for b in BUILDS for s in json.load(gzip.open(W / f"sites_{b}.json.gz", "rt"))]
    at_line, in_func = defaultdict(list), defaultdict(list)
    for s in sites:
        at_line[(s["file"], s["line"], s["F"])].append(s)
        in_func[(s["file"], s["F"])].append(s)
    rows = list(csv.DictReader(open(CT / "outfmt_20261124" / "tables" / "df2908090cda.csv", encoding="utf-8-sig")))
    out, stat = [], Counter()
    per_engine = defaultdict(Counter)
    for r in rows:
        key = (r["文件"], int(r["行"] or 0), r["函数"])
        hit = at_line.get(key, [])
        if hit:
            edges = sorted({f'{s["F"]}→{s["G"]}' for s in hit})
            blds = sorted({s["build"] for s in hit})
            res = sorted({desc(x) for s in hit for x in s["resources"]})
            docs = sorted({x["doc"] for s in hit for x in s["resources"]})
            st = "同行"
        elif in_func.get((r["文件"], r["函数"])):
            fs = in_func[(r["文件"], r["函数"])]
            edges = sorted({f'{s["F"]}→{s["G"]}' for s in fs})[:8]
            blds = sorted({s["build"] for s in fs})
            res = sorted({x["cat"] for s in fs for x in s["resources"]})
            docs = sorted({x["doc"] for s in fs for x in s["resources"]})
            st = "同函数有边界资源"
        else:
            edges, blds, res, docs = [], [], [], []
            st = "不在边界上（本轮范围内）" if in_scope(r["文件"]) else "超出本轮范围"
        stat[st] += 1
        per_engine[r["引擎"]][st] += 1
        out.append(dict(r, 挂接=st, 边界边="；".join(edges), 构建="、".join(blds), 跨层资源="；".join(res)[:600], 文档分类="、".join(docs)))
    d = HERE / "tables"
    d.mkdir(exist_ok=True)
    cols = list(rows[0].keys()) + ["挂接", "边界边", "构建", "跨层资源", "文档分类"]
    with open(d / "df2908090cda.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(out)
    json.dump(out, open(d / "df2908090cda.json", "w"), ensure_ascii=False, indent=1)
    # B gate: confirmed-bug rows (scan3 numbering 78,79,113,114 = P1; 162,174,175,186 = XV)
    old = list(csv.DictReader(open(CT / "scan3_20261119" / "tables" / "df2908090cda.csv", encoding="utf-8-sig")))
    gate = []
    for n in (78, 79, 113, 114, 162, 174, 175, 186):
        o = old[n - 1]
        m = [x for x in out if (x["文件"], x["行"], x["函数"], x["特征"]) == (o["文件"], o["行"], o["函数"], o["特征"])][0]
        need_line = m["引擎"] == "P1"
        ok = (m["挂接"] == "同行" and "页表项" in m["跨层资源"]) if need_line else \
            (m["挂接"] in ("同行", "同函数有边界资源") and "页表项" in m["跨层资源"])
        gate.append({"scan3_no": n, "engine": m["引擎"], "where": f'{m["文件"]}:{m["行"]} {m["函数"]}', "挂接": m["挂接"],
                     "跨层资源": m["跨层资源"][:200], "ok": ok})
        print("B", n, m["引擎"], m["函数"], m["挂接"], "OK" if ok else "BAD")
    res = {"counts": dict(stat), "per_engine": {e: dict(c) for e, c in per_engine.items()}, "gate": gate,
           "gate_pass": all(g["ok"] for g in gate)}
    json.dump(res, open(HERE / "join.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: res[k] for k in ("counts", "per_engine", "gate_pass")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
