"""G3r = G3d with half of the limit-hint cases made limit-relative (relhint criteria 二). Pure Python.

    python generate_r.py <group>... -> cases_<group>.json, lists_<group>.json, cases_<group>_<kernel>.txt
"""
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parents[1]
DG = CT / "diverse_dev_20261110" / "gen"
sys.path.insert(0, str(DG))
import mutate_lib as ML  # noqa: E402

S = {g: [(1 << 63) - 1, 1 << 52] for g in ("A101", "A310", "A171", "B467")}
S["A181"] = S["CUR"] = [1 << 52]
SEEDS = ("1", "2", "3")


def kernels(g):
    if g == "CUR":
        return {"cur_riscv": "riscv", "cur_arm64": "arm64", "cur_x86_64": "x86_64"}
    p = g.lower()
    return {f"{p}_pre": "riscv", f"{p}_fix": "riscv", f"{p}_ref_arm64": "arm64", f"{p}_ref_x86_64": "x86_64"}


def main():
    probes = json.loads((CT / "rtprobe_dev_20261110" / "probes.json").read_text())
    nrt = json.loads((DG / "nr_tables.json").read_text())
    for g in sys.argv[1:]:
        meta = json.loads((DG / f"cases_{g}.json").read_text())
        lists = json.loads((DG / f"lists_{g}.json").read_text())
        lay = json.loads((DG / f"layouts_{g}.json").read_text())
        C = {c["id"]: c for c in meta["cases"]}
        hint = {s + d: d for s in S[g] for d in (-1, 0, 1)}
        ks = kernels(g)
        lim = {}
        for k in ks:
            v = probes[k]["values"]
            assert probes[k]["complete"] and not probes[k]["unstable"] and not probes[k]["errors"], k
            lim[k] = {"m": int(v["mmap_top"], 16), "u": int(v["uaccess_top"], 16) - 1}
        g3d = {s: lists["G3d"][s] for s in SEEDS}
        used = sorted({i for s in SEEDS for i in g3d[s]})
        new, relid, kinds = [], {}, {"m": 0, "u": 0}
        nid = max(C) + 1
        for i in used:
            c = C[i]
            idx = [j for j, t in enumerate(c["args"]) if t.startswith("i:") and int(t[2:], 16) in hint]
            if not idx:
                continue
            rng = random.Random(f"{g}/rel/{i}")
            if rng.random() < 0.5:
                continue
            kind = rng.choice(["m", "u"])
            kinds[kind] += 1
            r = dict(c, id=nid, rel={"kind": kind, "of": i,
                                     "args": {str(j): hint[int(c["args"][j][2:], 16)] for j in idx}})
            new.append(r)
            relid[i] = nid
            nid += 1
        g3r = {s: [relid.get(i, i) for i in g3d[s]] for s in SEEDS}
        cases = [C[i] for i in used] + new
        per_kernel = {}
        for k, a in ks.items():
            out = []
            for c in cases:
                if "rel" in c:
                    args = list(c["args"])
                    for j, d in c["rel"]["args"].items():
                        args[int(j)] = "i:%x" % ((lim[k][c["rel"]["kind"]] + d) % 2**64)
                    out.append(dict(c, args=args))
                else:
                    out.append(c)
            ls = ML.lines(out, lay, nrt, meta["NR_syscalls"])[a]
            (HERE / f"cases_{g}_{k}.txt").write_text("\n".join(ls) + "\n", newline="\r\n")
            per_kernel[k] = sum(1 for c, o in zip(cases, out) if c is not o and o["args"] != c["args"])
        m2 = {k: v for k, v in meta.items() if k != "cases"}
        m2.update({"cases": cases, "rel": {"S": [format(s, "x") for s in S[g]], "limits": {
            k: {x: format(v, "x") for x, v in d.items()} for k, d in lim.items()}, "kinds": kinds,
            "relative_cases": len(new), "limit_hint_cases_in_G3d": sum(
                1 for i in used if any(t.startswith("i:") and int(t[2:], 16) in hint for t in C[i]["args"])),
            "lines_changed_per_kernel": per_kernel}})
        (HERE / f"cases_{g}.json").write_text(json.dumps(m2, indent=0))
        (HERE / f"lists_{g}.json").write_text(json.dumps({"G3d": g3d, "G3r": g3r}))
        # regression: the G3d part of every list equals the lines the diverse round ran
        for k, a in ks.items():
            old = {l.split(" ", 1)[0]: l for l in (DG / f"cases_{g}_{a}.txt").read_text().splitlines()}
            mine = {l.split(" ", 1)[0]: l for l in (HERE / f"cases_{g}_{k}.txt").read_text().splitlines()}
            assert all(mine[str(i)] == old[str(i)] for i in used), (g, k)
        print(g, "cases", len(cases), json.dumps(m2["rel"]))


if __name__ == "__main__":
    main()
