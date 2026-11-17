"""Score, rank and prune hint sites (rankprune criteria 三、四、5.1). Runs in WSL.

    python3 rank.py <group>...    -> ../gen/hints_<group>.json (pruned, generator format), ../ranking_<group>.json
    python3 rank.py --selftest
"""
import gzip
import json
import math
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from hints3 import run, trunc, is_addr  # noqa: E402

K, V, TOPSITES = 40, 6, 3
ARCHS = ("riscv", "arm64", "x86_64")
DRV = re.compile(r"(^|/)drivers/.*(riscv|sifive|-sbi)")
FIXC = {"A101": "2116988d5372", "A310": "61119394631f", "A171": "890ba5be6335", "A181": "1046791390af",
        "B467": "c625154993d0"}
FIXITEMS = {"A101": {"arch_get_mmap_end"}, "A171": {"TASK_SIZE_MAX"}, "A181": {"__put_user", "put_user"},
            "B467": None, "A310": "raw_nr"}
GEN = HERE.parent / "gen"
VT = json.loads((HERE.parents[1] / "twostage_dev_20261109/version_tables.json").read_text())
sys.path.insert(0, str(GEN))
import generate as G  # noqa: E402


def universe(group, entries):
    nrt = json.loads((GEN / "nr_tables.json").read_text())
    common = set.intersection(*[set(VT[k]) for k in G.KERNELS[group]])
    return {sc for sc in common if sc not in G.BLACK_EXACT and sc in entries and all(sc in nrt[a] for a in ARCHS)} \
        | {"raw_nr"}


def patch_names(group):
    d = json.load(gzip.open("/root/work/pgdev/patches_x86_arm64.json.gz", "rt"))
    cutoff = None
    if group != "CUR":
        cutoff = int(subprocess.run(["git", "-C", "/root/repos/linux", "log", "-1", "--format=%at", FIXC[group]],
                                    capture_output=True, text=True, check=True).stdout.strip())
    names = set()
    for c in d["commits"]:
        if cutoff is None or c["cdate"] < cutoff:
            names |= {h["func"] for h in c["hunks"] if h.get("func")}
    return names, cutoff


def evidence(item, facts, vals, fn_files):
    """criteria 三: 3 proven divergent constant, 2 riscv-specific implementation, 1 other"""
    md = facts["macros"].get(item)
    vs = [vals[a].get(item) for a in ARCHS]
    ints = [v for v in vs if isinstance(v, int)]
    objlike = (md is not None and not md["fl"]) or (md is None and item not in fn_files and len(ints) > 0)
    if objlike and len(ints) >= 2 and len(set(ints)) > 1:
        return 3
    if md is not None:
        f = md.get("file") or ""
        if md["fl"] and ("arch/riscv/" in f or DRV.search(f)):
            return 2
        if not md["fl"] and "arch/riscv/" in f and not isinstance(vals["riscv"].get(item), int):
            return 2
        return 1
    files = fn_files.get(item, [])
    if any(f.startswith("arch/riscv/") or DRV.search(f) for f in files):
        return 2
    return 1


def score_sites(h, facts, vals, pnames):
    fn_files = {}
    for f in facts["functions"].values():
        fn_files.setdefault(f["name"], []).append(f["file"])
    n = {}
    for sc, ss in h["sites"].items():
        for it in {i for s in ss for i in s["divergent"]}:
            n[it] = n.get(it, 0) + 1
    ev_cache = {}
    scored = {}
    for sc, ss in h["sites"].items():
        out = []
        for s in ss:
            best, why = 0.0, None
            for it in s["divergent"]:
                if it not in ev_cache:
                    ev_cache[it] = evidence(it, facts, vals, fn_files)
                w = 1.0 / math.log2(1 + n[it])
                if ev_cache[it] * w > best:
                    best, why = ev_cache[it] * w, it
            D = 1.0 / (1 + s["depth"] / 4)
            C = 0.5 ** s.get("cb_hops", 0)
            P = 1.5 if (s["fn"] in pnames or any(i in pnames for i in s["items"])) else 1.0
            out.append(dict(s, score=best * D * C * P, e_item=why, e=ev_cache.get(why), P=P))
        out.sort(key=lambda x: -x["score"])
        scored[sc] = out
    return scored, ev_cache


