"""gstate2 criteria 二/三: tightened 'global state' check. WSL.

    python3 gstate2.py      -> g1.json (calibration), gstate2.json (all classes, candidates), here
"""
import gzip
import json
import pickle
import re
import subprocess
import zlib
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path("/root/repos/linux")
LB = Path("/root/work/layerbound")
XP = Path("/root/work/xprop")
BUILDS = ("riscv", "arm64", "x86_64")
INIT = re.compile(r"\b(__init|__ref|__meminit|__head|__init_or_module|__cpuinit)\b")
RO = re.compile(r"\b(__ro_after_init|__initdata|__initconst)\b")
REG = re.compile(r"\b(\w*initcall\w*|early_param|__setup|core_param)\s*\(")
PCPU_OPS = r"(?:this_cpu|__this_cpu|raw_cpu)_(?:write|add|sub|inc|dec|or|and|xchg|cmpxchg)\w*"
ATOM_OPS = r"(?:atomic|atomic_long|atomic64)_(?:set|inc|dec|add|sub|xchg|cmpxchg|try_cmpxchg|or|and|andnot|fetch_\w+)\w*"

L, BYFILE, SRC_CACHE, GREP = {}, defaultdict(list), {}, {}


def lines_of(b):
    with gzip.open(LB / f"lines_{b}.pkl.gz", "rb") as fh:
        d = pickle.load(fh)
    return {p: zlib.decompress(x) for p, x in d["files"].items() if not p.startswith("gen:")}


def src(f):
    if f not in SRC_CACHE:
        SRC_CACHE[f] = (SRC / f).read_text(errors="replace").split("\n")
    return SRC_CACHE[f]


def grep(name):
    if name not in GREP:
        g = subprocess.run(["git", "-C", str(SRC), "grep", "-n", "-w", name, "--", "*.c", "*.h"], capture_output=True, text=True).stdout
        out = []
        for l in g.splitlines():
            f, ln, txt = l.split(":", 2)
            out.append((f, int(ln), txt))
        GREP[name] = out
    return GREP[name]


def active(b, f, ln):
    bm = L[b].get(f)
    return bm is not None and ln < len(bm) and bm[ln] == 1


def enclosing(f, ln):
    for e in BYFILE.get(f, []):
        if e["start"] <= ln <= e["end"]:
            return e
    return None


def is_init_hdr(e):
    return bool(INIT.search(" ".join(src(e["file"])[max(0, e["start"] - 3):e["start"]])))


def write_re(X):
    x = re.escape(X)
    return re.compile(
        rf"(\b{x}\b(\s*(\.|->)\s*\w+|\s*\[[^\]]*\])*\s*(=(?!=)|\+=|-=|\*=|/=|%=|\|=|&=|\^=|<<=|>>=|\+\+|--))"
        rf"|((\+\+|--)\s*\b{x}\b)"
        rf"|(\bWRITE_ONCE\s*\(\s*&?\s*\(?\s*{x}\b)"
        rf"|(\b{PCPU_OPS}\s*\(\s*&?\s*{x}\b)"
        rf"|(\b(?:memset|memcpy|memmove)\s*\(\s*&?\s*{x}\b)"
        rf"|(\b(?:set_bit|clear_bit|__set_bit|__clear_bit|change_bit)\s*\([^,]*,\s*&?\s*{x}\b)"
        rf"|(\b{ATOM_OPS}\s*\(\s*&\s*{x}\b)")


@lru_cache(maxsize=None)
def boot_only(b, fname, depth=4):
    """criteria 二.3: is function fname (in build b) only ever executed at boot? returns (bool, why)"""
    hits = [(f, ln, t) for f, ln, t in grep(fname) if active(b, f, ln)]
    defs = [e for f, ln, t in hits for e in [enclosing(f, ln)] if e is not None and e["name"] == fname and e["start"] == ln]
    if any(is_init_hdr(e) for e in defs):
        return True, "__init"
    if any(REG.search(t) for f, ln, t in hits):
        return True, "initcall/param 登记"
    callers, addr = set(), False
    for f, ln, t in hits:
        e = enclosing(f, ln)
        if e is not None and e["name"] == fname and e["start"] == ln:
            continue
        if e is None and re.search(rf"^\s*(extern\s+)?[A-Za-z_][\w\s\*]*[\s\*]{re.escape(fname)}\s*\(", t) and \
                not re.match(r"\s*#", t):
            continue                              # a prototype / declaration is not a reference (implementation fix)
        if re.match(r"\s*\*|\s*/[/*]", t):
            continue                              # comment lines
        if re.search(rf"\b{re.escape(fname)}\s*\(", t):
            if e is not None:
                callers.add(e["name"])
            else:
                addr = True                       # used in a file-scope macro/initializer
        else:
            addr = True                           # referenced without a call: address taken / callback
    if not callers:
        return False, ("回调（地址被取用）" if addr else "调用者未知")
    if depth <= 1:
        return False, "调用链过深"
    for c in sorted(callers):
        ok, why = boot_only(b, c, depth - 1)
        if not ok:
            return False, f"经 {c}：{why}"
    return (not addr), ("所有调用者都在启动阶段" if not addr else "另有地址被取用")


