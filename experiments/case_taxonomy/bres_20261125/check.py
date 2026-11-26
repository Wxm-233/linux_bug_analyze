"""bres criteria 三 G3/G4: coverage funnel, mis-binding check, regression against round 2 (xres) and the known bugs, and the
stratified sample of 30. WSL.

    python3 check.py      -> result.json, sample.json
"""
import gzip
import os
import json
import pickle
import random
import re
import zlib
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
WB = Path("/root/work/bres")
XP = Path("/root/work/xprop")
BUILDS = ("riscv", "arm64", "x86_64", "arm", "powerpc")
ARCHDIR = {"riscv": "riscv", "arm64": "arm64", "x86_64": "x86", "arm": "arm", "powerpc": "powerpc"}


def lines_of(b):
    with gzip.open(WB / f"lines_{b}.pkl.gz", "rb") as fh:
        d = pickle.load(fh)
    return {p: zlib.decompress(x) for p, x in d["files"].items()}


def locs(bind):
    d = bind["def"]
    out = []
    for part in d.split("；"):
        m = re.search(r"（([^（）]+):(\d+)）", part) or re.match(r"\s*([^:（]+):(\d+)", part)
        if m:
            out.append((m.group(1), int(m.group(2))))
    return out


def main():
    res = {"funnel": {}, "misbind": {}, "by_dir": {}}
    stats = json.load(open(HERE / "run_stats.json", encoding="utf-8"))["builds"]
    allrecs = {}
    bad_samples = []
    other_arch = Counter()
    for b in BUILDS:
        R = json.load(gzip.open(WB / f"rec_{b}.json.gz", "rt"))
        allrecs[b] = R
        L = lines_of(b)
        st = stats[b]
        cats = Counter(x["cat"] for r in R for x in r.get("resources", []))
        res["funnel"][b] = {"units": st["units"], "failed": st["failed"], "failed_pct": round(100 * st["failed"] / max(1, st["units"]), 2),
                            "common_funcs": st.get("common_funcs"), "boundary_funcs": st.get("boundary_funcs"), "records": len(R),
                            "by_kind": dict(Counter(r["kind"] for r in R)), "resources_by_cat": dict(cats.most_common(14))}
        bad = Counter()
        for r in R:
            if r["kind"] == "常量" and r["bind"]["def"].startswith("配置项"):
                continue
            for f, ln in locs(r["bind"]):
                f = ("gen:" + os.path.normpath(f[4:])) if f.startswith("gen:") else os.path.normpath(f)   # amendment 1.2
                if f.startswith("gen:"):
                    if f.startswith("gen:arch/") and not f.startswith(f"gen:arch/{ARCHDIR[b]}/"):
                        bad["生成头文件属于别的架构"] += 1
                        bad_samples.append((b, r["F"]["name"], r["iface"], f))
                    continue
                bm = L.get(f)
                if bm is None:
                    bad["定义文件不属于该构建"] += 1
                    bad_samples.append((b, r["F"]["name"], r["iface"], f))
                elif not (ln < len(bm) and bm[ln] == 1):
                    bad["定义行在该构建里不生效"] += 1
                    bad_samples.append((b, r["F"]["name"], r["iface"], f"{f}:{ln}"))
                if f.startswith("arch/") and not f.startswith(f"arch/{ARCHDIR[b]}/") and bm is not None:
                    other_arch[b] += 1                                   # amendment 1.1: compiled by this build, reported only
        res["misbind"][b] = dict(bad)
        top = Counter()
        for r in R:
            top[r["F"]["file"].split("/")[0]] += 1
        res["by_dir"][b] = dict(top.most_common(15))
        print(b, json.dumps(res["funnel"][b], ensure_ascii=False)[:400], "misbind", dict(bad), flush=True)
    res["misbind_total"] = sum(sum(v.values()) for v in res["misbind"].values())
    res["misbind_samples"] = bad_samples[:40]
    res["bound_in_other_arch_dir_but_compiled"] = dict(other_arch)
    # G4: round-2 sites (old mglru builds, mm/ only)
    reg = {}
    Enew = json.load(gzip.open(WB / "funcs.json.gz", "rt"))
    labn = defaultdict(set)                                  # (file, name) -> new labels (any build)
    compn = defaultdict(set)                                 # (file, name) -> builds compiling it
    for e in Enew:
        labn[(e["file"], e["name"])].add(e["label"])
        compn[(e["file"], e["name"])] |= set(e["builds"])
    for b in ("riscv", "arm64", "x86_64"):
        old = json.load(gzip.open(XP / f"sites_{b}.json.gz", "rt"))
        new = {(r["F"]["file"], r["F"]["name"], r["line"], r["iface"]) for r in allrecs[b]}
        newF = {(r["F"]["file"], r["F"]["name"]) for r in allrecs[b]}
        miss = Counter()
        ex = defaultdict(list)
        n = 0
        for s in old:
            if s["G_kind"] not in ("func", "macro"):
                continue
            n += 1
            if (s["file"], s["F"], s["line"], s["G"]) in new:
                continue
            gl = labn.get((s["G_file"], s["G"]), set())
            fl = labn.get((s["file"], s["F"]), set())
            if b not in compn.get((s["file"], s["F"]), set()):
                why = "F 在新构建里没编入（配置档不同）"
            elif fl and not (fl & {"公共层", "公共层-配置差异", "公共层（部分架构）"}):
                why = "F 在相对分层下是架构层"
            elif gl and not (gl & {"架构层A0", "架构层A1"}) and not s["G_file"].startswith("arch/"):
                why = "被调方在相对分层下回到公共层（只受功能配置控制）"
            elif b not in compn.get((s["G_file"], s["G"]), set()) and not s["G_file"].startswith("arch/"):
                why = "被调方在新构建里没编入"
            else:
                why = ("F 在新记录里没有任何边界（其他）" if (s["file"], s["F"]) not in newF else "F 在，但这一行这个接口不在（其他）")
            miss[why] += 1
            if len(ex[why]) < 12:
                ex[why].append(f'{s["file"]}:{s["line"]} {s["F"]} -> {s["G"]}（{s["G_label"]}，{s["G_kind"]}）')
        reg[b] = {"old_sites": n, "kept": n - sum(miss.values()), "missing": dict(miss), "examples": ex}
        print("G4", b, n, "kept", n - sum(miss.values()), dict(miss), flush=True)
    res["G4_xres"] = reg
    known = [("smaps", "fs/proc/task_mmu.c", "smaps_pmd_entry", r"pmd_young|pmd_dirty|pmd_present"),
             ("DAX", "mm/memory.c", "insert_page_into_pte_locked", r"pte_pfn"),
             ("回收", "mm/rmap.c", "folio_referenced_one", r".*young.*|ptep_clear_flush_young.*|pmdp_clear_flush_young.*"),
             ("MGLRU", "mm/vmscan.c", "lru_gen_look_around", r".*young.*|pte_.*"),
             ("shmem", "mm/shmem.c", "shmem_allowable_huge_orders", r".*"),
             ("riscv pud_leaf", "mm/mprotect.c", "change_pud_range", r"pud_leaf|pud_trans_huge"),
             ("riscv pud_leaf", "mm/memory.c", "zap_pud_range", r"pud_trans_huge|pud_leaf"),
             ("arm LPAE 交换项", "mm/migrate.c", r"remove_migration_pte|try_to_migrate_one|.*", r"pte_to_swp_entry|__swp_entry|swp_entry_to_pte|.*swp.*"),
             ("arm LPAE pmd_mkinvalid", "mm/huge_memory.c", r".*", r"pmdp_invalidate|pmd_mkinvalid")]
    kres = []
    for tag, f, fn, pat in known:
        hit = [(b, r["F"]["name"], r["line"], r["kind"], r["iface"], r["bind"]["def"]) for b in BUILDS for r in allrecs[b]
               if r["F"]["file"] == f and re.fullmatch(fn, r["F"]["name"]) and re.fullmatch(pat, r["iface"])]
        kres.append({"bug": tag, "file": f, "F": fn, "n": len(hit), "builds": sorted({h[0] for h in hit}), "sample": hit[:4]})
        print("G4 known", tag, f, fn, len(hit), sorted({h[0] for h in hit}), flush=True)
    res["G4_known"] = kres
    # sample of 30 (criteria 三 G3)
    rnd = random.Random(20261125)
    flat = [(b, r) for b in BUILDS for r in allrecs[b]]
    quota = {"调用": 15, "宏": 6, "常量": 4, "布局": 2, "包装一层": 3}
    pick = []
    for k, q in quota.items():
        pool = [x for x in flat if x[1]["kind"] == k]
        pick += rnd.sample(pool, min(q, len(pool)))
    while len(pick) < 30:
        pool = [x for x in flat if x[1]["kind"] == "调用" and x not in pick]
        pick.append(rnd.choice(pool))
    json.dump([dict(r, _build=b) for b, r in pick], open(HERE / "sample.json", "w"), ensure_ascii=False, indent=1)
    json.dump(res, open(HERE / "result.json", "w"), ensure_ascii=False, indent=1)
    print("misbind total", res["misbind_total"])


if __name__ == "__main__":
    main()