def ordered_values(site, params, facts, vals, ev_cache):
    """criteria 四: e=3 K2 values first, then other K2, then the rest (K1)"""
    order = {}
    for p in site["values"]:
        pname, ptype = params[int(p)]
        first, second = [], []
        for o in site["objects"]:
            avs = [vals[a].get(o) for a in ARCHS]
            ints = [v for v in avs if isinstance(v, int)]
            e3 = len(ints) >= 2 and len(set(ints)) > 1
            vv = []
            for v in avs:
                if not isinstance(v, int):
                    continue
                vv += ["i:%x" % trunc(v + dd, ptype) for dd in (-1, 0, 1)]
                if is_addr(pname, ptype) and v > 0 and v.bit_length() <= 64:
                    vv.append("o:%d" % (v.bit_length() - 1))
            (first if e3 else second).extend(vv)
        have = set(site["values"][p])
        seq = [x for x in first + second if x in have] + sorted(have)
        seen, res = set(), []
        for x in seq:
            if x not in seen:
                seen.add(x)
                res.append(x)
        order[p] = res
    return order


def main_group(group):
    tag = "CUR" if group == "CUR" else f"{group}_pre"
    facts = json.load(gzip.open(f"/root/work/static2/facts/{tag}.json.gz", "rt"))
    vals = json.loads(Path(f"/root/work/static2/values/{group}.json").read_text())
    h = run(facts, vals, {"I1", "I2", "I3", "I4"})
    pnames, cutoff = patch_names(group)
    scored, ev_cache = score_sites(h, facts, vals, pnames)
    U = universe(group, h["entries"])
    sc_score = {sc: ss[0]["score"] for sc, ss in scored.items() if sc in U}
    if h["raw_nr"]:
        sc_score["raw_nr"] = 2.0 * (1.5 if any(x["fn"] in pnames for x in h["raw_nr"]["ifs"]) else 1.0)
    ranked = sorted(sc_score, key=lambda sc: (-sc_score[sc], sc))
    top = ranked[:K]
    sites_out, capped = {}, {}
    for sc in top:
        if sc == "raw_nr":
            continue
        params = h["entries"][sc]
        cap = {}
        for s in scored[sc]:
            for p, vs in ordered_values(s, params, facts, vals, ev_cache).items():
                lst = cap.setdefault(p, [])
                for x in vs:
                    if len(lst) < V and x not in lst:
                        lst.append(x)
        capped[sc] = cap
        sites_out[sc] = []
        for s in scored[sc][:TOPSITES]:
            v2 = {p: [x for x in vs if x in cap.get(p, [])] for p, vs in s["values"].items()}
            v2 = {p: vs for p, vs in v2.items() if vs}
            if v2:
                sites_out[sc].append({"fn": s["fn"], "line": s["line"], "score": s["score"], "values": v2})
    pruned = {"group": group, "entries": h["entries"], "sites": {k: v for k, v in sites_out.items() if v},
              "raw_nr": h["raw_nr"] if "raw_nr" in top else None, "NR_syscalls": h["NR_syscalls"],
              "T": sorted(sc for sc in top if sc == "raw_nr" or sites_out.get(sc)),
              "stats": {"T_before": len([s for s in h["T"] if s in U]), "T_after": len(top), "K": K, "V": V}}
    (GEN / f"hints_{group}.json").write_text(json.dumps(pruned, indent=0))
    # criteria 5.1
    ev = {"group": group, "cutoff": cutoff, "patch_names": len(pnames), "T_ranked": len(ranked),
          "evidence_counts": {str(k): sum(1 for v in ev_cache.values() if v == k) for k in (1, 2, 3)},
          "top": [[i + 1, sc, round(sc_score[sc], 4), (scored[sc][0]["fn"], scored[sc][0]["e_item"],
                   scored[sc][0]["e"], scored[sc][0]["depth"], scored[sc][0].get("cb_hops"), scored[sc][0]["P"])
                   if sc in scored else ("raw_nr",)] for i, sc in enumerate(ranked[:60])]}
    fi = FIXITEMS.get(group)
    if group != "CUR":
        if fi == "raw_nr":
            fsc = ["raw_nr"] if "raw_nr" in sc_score else []
            fixvals = {"raw_nr": True} if "raw_nr" in top else {}
        elif fi:
            fsc = sorted(sc for sc, ss in scored.items() if sc in U and any(fi & (set(s["items"]) | set(s["objects"]))
                                                                             for s in ss))
            fixvals = {}
            for sc in fsc:
                if sc not in capped:
                    continue
                vals_fix = set()
                for s in scored[sc]:
                    if fi & (set(s["items"]) | set(s["objects"])):
                        for vs in s["values"].values():
                            vals_fix |= set(vs)
                kept = {x for vs in capped[sc].values() for x in vs}
                fixvals[sc] = bool(vals_fix & kept)
        else:
            fsc, fixvals = [], {}
        ranks = {sc: ranked.index(sc) + 1 for sc in fsc}
        ev["fixpoint"] = {"syscalls": ranks, "best_rank": min(ranks.values()) if ranks else None,
                          "in_topK": [sc for sc, r in ranks.items() if r <= K], "values_kept": fixvals,
                          "evaluable": fi is not None}
    (HERE.parent / f"ranking_{group}.json").write_text(json.dumps(ev, indent=1))
    print(group, "T", len(ranked), "->", len(top), "fix", json.dumps(ev.get("fixpoint")), flush=True)


