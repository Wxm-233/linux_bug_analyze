"""buildattr criteria 三/五 (+ amendment 1): per-build feasibility of rule-A-v2 parameter chains, from compile databases. WSL.

    python3 attr.py run      -> attr.json (per report x build), summary.json, attr.log
Rerun linmap2 (read-only import) on df2908090cda to get the summary object; must reproduce head.json's 580 'param' reports.
"""
import json
import resource
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "linmap2_20261119"))
import linmap2 as V2  # noqa: E402

L = V2.L
REV = "df2908090cda"
BUILDS = {a: f"/root/work/boundary_build/{a}_defconfig" for a in ("riscv", "arm64", "x86_64")}
SRC = "/root/repos/linux/"
STATES = ("调用文件未入选", "定义互斥", "定义可共存", "证据不足")


def compiled_sets():
    out = {}
    for a, d in BUILDS.items():
        cc = json.load(open(d + "/compile_commands.json"))
        out[a] = {e["file"][len(SRC):] for e in cc if e["file"].startswith(SRC) and e["file"].endswith(".c")}
    return out


def key(c):
    return (c["file"], c["line"], c["func"], c["sink_file"], c["sink_func"], tuple(c["via"]), c["arg"])


def edge_defs(Pp, f, g):
    """amendment 1: definitions of f that, analysed alone, produce a parameter summary whose first hop is g
    (g is None: f calls the sink directly)"""
    out = []
    saved = Pp.sp.pop(f, None)
    try:
        for path, pf in Pp.files.items():
            for fn in pf.funcs:
                if fn[0] != f:
                    continue
                Pp.sp.pop(f, None)
                Pp.walk(pf, fn, False)
                ent = Pp.sp.get(f, {})
                if any((info[4][:1] == [g]) if g else (not info[4]) for info in ent.values()):
                    out.append(path)
    finally:
        Pp.sp.pop(f, None)
        if saved is not None:
            Pp.sp[f] = saved
    return sorted(set(out))


def main():
    t0 = time.time()
    cs = compiled_sets()
    ref = json.loads((CT / "linmap2_20261119/head.json").read_text(encoding="utf-8"))
    v1, cands, info, Pp = V2.run(L.full(REV))
    same = Counter(map(key, cands)) == Counter(map(key, ref["param"]))
    n_vk = sum(1 for c in cands if c["via"][-2:] == ["vfree", "kfree"] or c["via"] == ["vfree", "kfree"])
    print("rerun", len(cands), "identical to head.json:", same, "| via ..vfree,kfree:", n_vk, flush=True)
    if not same:
        raise SystemExit("rerun differs from head.json -- stop (criteria 二)")
    cache = {}
    rows = []
    for c in cands:
        hops = []
        chain = c["via"]                         # caller -> via[0] -> ... -> via[-1] (= sink func) -> sink
        for k, f in enumerate(chain):
            g = chain[k + 1] if k + 1 < len(chain) else None
            if (f, g) not in cache:
                cache[(f, g)] = edge_defs(Pp, f, g)
            hops.append({"f": f, "g": g or c["sink"], "defs": cache[(f, g)]})
        st = {}
        for a, files in cs.items():
            if c["file"] not in files:
                st[a] = "调用文件未入选"
                continue
            res = []
            for h in hops:
                if not h["defs"] or any(not p.endswith(".c") for p in h["defs"]):
                    res.append("unknown") if not any(p in files for p in h["defs"]) else res.append("ok")
                elif any(p in files for p in h["defs"]):
                    res.append("ok")
                else:
                    res.append("excluded")
            st[a] = "定义互斥" if "excluded" in res else ("证据不足" if "unknown" in res else "定义可共存")
        rows.append({**{k: c[k] for k in ("file", "line", "func", "sink_func", "via", "arg", "kind")}, "hops": hops, "state": st})
    # report-level
    rep = Counter()
    for r in rows:
        v = set(r["state"].values())
        if "定义可共存" in v:
            rep["仍可行"] += 1
        elif "证据不足" in v:
            rep["有未知"] += 1
        elif v == {"调用文件未入选"}:
            rep["三个构建都没编入调用文件"] += 1
        else:
            rep["所有链都被排除"] += 1
    per_build = {a: Counter(r["state"][a] for r in rows) for a in cs}
    edges = Counter((h["f"], h["g"], tuple(h["defs"])) for r in rows for h in r["hops"][1:])
    # blind comparison
    be = json.loads((HERE / "blind_expect.json").read_text(encoding="utf-8"))
    idx = {(r["file"], r["line"], r["func"]): r for r in rows}
    blind = []
    for s in be["sample"]:
        r = idx.get((s["file"], s["line"], s["func"]))
        got = r["state"] if r else None
        blind.append({**s, "got": got, "agree": got == s["expect"]})
    ctrl = []
    v1idx = {(x["file"], x["line"], x["func"]) for x in v1}
    for cdef in be["controls"]:
        k3 = (cdef["file"], cdef["line"], cdef["func"])
        if cdef["source"] == "v2":
            r = idx.get(k3)
            got = r["state"][cdef["arch"]] if r else None
        else:
            got = ("定义可共存" if cdef["file"] in cs[cdef["arch"]] else "调用文件未入选") if k3 in v1idx else None
        ctrl.append({**cdef, "got": got, "ok": got == cdef["expect"]})
    # criteria 五.3 denominator: known-edge reports whose caller file is compiled in >=1 build (distinct positions)
    known = [r for r in rows if r["via"][-2:] == ["vfree", "kfree"] or "vmalloc_to_page" in r["via"]]
    den = [r for r in known if any(s != "调用文件未入选" for s in r["state"].values())]
    good = [r for r in den if all(s in ("定义互斥", "调用文件未入选") for s in r["state"].values())]
    summ = {"rerun_identical": same, "n_reports": len(rows), "via_vfree_kfree": n_vk, "per_build": {a: dict(v) for a, v in per_build.items()},
            "per_build_sum_ok": all(sum(v.values()) == len(rows) for v in per_build.values()),
            "report_level": dict(rep), "distinct_edges": len(edges), "edges": [{"f": f, "g": g, "defs": list(d), "reports": n} for (f, g, d), n in edges.most_common(30)],
            "known_edge_reports": len(known), "denominator_positions": len({(r["file"], r["line"]) for r in den}),
            "correctly_excluded_positions": len({(r["file"], r["line"]) for r in good}),
            "blind_agree": sum(b["agree"] for b in blind), "blind_n": len(blind), "controls_ok": sum(c["ok"] for c in ctrl), "controls_n": len(ctrl),
            "secs": round(time.time() - t0, 1), "maxrss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)}
    (HERE / "attr.json").write_text(json.dumps({"rows": rows, "blind": blind, "controls": ctrl}, indent=1, ensure_ascii=False))
    (HERE / "summary.json").write_text(json.dumps(summ, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in summ.items() if k != "edges"}, indent=1, ensure_ascii=False))
    print("top edges:")
    for e in summ["edges"][:10]:
        print("  ", e)
    print("blind disagreements:")
    for b in blind:
        if not b["agree"]:
            print("  ", b["file"], b["line"], "expect", b["expect"], "got", b["got"])
    print("controls:")
    for c in ctrl:
        print("  ", c["arch"], c["file"], c["line"], "expect", c["expect"], "got", c["got"])


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    main()
