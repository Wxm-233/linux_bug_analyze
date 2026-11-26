"""xprop criteria 一.C: first 'global state' property check. For each arch global X read/written by a boundary arch function G (xres3
sites, role 全局), find X's declaration and all writes in the code compiled into that build (round-1 line maps), classify:
常量 / 启动时设定 / 运行时可变 / 没找到写入. Candidates = 运行时可变. Also the capability matrix (criteria 附). WSL.

    python3 gstate.py   -> gstate.json, capability.json
"""
import gzip
import json
import pickle
import re
import subprocess
import zlib
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path("/root/repos/linux")
LB = Path("/root/work/layerbound")
W = Path("/root/work/xprop")
BUILDS = ("riscv", "arm64", "x86_64")
INIT = re.compile(r"\b(__init|__ref|__meminit|__head|__init_or_module|__cpuinit|__initdata)\b")
RO = re.compile(r"\b(__ro_after_init|const|__initdata|__initconst)\b")


def lines_of(b):
    with gzip.open(LB / f"lines_{b}.pkl.gz", "rb") as fh:
        d = pickle.load(fh)
    return {p: zlib.decompress(x) for p, x in d["files"].items() if not p.startswith("gen:")}


def main():
    sites = {b: json.load(gzip.open(W / f"sites_{b}.json.gz", "rt")) for b in BUILDS}
    funcs = json.load(gzip.open(LB / "funcs.json.gz", "rt"))
    byfile = defaultdict(list)
    for e in funcs:
        if e["kind"] == "func":
            byfile[e["file"]].append(e)
    reads = defaultdict(lambda: defaultdict(set))                       # X -> build -> {G}
    for b in BUILDS:
        for s in sites[b]:
            for r in s["resources"]:
                if r["role"] == "全局":
                    reads[r["name"]][b].add(f'{s["G"]}（{s["G_file"]}）')
    L = {b: lines_of(b) for b in BUILDS}
    src_cache = {}

    def src(f):
        if f not in src_cache:
            src_cache[f] = (SRC / f).read_text(errors="replace").split("\n")
        return src_cache[f]

    def enclosing(f, ln):
        for e in byfile.get(f, []):
            if e["start"] <= ln <= e["end"]:
                return e
        return None

    out = []
    for X, per in sorted(reads.items()):
        g = subprocess.run(["git", "-C", str(SRC), "grep", "-n", "-w", X, "--", "*.c", "*.h"], capture_output=True, text=True).stdout
        hits = []
        for l in g.splitlines():
            f, ln, txt = l.split(":", 2)
            hits.append((f, int(ln), txt))
        wpat = re.compile(r"(\b" + re.escape(X) + r"\b(\s*(\.|->)\s*\w+|\s*\[[^\]]*\])*\s*(=(?!=)|\+=|-=|\|=|&=|\^=|<<=|>>=|\+\+|--))|"
                          r"((\+\+|--)\s*\b" + re.escape(X) + r"\b)|(&\s*" + re.escape(X) + r"\b)")
        for b in BUILDS:
            act = []
            for f, ln, txt in hits:
                bm = L[b].get(f)
                if bm is not None and ln < len(bm) and bm[ln]:
                    act.append((f, ln, txt))
            decl = [(f, ln, txt) for f, ln, txt in act if enclosing(f, ln) is None and re.search(r"\b" + re.escape(X) + r"\b", txt)]
            writes = []
            for f, ln, txt in act:
                e = enclosing(f, ln)
                if e is None or not wpat.search(txt):
                    continue
                hdr = " ".join(src(f)[max(0, e["start"] - 3):e["start"]])
                writes.append({"at": f"{f}:{ln}", "func": e["name"], "init": bool(INIT.search(hdr)), "text": txt.strip()[:120]})
            ro = any(RO.search(t) for _, _, t in decl)
            if not act:
                cls = "本构建没有这个变量"
            elif ro and not any(not w["init"] for w in writes):
                cls = "常量" if any(re.search(r"\bconst\b", t) for _, _, t in decl) and not writes else "启动时设定"
            elif not writes:
                cls = "没找到写入"
            elif all(w["init"] for w in writes):
                cls = "启动时设定"
            else:
                cls = "运行时可变"
            out.append({"X": X, "build": b, "read_by": sorted(per.get(b, ())), "class": cls,
                        "decl": [f"{f}:{ln} {t.strip()[:100]}" for f, ln, t in decl[:4]],
                        "runtime_writes": [w for w in writes if not w["init"]][:6], "n_writes": len(writes)})
    cand = [o for o in out if o["class"] == "运行时可变" and o["read_by"]]
    summary = {"globals": len(reads), "by_class": dict(Counter(o["class"] for o in out if o["read_by"])), "candidates": len(cand)}
    # cross-arch view: X read by a boundary G in one build, while other builds have no such variable
    cross = []
    for X, per in reads.items():
        cl = {o["build"]: o["class"] for o in out if o["X"] == X}
        if len(per) < 3:
            cross.append({"X": X, "read_in": sorted(per), "class_by_build": cl})
    json.dump({"summary": summary, "candidates": cand, "all": out, "only_some_arches": cross}, open(HERE / "gstate.json", "w"),
              ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False))
    for c in cand:
        print("CAND", c["build"], c["X"], c["read_by"][:2], [w["at"] + " " + w["func"] for w in c["runtime_writes"][:3]])

    # capability matrix (criteria 附)
    cap = defaultdict(dict)
    for b in BUILDS:
        for s in sites[b]:
            for r in s["resources"]:
                if r["role"] == "返回" and r["cat"] == "能力判断":
                    cap[s["G"]][b] = r.get("impl", "?")
    diff = {g: v for g, v in cap.items() if len(set(v.values())) > 1 or len(v) < 3}
    json.dump({"matrix": cap, "differ_or_missing": diff}, open(HERE / "capability.json", "w"), ensure_ascii=False, indent=1)
    print("capability G", len(cap), "differ/missing", len(diff))
    for g, v in sorted(diff.items())[:40]:
        print("CAP", g, v)


if __name__ == "__main__":
    main()
