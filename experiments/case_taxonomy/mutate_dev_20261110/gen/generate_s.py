"""G0s / G2s / G3s: base case + 1-2 point mutation (mutate criteria 三、四).

    python generate_s.py <group> -> cases_<group>.json, cases_<group>_<arch>.txt, lists_<group>.json

Bases come from bases.json (calibrated on the current version). For a group whose signature or layouts differ
from the current version, the base is rebuilt from the default options (first option of each parameter) of that
group's signature, and the substitution is counted.
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
    hints = {}
    for sc in T:
        if sc == "raw_nr":
            hints[sc] = {0: set(h["raw_nr"]["values"])}
            continue
        d = {}
        for s in h["sites"].get(sc, []):
            for p, vs in s["values"].items():
                d.setdefault(int(p), set()).update(vs)
        hints[sc] = d
    subst = []
    B_of = {}
    for sc in U:
        if sc == "raw_nr":
            B_of[sc] = [{"sc": "raw_nr", "args": ["r:0"] + ["i:0"] * 6, "tmpl": "none"}]
            continue
        bs = bases.get(sc, {}).get("bases", [])
        good = [b for b in bs if len(b["args"]) == len(params[sc]) and
                all(t in lay[a] for b2 in b.get("structs", []) if "type" in b2 for t in [b2["type"]] for a in ML.ARCHS)]
        if not good:
            good = ML.candidates(sc, params[sc], vocab, lay, random.Random(f"default/{group}/{sc}"), n=1)
            subst.append(sc)
        B_of[sc] = [{k: v for k, v in b.items() if k != "cand"} for b in good]
    cases, key2id, lists = [], {}, {}
    for G in ("G0s", "G2s", "G3s"):
        lists[G] = {}
        for seed in SEEDS:
            rng = random.Random(f"{group}/{G}/{seed}")
            order_u = U[:]
            rng.shuffle(order_u)
            target = [] if G == "G0s" else T[:]
            rng.shuffle(target)
            ids, iu, it = [], 0, 0
            for i in range(B):
                if target and i % 5 != 4:
                    sc, it = target[it % len(target)], it + 1
                    uh = G == "G3s"
                else:
                    sc, iu = order_u[iu % len(order_u)], iu + 1
                    uh = False
                base = rng.choice(B_of[sc])
                c = ML.mutate(base, params[sc], vocab, lay, rng, hints.get(sc), uh)
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
            "base_substituted": subst, "cases": cases}
    (HERE / f"cases_{group}.json").write_text(json.dumps(meta, indent=0))
    (HERE / f"lists_{group}.json").write_text(json.dumps(lists))
    print(group, "U", len(U), "T", len(T), "cases", len(cases), "base_substituted", len(subst),
          "structured", sum(1 for c in cases if c.get("structs")))


if __name__ == "__main__":
    main()