def classify(X, b):
    hits = [(f, ln, t) for f, ln, t in grep(X) if active(b, f, ln)]
    if not hits:
        return {"class": "本构建没有这个变量"}
    decl = [(f, ln, t) for f, ln, t in hits if enclosing(f, ln) is None and not re.match(r"\s*#", t)]
    arch_decl = [(f, ln, t) for f, ln, t in decl if f.startswith("arch/")]
    wr = write_re(X)
    writes = []
    for f, ln, t in hits:
        e = enclosing(f, ln)
        if e is None or not wr.search(t):
            continue
        ok, why = boot_only(b, e["name"])
        writes.append({"at": f"{f}:{ln}", "func": e["name"], "boot": ok, "why": why, "text": t.strip()[:110]})
    ro = any(RO.search(t) for _, _, t in decl)
    const = any(re.search(r"\bconst\b", t) for _, _, t in decl)
    if not arch_decl:
        cls = "公共状态"
    elif const and not writes:
        cls = "常量"
    elif ro and all(w["boot"] for w in writes):
        cls = "启动时设定"
    elif not writes:
        cls = "没找到写入"
    elif all(w["boot"] for w in writes):
        cls = "启动时设定"
    else:
        cls = "运行时可变"
    return {"class": cls, "arch_decl": [f"{f}:{ln} {t.strip()[:90]}" for f, ln, t in arch_decl[:3]],
            "runtime_writes": [w for w in writes if not w["boot"]][:6], "boot_writes": [w for w in writes if w["boot"]][:3],
            "n_writes": len(writes)}


def main():
    for b in BUILDS:
        L[b] = lines_of(b)
    for e in json.load(gzip.open(LB / "funcs.json.gz", "rt")):
        if e["kind"] == "func":
            BYFILE[e["file"]].append(e)
    # G1 calibration
    cal = [("tlb_single_page_flush_ceiling", "x86_64", "运行时可变"), ("cpu_tlbstate", "x86_64", "运行时可变"),
           ("pgtable_l4_enabled", "riscv", "启动时设定"), ("page_offset_base", "x86_64", "启动时设定"),
           ("memstart_addr", "arm64", "启动时设定")]
    g1 = []
    for X, b, want in cal:
        r = classify(X, b)
        g1.append(dict(r, X=X, build=b, want=want, ok=r["class"] == want))
        print("G1", "OK " if r["class"] == want else "BAD", b, X, r["class"], [w["at"] + " " + w["why"] for w in r.get("runtime_writes", [])][:2])
    print("G1", sum(x["ok"] for x in g1), "/", len(g1))
    json.dump(g1, open(HERE / "g1.json", "w"), ensure_ascii=False, indent=1)
    # resources from round 3
    reads = defaultdict(lambda: defaultdict(set))
    for b in BUILDS:
        for s in json.load(gzip.open(XP / f"sites_{b}.json.gz", "rt")):
            for r in s["resources"]:
                if r["role"] == "全局":
                    reads[r["name"]][b].add(f'{s["G"]}（{s["G_file"]}）')
    out = []
    for X in sorted(reads):
        for b in BUILDS:
            if not reads[X].get(b):
                continue
            r = classify(X, b)
            out.append(dict(r, X=X, build=b, read_by=sorted(reads[X][b])))
    cand = [o for o in out if o["class"] == "运行时可变"]
    old = json.load(open(HERE.parent / "xprop_20261124" / "gstate.json", encoding="utf-8"))["candidates"]
    old_now = [{"X": o["X"], "build": o["build"], "now": next((x["class"] for x in out if x["X"] == o["X"] and x["build"] == o["build"]), "?")}
               for o in old]
    only = defaultdict(set)
    for o in out:
        if o["class"] not in ("公共状态", "本构建没有这个变量"):
            only[o["X"]].add(o["build"])
    res = {"by_class": dict(Counter(o["class"] for o in out)), "candidates": cand, "round3_candidates_now": old_now,
           "arch_state_only_some": {x: sorted(v) for x, v in only.items() if len(v) < 3}, "all": out}
    json.dump(res, open(HERE / "gstate2.json", "w"), ensure_ascii=False, indent=1)
    print("by_class", res["by_class"])
    print("round3 candidates now:", [(x["build"], x["X"], x["now"]) for x in old_now])
    for c in cand:
        print("CAND", c["build"], c["X"], c["read_by"][:2], [w["at"] + " " + w["func"] + " " + w["why"] for w in c["runtime_writes"][:3]])


if __name__ == "__main__":
    main()
