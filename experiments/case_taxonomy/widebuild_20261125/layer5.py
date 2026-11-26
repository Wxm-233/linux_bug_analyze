"""widebuild criteria 二.3 / 三: round-1 layering and boundary (layerbound_20261124, rules unchanged) on five builds, output in
/root/work/layerbound5. Only the build list, the build trees and the output directory are overridden. WSL.

    python3 layer5.py avail          -> W5/config_symbols.json, g1_config.json
    python3 layer5.py pp <build> [-j N]
    python3 layer5.py layer          -> W5/funcs.json.gz, edges.json.gz; here g1_funcs.json, g2.json, g3.json
    python3 layer5.py check          -> here g1_all.json (G1), g2_compare.json (G2), g3_cover.json (G3)
"""
import gzip
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "layerbound_20261124"))
sys.path.insert(0, str(HERE))
W1 = Path("/root/work/layerbound")
W5 = Path("/root/work/layerbound5")
BUILDS = ("riscv", "arm64", "x86_64", "arm", "powerpc")
OLD = ("riscv", "arm64", "x86_64")
PROF = {"riscv": "wide", "x86_64": "wide", "arm64": "widemte", "arm": "widearm", "powerpc": "wide"}
TREE = "/root/work/kbuild/trees/df2908090cda_{}_{}"


def avail():
    """same rule as layerbound avail.py: a symbol is arch-related if some (not all) of the allyesconfigs have it"""
    av = {}
    for a in BUILDS:
        s = set()
        # amendment 1.1: allyesconfig plus the real build's .config
        for p in (W5 / f"avail_{a}" / ".config", Path(TREE.format(a, PROF[a])) / "out" / ".config"):
            for l in p.read_text().splitlines():
                m = re.match(r"(?:# )?CONFIG_(\w+)(?:=| is not set)", l)
                if m:
                    s.add(m.group(1))
        av[a] = s
    allsym = set().union(*av.values())
    arch_rel = {x: sorted(a for a in BUILDS if x in av[a]) for x in allsym if sum(x in av[a] for a in BUILDS) < len(BUILDS)}
    common = sorted(x for x in allsym if x not in arch_rel)
    json.dump({"arch_related": arch_rel, "common": common}, open(W5 / "config_symbols.json", "w"))
    old = json.load(open(W1 / "config_symbols.json"))
    newly = sorted(set(arch_rel) - set(old["arch_related"]))
    print("symbols", len(allsym), "arch-related", len(arch_rel), "common", len(common), "newly arch-related vs 3 builds", len(newly))
    exp = {"RISCV_ISA_SVNAPOT": True, "ARM64_64K_PAGES": True, "HAVE_ARCH_TRANSPARENT_HUGEPAGE_PUD": True,
           "ARCH_SUPPORTS_PUD_PFNMAP": True, "TRANSPARENT_HUGEPAGE": False, "SWAP": False, "SMP": False, "MMU": False}
    res, ok = {}, 0
    for k, v in exp.items():
        got = k in arch_rel
        res[k] = {"expected_arch": v, "got_arch": got, "archs": arch_rel.get(k, "all" if k in allsym else "none")}
        ok += got == v
        print(f"  {k:40s} expected {'arch' if v else 'common'} got {'arch' if got else 'common'} {arch_rel.get(k, '')}")
    print("G1 config", ok, "/", len(exp))
    json.dump({"ok": ok, "n": len(exp), "rows": res, "newly_arch_related": len(newly), "newly_sample": newly[:200]},
              open(HERE / "g1_config.json", "w"), indent=1)


def pp(build, j):
    import pp as P
    P.W = W5
    P.SRC2 = TREE.format(build, PROF[build]) + "/src"
    P.main(build, j)


def layer():
    # implementation fix: layer_n.py = layerbound layer.py with the hard-coded build count 3 replaced by len(BUILDS) (layer_n.diff)
    import layer_n as Lm
    Lm.W, Lm.HERE, Lm.BUILDS = W5, HERE, BUILDS
    Lm.main()