def selftest():
    facts = {"macros": {"A": {"fl": False, "file": "arch/riscv/include/asm/a.h"},
                        "B": {"fl": True, "file": "arch/riscv/include/asm/b.h"},
                        "C": {"fl": True, "file": "include/linux/c.h"}},
             "functions": {"u1": {"name": "f_riscv", "file": "arch/riscv/kernel/x.c"},
                           "u2": {"name": "f_pub", "file": "kernel/y.c"}}}
    vals = {"riscv": {"A": 1}, "arm64": {"A": 2}, "x86_64": {"A": 2}}
    fn_files = {"f_riscv": ["arch/riscv/kernel/x.c"], "f_pub": ["kernel/y.c"]}
    got = [evidence(x, facts, vals, fn_files) for x in ("A", "B", "C", "f_riscv", "f_pub")]
    assert got == [3, 2, 1, 2, 1], got
    h = {"sites": {"s1": [{"fn": "g", "line": 1, "depth": 4, "cb_hops": 1, "items": ["A"], "objects": ["A"],
                           "divergent": {"A": "x"}, "values": {"0": ["i:1"]}}],
                   "s2": [{"fn": "patched", "line": 2, "depth": 0, "cb_hops": 0, "items": ["C"], "objects": [],
                           "divergent": {"C": "x"}, "values": {"0": ["i:2"]}}]}}
    sc, _ = score_sites(h, facts, vals, {"patched"})
    s1 = 3 * (1 / math.log2(2)) * (1 / 2) * 0.5 * 1.0
    s2 = 1 * (1 / math.log2(2)) * 1 * 1 * 1.5
    assert abs(sc["s1"][0]["score"] - s1) < 1e-9 and abs(sc["s2"][0]["score"] - s2) < 1e-9, sc
    print("SELFTEST PASS", got, round(s1, 4), round(s2, 4))


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest()
    else:
        for g in sys.argv[1:]:
            main_group(g)
