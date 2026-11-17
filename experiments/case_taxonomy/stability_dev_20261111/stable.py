"""Volatile-output learning and normalisation (stability criteria 二). Pure Python, reads gz logs.

    python stable.py learn                 -> volatile.json           (from diverse_dev_20261110/runs)
    python stable.py retest                -> retest.json             (criteria 三.2, 三.3, 三.5)
"""
import glob
import gzip
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "diverse_dev_20261110"))
sys.path.insert(0, str(CT / "anyarch_dev_20261110"))
import compare as C  # noqa: E402
import compare_any as CA  # noqa: E402

GROUPS = ["CUR", "A101", "A310", "A171", "A181", "B467"]
ERRNO = re.compile(r"^E[A-Z0-9]+$")


def read_runs(run_dir, g):
    """{kernel: [cases of run1, run2, run3]}"""
    out = {}
    for f in sorted(glob.glob(str(run_dir / g / "*.log.gz"))):
        k, i = re.match(r"(.*)\.run(\d)\.log\.gz", os.path.basename(f)).groups()
        t = gzip.open(f).read().replace(b"\x00", b"").decode("utf-8", "replace")
        t, _ = C.KMSG.subn("", t)
        p = C.parse_log(t)
        assert p["complete"], f
        out.setdefault(k, []).append(p)
    return out


def slots(case, v):
    """[(slot key, (count, hash))] of one observation"""
    sc = case["sc"]
    out = []
    for ai, n, h in v[2] or []:
        out.append(((sc, "b", str(ai)), (n, h)))
    if v[3] and v[3] != [None, None]:
        out.append(((sc, "pool", ""), tuple(v[3])))
    if len(v) > 4 and v[4]:
        S = case.get("structs", [])
        for k, n, h in v[4]:
            ty = S[k].get("type", "plain") if k < len(S) else "plain"
            out.append(((sc, "s", ty), (n, h)))
    return out


def learn():
    vs, vr = {}, {}
    for g in GROUPS:
        cases = {str(c["id"]): c for c in json.loads((CT / "diverse_dev_20261110/gen" / f"cases_{g}.json").read_text())["cases"]}
        for k, runs in read_runs(CT / "diverse_dev_20261110/runs", g).items():
            for cid, c in cases.items():
                o = [r["cases"].get(cid) for r in runs]
                if None in o:
                    continue
                if len({o_[0] for o_ in o}) > 1:
                    vr.setdefault(c["sc"], set()).add(f"{g}/{cid}")
                if len({(o_[0], o_[1]) for o_ in o}) > 1:
                    continue
                per = {}
                for o_ in o:
                    d = {}
                    for key, val in slots(c, o_):
                        d.setdefault(key, []).append(val)
                    for key, val in d.items():
                        per.setdefault(key, set()).add(tuple(val))
                for key, vals in per.items():
                    if len(vals) > 1:
                        vs.setdefault(key, set()).add(f"{g}/{cid}")
    out = {"slots": sorted(["|".join(k), len(v)] for k, v in vs.items() if len(v) >= 2),
           "slots_below_threshold": sorted(["|".join(k), len(v)] for k, v in vs.items() if len(v) < 2),
           "returns": sorted([sc, len(v)] for sc, v in vr.items() if len(v) >= 2),
           "returns_below_threshold": sorted([sc, len(v)] for sc, v in vr.items() if len(v) < 2)}
    (HERE / "volatile.json").write_text(json.dumps(out, indent=1))
    print("volatile slots", len(out["slots"]), "returns", len(out["returns"]),
          "below threshold", len(out["slots_below_threshold"]), len(out["returns_below_threshold"]))
    for s in out["slots"]:
        print("  slot", s)
    for s in out["returns"]:
        print("  return", s)


def normaliser():
    v = json.loads((HERE / "volatile.json").read_text())
    VS = {tuple(s[0].split("|")) for s in v["slots"]}
    VR = {s[0] for s in v["returns"]}

    def norm(case, o):
        sc = case["sc"]
        o = list(o)
        if sc in VR and not ERRNO.match(o[0]):
            o[0] = "val"
        if o[2]:
            o[2] = [[ai, int(n > 0)] if (sc, "b", str(ai)) in VS else [ai, n, h] for ai, n, h in o[2]]
        if o[3] and o[3] != [None, None] and (sc, "pool", "") in VS:
            o[3] = [int(o[3][0] > 0)]
        if len(o) > 4 and o[4]:
            S = case.get("structs", [])
            o[4] = [[k, int(n > 0)] if (sc, "s", S[k].get("type", "plain") if k < len(S) else "plain") in VS
                    else [k, n, h] for k, n, h in o[4]]
        return o
    return norm


def kernels(g):
    if g == "CUR":
        return {"cur_riscv": "riscv", "cur_arm64": "arm64", "cur_x86_64": "x86_64"}
    p = g.lower()
    return {f"{p}_pre": "riscv", f"{p}_fix": "riscv", f"{p}_ref_arm64": "arm64", f"{p}_ref_x86_64": "x86_64"}