def check():
    E5 = json.load(gzip.open(W5 / "funcs.json.gz", "rt"))
    E1 = json.load(gzip.open(W1 / "funcs.json.gz", "rt"))
    ed5 = json.load(gzip.open(W5 / "edges.json.gz", "rt"))
    ed1 = json.load(gzip.open(W1 / "edges.json.gz", "rt"))
    # G1: round-1 cases (amendment-2 reading: over compiled definitions) + six new ones
    g1old = json.load(open(CT / "layerbound_20261124" / "g1_funcs.json", encoding="utf-8"))
    rows, ok = [], 0
    for it in g1old:
        defs = [e for e in E5 if e["file"] == it["file"] and e["name"] == it["name"] and e["kind"] == "func" and e["builds"]]
        got = [e["label"] for e in defs]
        good = bool(got) and all(x in it["want"] for x in got)
        ok += good
        rows.append({"case": f'{it["file"]} {it["name"]}', "want": it["want"], "got": got, "ok": good})
    ARCHL = ("架构层A0", "架构层A1")

    def defs_of(f, pat):
        return [e for e in E5 if e["file"] == f and re.fullmatch(pat, e["name"])]
    new = [("arch/powerpc/include/asm/hugetlb.h", "hugepages_supported", lambda ds: ds and all(d["label"] in ARCHL for d in ds)),
           ("arch/arm/include/asm/pgtable-3level.h", "pmd_mkinvalid", lambda ds: ds and all(d["label"] in ARCHL for d in ds)),
           ("arch/arm/include/asm/pgtable.h", r"__swp_\w+|pte_swp_\w+", lambda ds: ds and all(d["label"] in ARCHL for d in ds)),
           ("mm/zswap.c", "zswap_decompress", lambda ds: ds and all(set(d["builds"]) == set(BUILDS) for d in ds)),
           ("mm/kasan/hw_tags.c", "__kasan_unpoison_vmalloc", lambda ds: ds and all(d["builds"] == ["arm64"] for d in ds)),
           ("include/linux/highmem-internal.h", r"kmap_local_page",                # amendment 1.2: file name corrected
            lambda ds: any("arm" in d["builds"] for d in ds))]
    for f, pat, pred in new:
        ds = defs_of(f, pat)
        good = bool(pred(ds))
        ok += good
        rows.append({"case": f"{f} {pat}", "got": [(d["name"], d["label"], d["builds"]) for d in ds][:6], "ok": good})
    for r in rows:
        print("G1", "OK " if r["ok"] else "BAD", r["case"], r["got"][:3])
    print("G1", ok, "/", len(rows))
    json.dump({"ok": ok, "n": len(rows), "rows": rows}, open(HERE / "g1_all.json", "w"), ensure_ascii=False, indent=1)
    # G2: labels on the three old builds, old vs new
    k = lambda e: (e["file"], e["name"], e["start"], e["kind"])  # noqa: E731
    m1 = {k(e): e for e in E1}
    m5 = {k(e): e for e in E5}
    cfg1 = set(json.load(open(W1 / "config_symbols.json"))["arch_related"])
    cfg5 = set(json.load(open(W5 / "config_symbols.json"))["arch_related"])
    newly = cfg5 - cfg1
    ch, reasons, ex = Counter(), Counter(), defaultdict(list)
    for key, e1 in m1.items():
        e5 = m5.get(key)
        if e5 is None:
            ch["gone"] += 1
            continue
        b1, b5 = set(e1["builds"]), set(e5["builds"]) & set(OLD)
        if e1["label"] == e5["label"]:
            ch["same"] += 1
            continue
        ch["changed"] += 1
        if b1 != b5:
            r = "配置档变化（原三构建里的编入情况变了）"
        elif set(map(str, e5["diffs"])) != set(map(str, e1["diffs"])) and \
                any("arch" in str(d) for d in e5["diffs"]) and not any("arch" in str(d) for d in e1["diffs"]):
            r = "差异归因变为架构相关（新增架构）"
        elif set(e5["builds"]) - set(OLD):
            r = "新架构编入后差异来源变化"
        else:
            r = "其他"
        reasons[r] += 1
        if len(ex[r]) < 15:
            ex[r].append({"key": list(key), "old": e1["label"], "new": e5["label"], "old_builds": sorted(b1),
                          "new_builds": e5["builds"], "old_diffs": e1["diffs"][:3], "new_diffs": e5["diffs"][:3]})
    print("G2 labels", dict(ch), dict(reasons))
    # known-bug boundary edges
    def callees(E, ed, f, n):
        ids = {i for i, e in enumerate(E) if e["file"] == f and e["name"] == n}
        out = defaultdict(set)
        for kind in ("direct", "macro"):
            for a, b_, bld in ed[kind]:
                if a in ids:
                    out[E[b_]["name"]].add(bld)
        return out
    known = [("fs/proc/task_mmu.c", "smaps_pmd_entry", "pmd_young"), ("mm/memory.c", "insert_page_into_pte_locked", "pte_pfn"),
             ("mm/rmap.c", "folio_referenced_one", None), ("mm/vmscan.c", "lru_gen_look_around", None)]
    kres = []
    for f, n, want in known:
        c1, c5 = callees(E1, ed1, f, n), callees(E5, ed5, f, n)
        lost = {x: sorted(v) for x, v in c1.items() if not (v <= c5.get(x, set()))}
        kres.append({"func": f"{f} {n}", "want": want, "want_ok": want is None or want in c5, "old_callees": len(c1),
                     "new_callees": len(c5), "lost_on_old_builds": lost, "new_builds": sorted({b for v in c5.values() for b in v})})
        print("G2 known", n, "want", want, want is None or want in c5, "old", len(c1), "new", len(c5), "lost", list(lost)[:5])
    json.dump({"labels": dict(ch), "reasons": dict(reasons), "examples": ex, "newly_arch_related": len(newly), "known": kres,
               "edges": {"old_direct": len(ed1["direct"]), "new_direct": len(ed5["direct"]), "old_macro": len(ed1["macro"]),
                         "new_macro": len(ed5["macro"])}},
              open(HERE / "g2_compare.json", "w"), ensure_ascii=False, indent=1)
    # G3: L0-L2 of the 12 clean misses on the five builds
    est = json.load(open(CT / "recallprobe_20261125" / "estimate.json", encoding="utf-8"))
    t1 = defaultdict(set)
    for kind in ("direct", "macro"):
        for a, b_, bld in ed5[kind]:
            t1[a].add(bld)
    byn = defaultdict(list)
    for i, e in enumerate(E5):
        if e["kind"] == "func":
            byn[(e["file"], e["name"])].append(i)
    cover = []
    for s in est:
        best = None
        for p in s["per_func"]:
            ids = [i for i in byn.get((p["file"], p["func"]), []) if E5[i]["builds"]]
            inscope = (p["file"].startswith("mm/") and p["file"].endswith(".c")) or p["file"] == "fs/proc/task_mmu.c"
            if not ids:
                lv, why = 0, "未编入或不存在"
            elif not inscope:
                lv, why = 1, "超出范围"
            elif not any(t1.get(i) for i in ids):
                lv, why = 2, "不在边界上"
            else:
                lv, why = 3, "在边界上（第 ① 类）"
            info = {"func": f'{p["file"]} {p["func"]}', "level": lv, "why": why,
                    "builds": sorted({b for i in ids for b in E5[i]["builds"]}),
                    "boundary_builds": sorted({b for i in ids for b in t1.get(i, ())})}
            if best is None or lv > best["level"]:
                best = info
        cover.append({"commit": s["commit"], "info": s["info"], "before": f'L{min(s["best_level"], 3)} {s["best_why"]}', "now": best})
        print("G3", s["commit"], "before:", s["best_level"], s["best_why"], "| now:", best["level"], best["why"], best["func"],
              best["builds"], best["boundary_builds"])
    json.dump(cover, open(HERE / "g3_cover.json", "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "pp":
        pp(sys.argv[2], int(sys.argv[sys.argv.index("-j") + 1]) if "-j" in sys.argv else 10)
    else:
        {"avail": avail, "layer": layer, "check": check}[c]()
