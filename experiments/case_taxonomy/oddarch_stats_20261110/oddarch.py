"""Per-architecture odd-one-out statistics on the diverse_dev run logs (criteria 三). Pure Python, no kernel runs.

    python oddarch.py  -> stats.json, clusters_CUR.json, clusters_samples.json
"""
import gzip
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "diverse_dev_20261110"
sys.path.insert(0, str(SRC))
import compare as C  # noqa: E402  (reuses parse_log, KMSG, perf_needs_hw, is_hw_pmu; nothing runs on import)

GROUPS = ["CUR", "A101", "A171", "A181", "A310", "B467"]
ARCHS = ("riscv", "arm64", "x86_64")
MG = ("G0d", "G2d", "G3d")


def kernels(g):
    if g == "CUR":
        return {"cur_riscv": "riscv", "cur_arm64": "arm64", "cur_x86_64": "x86_64"}
    p = g.lower()
    return {f"{p}_pre": "riscv", f"{p}_fix": "riscv", f"{p}_ref_arm64": "arm64", f"{p}_ref_x86_64": "x86_64"}


def load(g):
    meta = json.loads((SRC / "gen" / f"cases_{g}.json").read_text())
    cases = {str(c["id"]): c for c in meta["cases"]}
    old = json.loads((SRC / "runs" / g / "compare.json").read_text())
    ks = kernels(g)
    obs, hw = {}, {}
    for k in ks:
        runs = []
        for i in (1, 2, 3):
            raw = gzip.open(SRC / "runs" / g / f"{k}.run{i}.log.gz").read()
            text = raw.replace(b"\x00", b"").decode("utf-8", "replace")
            text, _ = C.KMSG.subn("", text)
            runs.append(C.parse_log(text))
        assert all(r["complete"] for r in runs), (g, k)
        hw[k] = any(C.is_hw_pmu(n) for n in runs[0]["probe"].get("pmu_devices", []))
        obs[k] = [{cid: json.dumps(v) for cid, v in r["cases"].items()} for r in runs]
    assert hw == old["hw_pmu"], (g, hw, old["hw_pmu"])
    stable, unstable = {}, set()
    for cid in cases:
        vals = {}
        for k in ks:
            vs = {o.get(cid, "missing") for o in obs[k]}
            if len(vs) != 1:
                unstable.add(cid)
                break
            vals[k] = vs.pop()
        else:
            stable[cid] = vals
    assert sorted(unstable, key=int) == sorted(old["unstable"], key=int), g
    return cases, ks, hw, stable, unstable, old


def triple_verdicts(cases, trip, hw, stable, unstable):
    """trip: {arch: kernel}"""
    out = {}
    for cid, c in cases.items():
        if cid in unstable:
            out[cid] = "unstable"
            continue
        if C.perf_needs_hw(c) and not all(hw[k] for k in trip.values()):
            out[cid] = "excluded"
            continue
        v = {a: stable[cid][k] for a, k in trip.items()}
        distinct = set(v.values())
        if len(distinct) == 1:
            out[cid] = "same"
        elif len(distinct) == 3:
            out[cid] = "all_diff"
        else:
            odd = [a for a in ARCHS if sum(v[a] == v[b] for b in ARCHS) == 1]
            assert len(odd) == 1
            out[cid] = "odd_" + odd[0]
    return out


def ckey(c, vals, trip, arch):
    r = json.loads(vals[trip[arch]])[0]
    ref = sorted({json.loads(vals[trip[a]])[0] for a in ARCHS if a != arch})
    return f"{c['sc']}|{r}|{'/'.join(ref)}"


def count(vd):
    s = {}
    for v in vd.values():
        s[v] = s.get(v, 0) + 1
    return dict(sorted(s.items()))


