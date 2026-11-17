"""G0x / G2x / G3x: each case is single-point mutation (mutate criteria 三) with probability 1/2, otherwise random
values + case model (casemodel criteria 二 and amendment 1). (mix criteria 二)

    python generate_x.py <group> -> cases_<group>.json, cases_<group>_<arch>.txt, lists_<group>.json
"""
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mutate_lib as ML  # noqa: E402
from calib import universe  # noqa: E402

BG, GM = ML.BG, ML.GM
B, SEEDS = 1000, (1, 2, 3)


def casemodel_case(rng, sc, params, hints_sites, use_hints, vocab, lay, use):
    """copy of casemodel generate_m.main.case (C1 -> C3 -> C2 after the base values, amendment 1)"""
    c = BG.make_case(rng, sc, params, hints_sites, use_hints)
    bld = GM.Builder(rng, lay)
    if sc != "raw_nr":
        for i, (pname, ptype) in enumerate(params):
            pt = GM.pointee(ptype)
            if pt and bld.ok(pt) and rng.random() < 0.5:
                n0 = len(bld.bufs)
                k = bld.struct(pt, 0)
                if len(bld.bufs) > 16 or any(len(b.get("set", {})) > 40 for b in bld.bufs):
                    del bld.bufs[n0:]
                else:
                    c["args"][i] = "t:%d" % k
                    use["C1"] += 1
            elif pname in GM.RES and rng.random() < 0.5:
                c["args"][i] = GM.RES[pname]
                use["C3"] += 1
            elif vocab.get(sc, {}).get(str(i)) and rng.random() < 0.5:
                v = vocab[sc][str(i)]
                x = rng.choice(v["eq"]) if v["eq"] else 0
                for b in rng.sample(v["bits"], min(len(v["bits"]), rng.choice([0, 1, 2]))):
                    x |= b
                c["args"][i] = BG.hexv(x, ptype)
                use["C2"] += 1
    if bld.bufs:
        c["structs"] = bld.bufs
    return c


def main():
    group = sys.argv[1]
    h = json.loads((HERE.parents[1] / "rankprune_dev_20261110" / "gen" / f"hints_{group}.json").read_text())
    vocab = json.loads((HERE / f"vocab_{group}.json").read_text())["vocab"]
    lay = json.loads((HERE / f"layouts_{group}.json").read_text())
    nrt = json.loads((HERE / "nr_tables.json").read_text())
    bases = json.loads((HERE / "bases.json").read_text())["bases"]
    U = universe(group, h, nrt) + ["raw_nr"]
    T = [s for s in h["T"] if s in U]
    params = {sc: h["entries"][sc] for sc in U if sc != "raw_nr"}
    params["raw_nr"] = BG.RAW_PARAMS
    sites = {sc: [s["values"] for s in h["sites"].get(sc, [])] for sc in T if sc != "raw_nr"}
    if "raw_nr" in T:
        sites["raw_nr"] = [{"0": h["raw_nr"]["values"]}]
    hints_p = {}
    for sc, ss in sites.items():
        d = {}
        for s in ss:
            for p, vs in s.items():
                d.setdefault(int(p), set()).update(vs)
        hints_p[sc] = d
    B_of, subst = {}, []
    for sc in U:
        if sc == "raw_nr":
            B_of[sc] = [{"sc": "raw_nr", "args": ["r:0"] + ["i:0"] * 6, "tmpl": "none"}]
            continue
        bs = bases.get(sc, {}).get("bases", [])
        good = [b for b in bs if len(b["args"]) == len(params[sc]) and
                all(b2["type"] in lay[a] for b2 in b.get("structs", []) if "type" in b2 for a in ML.ARCHS)]
        if not good:
            good = ML.candidates(sc, params[sc], vocab, lay, random.Random(f"default/{group}/{sc}"), n=1)
            subst.append(sc)
        B_of[sc] = [{k: v for k, v in b.items() if k != "cand"} for b in good]
    use = {"C1": 0, "C2": 0, "C3": 0, "mutate": 0, "random": 0}
    cases, key2id, lists = [], {}, {}
    for G in ("G0x", "G2x", "G3x"):
        lists[G] = {}
        for seed in SEEDS:
            rng = random.Random(f"{group}/{G}/{seed}")
            order_u = U[:]
            rng.shuffle(order_u)
            target = [] if G == "G0x" else T[:]
            rng.shuffle(target)
            ids, iu, it = [], 0, 0
            for i in range(B):
                if target and i % 5 != 4:
                    sc, it = target[it % len(target)], it + 1
                    uh = G == "G3x"
                else:
                    sc, iu = order_u[iu % len(order_u)], iu + 1
                    uh = False
                if rng.random() < 0.5:
                    c = ML.mutate(rng.choice(B_of[sc]), params[sc], vocab, lay, rng, hints_p.get(sc), uh)
                    use["mutate"] += 1
                else:
                    c = casemodel_case(rng, sc, params[sc], sites.get(sc), uh, vocab, lay, use)
                    use["random"] += 1
                key = json.dumps(c, sort_keys=True)
                if key not in key2id:
                    key2id[key] = len(cases) + 1
                    cases.append(dict(c, id=len(cases) + 1))
                ids.append(key2id[key])
            lists[G][str(seed)] = ids
    NR = {a: (h["NR_syscalls"].get(a) if isinstance(h["NR_syscalls"].get(a), int) else max(nrt[a].values()) + 1)
          for a in ML.ARCHS}
    for a, ls in ML.lines(cases, lay, nrt, NR).items():
        (HERE / f"cases_{group}_{a}.txt").write_text("\n".join(ls) + "\n")
    meta = {"group": group, "B": B, "seeds": SEEDS, "U": U, "T": T, "NR_syscalls": NR, "params": params,
            "base_substituted": subst, "use": use, "cases": cases}
    (HERE / f"cases_{group}.json").write_text(json.dumps(meta, indent=0))
    (HERE / f"lists_{group}.json").write_text(json.dumps(lists))
    print(group, "U", len(U), "T", len(T), "cases", len(cases), "use", use, "base_substituted", len(subst))


if __name__ == "__main__":
    main()
