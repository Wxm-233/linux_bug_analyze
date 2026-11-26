"""covgap criteria 二 R1-R3 (report only): layering change, the two round-3 gaps, row-by-row comparison with round 3. WSL.

    python3 compare.py      -> here compare.json, r1_sample.json, r3_sample_new.json
"""
import gzip
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
W = Path("/root/work/covgap")
WOLD = Path("/root/work/bres")
T3 = CT / "task3_20261125"
NEWL = "公共层（体内架构配置）"


def k(r):
    return (r["engine"], r["file"], r["line"], r["func"]) + ((r["sig"],) if r["engine"] != "ORD" else ())


def main():
    res = {}
    E = json.load(gzip.open(W / "funcs.json.gz", "rt"))
    Eold = json.load(gzip.open(WOLD / "funcs.json.gz", "rt"))
    # R1: every 体内架构配置 label would have been A1 under the round-2 rule (same builds)
    moved = [e for e in E if e["label"] == NEWL]
    funcs = sorted({(e["file"], e["name"], e["start"]) for e in moved if e["kind"] == "func"})
    res["R1"] = {"entries": len(moved), "funcs": len(funcs),
                 "by_dir": dict(Counter(f.split("/")[0] + ("/" + f.split("/")[1] if f.startswith("include/") else "") for f, _, _ in funcs).most_common(12)),
                 "labels_new": dict(Counter(e["label"] for e in E)), "labels_round2": dict(Counter(e["label"] for e in Eold))}
    rnd = random.Random(20261125)
    smp = rnd.sample(funcs, min(10, len(funcs)))
    byk = defaultdict(list)
    for e in moved:
        byk[(e["file"], e["name"], e["start"])].append(e)
    json.dump([{"file": f, "func": n, "start": s, "end": byk[(f, n, s)][0]["end"],
                "builds": sorted({b for e in byk[(f, n, s)] for b in e["builds"]}),
                "diffs": byk[(f, n, s)][0]["diffs"]} for f, n, s in smp],
              open(HERE / "r1_sample.json", "w"), ensure_ascii=False, indent=1)
    print("R1", res["R1"]["entries"], "entries", res["R1"]["funcs"], "funcs", res["R1"]["by_dir"])

    # round-2 vs new compiled sets and labels (for the reasons below)
    def index(EE):
        lab, comp = defaultdict(set), defaultdict(set)
        for e in EE:
            lab[(e["file"], e["name"])].add(e["label"])
            comp[(e["file"], e["name"])] |= set(e["builds"])
        return lab, comp
    lab_n, comp_n = index(E)
    lab_o, comp_o = index(Eold)
    files_o = {e["file"] for e in Eold if e["builds"]}

    old = json.load(open(T3 / "out" / "cands.json", encoding="utf-8"))
    new = json.load(open(HERE / "t3" / "out" / "cands.json", encoding="utf-8"))
    oldk, newk = {k(r): r for r in old}, {k(r): r for r in new}
    p1v = {tuple(x["key"]): x for x in json.load(gzip.open(HERE / "t3" / "out" / "p1_verdicts.json.gz", "rt"))}

    # R2: round-3 P1 old-only rows (vs the df table), by round-3 reason class
    r3res = json.load(open(T3 / "result.json", encoding="utf-8"))
    gap = r3res["G3"]["P1"]["old_only"]
    rows = []
    for e, f, line, fn, sig in gap:
        kk = (e, f, line, fn, sig)
        A = sig.split("|")[0]
        v = p1v.get((f, fn, line, A))
        rows.append({"row": f"{f}:{line} {fn} {sig}", "back": kk in newk,
                     "now": "候选" if kk in newk else (f"有任务，判定为{v['verdict']}（{v['why']}）" if v else "没有边界记录"),
                     "F_label_now": sorted(lab_n.get((f, fn), ())), "F_builds_now": sorted(comp_n.get((f, fn), ()))})
    res["R2"] = {"n": len(rows), "back": sum(r["back"] for r in rows), "rows": rows}
    for r in rows:
        print("R2", "BACK" if r["back"] else "----", r["row"], "|", r["now"], r["F_label_now"], r["F_builds_now"])

    # R3: row-by-row vs round 3
    cmp_ = {}
    for eng in ("P1", "ORD", "EC"):
        o = {x for x in oldk if x[0] == eng}
        n = {x for x in newk if x[0] == eng}
        gone = []
        for x in sorted(o - n):
            r = oldk[x]
            f, fn = r["file"], r["func"]
            if eng == "P1":
                v = p1v.get((f, fn, r["line"], r["sig"].split("|")[0]))
                why = f"有任务，判定为{v['verdict']}（{v['why']}）" if v else "没有边界记录"
            else:
                why = "本轮没有这一行"
            why += f"；F 标签 {sorted(lab_o.get((f, fn), ()))}→{sorted(lab_n.get((f, fn), ()))}；构建 {sorted(comp_o.get((f, fn), ()))}→{sorted(comp_n.get((f, fn), ()))}"
            gone.append({"row": f'{f}:{r["line"]} {fn} {r["sig"][:80]}', "why": why})
        src = Counter()
        added = []
        for x in sorted(n - o):
            r = newk[x]
            f, fn = r["file"], r["func"]
            if NEWL in lab_n.get((f, fn), ()) and NEWL not in lab_o.get((f, fn), ()):
                s = "体内架构配置的函数"
            elif f not in files_o:
                s = "新编入的文件"
            elif not comp_o.get((f, fn)) and comp_n.get((f, fn)):
                s = "新开的配置（函数原来没编入）"
            else:
                s = "其他"
            src[s] += 1
            added.append(dict(r, _source=s))
        cmp_[eng] = {"round3": len(o), "now": len(n), "both": len(o & n), "gone": gone, "added_by_source": dict(src),
                     "added": [{"row": f'{a["file"]}:{a["line"]} {a["func"]} {a["sig"][:80]}', "source": a["_source"]} for a in added]}
        print("R3", eng, "round3", len(o), "now", len(n), "both", len(o & n), "gone", len(gone), "added", dict(src))
        for g in gone:
            print("   gone", g["row"], "|", g["why"])
        if eng in ("P1", "ORD"):
            cmp_[eng]["_sample"] = rnd.sample(added, min(10, len(added)))
    json.dump({e: v.pop("_sample") for e, v in cmp_.items() if "_sample" in v}, open(HERE / "r3_sample_new.json", "w"),
              ensure_ascii=False, indent=1)
    res["R3"] = cmp_
    json.dump(res, open(HERE / "compare.json", "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