def main():
    stats = {"groups": {}}
    cur_clusters, sample_clusters = [], []
    for g in GROUPS:
        cases, ks, hw, stable, unstable, old = load(g)
        lists = json.loads((SRC / "gen" / f"lists_{g}.json").read_text())
        ref = {a: k for k, a in ks.items() if a != "riscv"}
        trips = {k: dict(ref, riscv=k) for k, a in ks.items() if a == "riscv"}
        vds = {k: triple_verdicts(cases, t, hw, stable, unstable) for k, t in trips.items()}
        gs = {"cases": len(cases), "triples": {}}
        mismatch = {}
        for rk, vd in vds.items():
            # regression against the earlier riscv-only comparison (criteria 三.7)
            for cid, v in vd.items():
                o = old["verdicts"][rk][cid]
                if (v == "odd_riscv") != (o == "odd_strong"):
                    mismatch.setdefault(f"{v}|{o}", []).append(cid)
            cl = {a: {} for a in ARCHS}
            for cid, v in vd.items():
                if v.startswith("odd_"):
                    a = v[4:]
                    cl[a].setdefault(ckey(cases[cid], stable[cid], trips[rk], a), []).append(cid)
            gs["triples"][rk] = {"verdicts": count(vd), "clusters": {a: len(cl[a]) for a in ARCHS}}
            if g == "CUR":
                by = {}
                for G in MG:
                    ids = {str(i) for s in lists[G] for i in lists[G][s]}
                    by[G] = {a: {"cases": sum(1 for c in ids if vd.get(c) == "odd_" + a),
                                 "clusters": sum(1 for cs in cl[a].values() if ids & set(cs))} for a in ARCHS}
                    by[G]["all_diff"] = sum(1 for c in ids if vd.get(c) == "all_diff")
                gs["triples"][rk]["by_method_group"] = by
                for a in ARCHS:
                    for k in sorted(cl[a]):
                        cs = sorted(cl[a][k], key=int)
                        ex = cs[0]
                        grp = [G for G in MG if any(int(c) in lists[G][s] for s in lists[G] for c in cs)]
                        cur_clusters.append({"odd": a, "cluster": k, "n_cases": len(cs), "groups": grp,
                                             "example": ex, "sc": cases[ex]["sc"], "args": cases[ex]["args"],
                                             "structs": cases[ex].get("structs"), "values": stable[ex]})
                for cid, v in vd.items():
                    if v == "all_diff":
                        cur_clusters.append({"odd": "all_diff", "cluster": cases[cid]["sc"], "n_cases": 1,
                                             "example": cid, "sc": cases[cid]["sc"], "args": cases[cid]["args"],
                                             "values": stable[cid]})
        assert not mismatch, (g, {k: len(v) for k, v in mismatch.items()})
        if g != "CUR":
            pre, fix = f"{g.lower()}_pre", f"{g.lower()}_fix"
            both = {}
            for a in ("arm64", "x86_64"):
                ids = [c for c in cases if vds[pre][c] == "odd_" + a and vds[fix][c] == "odd_" + a]
                cl = {}
                for cid in ids:
                    cl.setdefault(ckey(cases[cid], stable[cid], trips[pre], a), []).append(cid)
                both[a] = {"cases": len(ids), "clusters": len(cl)}
                for k in sorted(cl):
                    ex = sorted(cl[k], key=int)[0]
                    sample_clusters.append({"group": g, "odd": a, "cluster": k, "n_cases": len(cl[k]), "example": ex,
                                            "sc": cases[ex]["sc"], "args": cases[ex]["args"], "values": stable[ex]})
            gs["odd_in_both_pre_and_fix"] = both
        stats["groups"][g] = gs
        print(g, json.dumps(gs["triples"]), json.dumps(gs.get("odd_in_both_pre_and_fix", {})))
    union = {a: sorted({c["cluster"] for c in sample_clusters if c["odd"] == a} |
                       {c["cluster"] for c in cur_clusters if c["odd"] == a}) for a in ("arm64", "x86_64")}
    stats["distinct_cluster_keys_all_groups"] = {a: len(v) for a, v in union.items()}
    stats["cluster_keys_all_groups"] = union
    (HERE / "stats.json").write_text(json.dumps(stats, indent=1, ensure_ascii=False), encoding="utf8")
    (HERE / "clusters_CUR.json").write_text(json.dumps(cur_clusters, indent=1, ensure_ascii=False), encoding="utf8")
    (HERE / "clusters_samples.json").write_text(json.dumps(sample_clusters, indent=1, ensure_ascii=False),
                                                encoding="utf8")
    print(json.dumps(stats["distinct_cluster_keys_all_groups"]))


if __name__ == "__main__":
    main()