def verdicts(cases, runs, g, norm=None):
    """{checked riscv kernel: {cid: verdict}}, clusters, with the compare_any rules"""
    ks = kernels(g)
    hw = {k: any(C.is_hw_pmu(n) for n in runs[k][0]["probe"].get("pmu_devices", [])) for k in ks}
    stable, unstable = {}, set()
    for cid, c in cases.items():
        vals = {}
        for k in ks:
            o = [r["cases"].get(cid) for r in runs[k]]
            s = {json.dumps(norm(c, x) if norm and x is not None else x) for x in o}
            if len(s) != 1:
                unstable.add(cid)
                break
            vals[k] = s.pop()
        else:
            stable[cid] = vals
    cfg = {"kernels": [{"name": k, "arch": a} for k, a in ks.items()]}
    out, clusters = {}, {}
    for chk, cset in CA.sets(cfg).items():
        if ks[chk] != "riscv":
            continue
        vd, cl = {}, {}
        for cid, c in cases.items():
            if cid in unstable:
                vd[cid] = "unstable"
                continue
            v = CA.verdict(c, cset, hw, stable[cid])
            vd[cid] = v
            if v.startswith("odd_"):
                cl.setdefault(v[4:], {}).setdefault(CA.ckey(c, cset, stable[cid], v[4:]), []).append(cid)
        out[chk], clusters[chk] = vd, cl
    return out, clusters, stable


def count(vd, ids):
    d = {}
    for i in ids:
        d[vd[i]] = d.get(vd[i], 0) + 1
    return dict(sorted(d.items()))


def retest():
    norm = normaliser()
    res = {"pairs": {}, "current_directions": {}, "new_odd_clusters": []}
    tot = {"old": 0, "new": 0}
    for g in GROUPS:
        allc = {str(c["id"]): c for c in json.loads((CT / "diverse_dev_20261110/gen" / f"cases_{g}.json").read_text())["cases"]}
        first = read_runs(CT / "diverse_dev_20261110/runs", g)
        tests = []
        if g == "CUR":
            ap = json.loads((CT / "anyarch_dev_20261110/gen/apply_stats.json").read_text())["changed_ids"]["arm64"]
            ids = [i for i in allc if int(i) not in set(ap)]
            tests.append(("diverse_vs_anyarch_all", read_runs(CT / "anyarch_dev_20261110/runs", "CURt"), ids))
        lists = json.loads((CT / "diverse_dev_20261110/gen" / f"lists_{g}.json").read_text())
        g3 = sorted({str(i) for s in lists["G3d"] for i in lists["G3d"][s]}, key=int)
        tests.append(("diverse_vs_relhint_G3d", read_runs(CT / "relhint_dev_20261110/runs", g), g3))
        for name, second, ids in tests:
            sub = {i: allc[i] for i in ids}
            row = {"cases": len(ids)}
            for tag, nf in (("old", None), ("new", norm)):
                v1, c1, _ = verdicts(sub, first, g, nf)
                v2, c2, st2 = verdicts(sub, second, g, nf)
                per = {}
                for chk in v1:
                    diff = [i for i in ids if v1[chk][i] != v2[chk][i]]
                    moves = {}
                    for i in diff:
                        m = f"{v1[chk][i]} -> {v2[chk][i]}"
                        moves[m] = moves.get(m, 0) + 1
                    per[chk] = {"differ": len(diff), "moves": dict(sorted(moves.items())),
                                "first": count(v1[chk], ids), "second": count(v2[chk], ids),
                                "clusters_first": {a: len(x) for a, x in c1[chk].items()},
                                "clusters_second": {a: len(x) for a, x in c2[chk].items()}}
                    tot[tag] += len(diff)
                    if tag == "new" and g == "CUR" and name == "diverse_vs_anyarch_all":
                        vo, co, _ = verdicts(sub, second, g, None)
                        for a, cl in c2[chk].items():
                            for key, m in cl.items():
                                if key not in co[chk].get(a, {}):
                                    ex = m[0]
                                    res["new_odd_clusters"].append(
                                        {"odd": a, "cluster": key, "n_cases": len(m), "example": ex,
                                         "sc": sub[ex]["sc"], "args": sub[ex]["args"],
                                         "old_verdicts": sorted({vo[chk][i] for i in m}), "values": st2[ex]})
                row[tag] = per
            res["pairs"][f"{g}/{name}"] = row
            for chk in row["old"]:
                print(g, name, chk, "cases", len(ids), "differ old", row["old"][chk]["differ"], "new",
                      row["new"][chk]["differ"], "| unstable(second) old", row["old"][chk]["second"].get("unstable", 0),
                      "new", row["new"][chk]["second"].get("unstable", 0))
    res["total_differ"] = tot
    (HERE / "retest.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf8")
    print("TOTAL differ", tot)
    cur = res["pairs"]["CUR/diverse_vs_anyarch_all"]
    for tag in ("old", "new"):
        p = cur[tag]["cur_riscv"]
        print(tag, "first", p["first"], p["clusters_first"], "second", p["second"], p["clusters_second"])
    print("new odd clusters under the new rule (second run):", len(res["new_odd_clusters"]))
    for c in res["new_odd_clusters"]:
        print("  ", c["odd"], c["cluster"], c["n_cases"], c["old_verdicts"], c["args"])
        for k, v in c["values"].items():
            print("       ", k, v[:110])


if __name__ == "__main__":
    {"learn": learn, "retest": retest}[sys.argv[1]]()
