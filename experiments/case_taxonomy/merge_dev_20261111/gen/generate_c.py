"""G3c = G3d + limit-relative hint values (both spellings, mmap_top only) + interface-constant translation
(merge criteria 二). Pure Python.

    python generate_c.py <group>... -> cases_<group>.json, lists_<group>.json, cases_<group>_<kernel>.txt
"""
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parents[1]
DG = CT / "diverse_dev_20261110" / "gen"
sys.path.insert(0, str(CT / "anyarch_dev_20261110" / "gen"))
import translate as TR  # noqa: E402  (constant translation; also puts mutate_lib on the path)

ML = TR.ML
S = {g: [(1 << 63) - 1, 1 << 52] for g in ("A101", "A310", "A171", "B467")}
S["A181"] = S["CUR"] = [1 << 52]
SEEDS = ("1", "2", "3")
OTOK = re.compile(r"o:([zag]):52$")


def kernels(g):
    if g == "CUR":
        return {"cur_riscv": "riscv", "cur_arm64": "arm64", "cur_x86_64": "x86_64"}
    p = g.lower()
    return {f"{p}_pre": "riscv", f"{p}_fix": "riscv", f"{p}_ref_arm64": "arm64", f"{p}_ref_x86_64": "x86_64"}


def main():
    probes = json.loads((CT / "rtprobe_dev_20261110" / "probes.json").read_text())
    nrt = json.loads((DG / "nr_tables.json").read_text())
    consts, vn, _, _, _, bases = TR.load()
    fam, _ = TR.families(consts, vn, bases)
    conf = json.loads((CT / "anyarch_dev_20261110/gen/confirmed.json").read_text())["confirmed"]
    table = TR.table_of(fam, conf)
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
            m = int(v["mmap_top"], 16)
            lim[k] = {"m": m, "bit": (m - 1).bit_length()}  # smallest b with 2^b >= mmap_top
        g3d = {s: lists["G3d"][s] for s in SEEDS}
        used = sorted({i for s in SEEDS for i in g3d[s]})
        new, relid = [], {}
        n_int = n_o = n_both = 0
        nid = max(C) + 1
        for i in used:
            c = C[i]
            ii = [j for j, t in enumerate(c["args"]) if t.startswith("i:") and int(t[2:], 16) in hint]
            oo = [j for j, t in enumerate(c["args"]) if OTOK.match(t)]
            if not ii and not oo:
                continue
            if random.Random(f"{g}/rel/{i}").random() < 0.5:  # same coin as the relhint round
                continue
            n_int += bool(ii) and not oo
            n_o += bool(oo) and not ii
            n_both += bool(ii) and bool(oo)
            new.append(dict(c, id=nid, rel={"kind": "m", "of": i,
                                            "args": {str(j): hint[int(c["args"][j][2:], 16)] for j in ii},
                                            "obits": [j for j in oo]}))
            relid[i] = nid
            nid += 1
        # a G3d case that carries a translatable constant gets a copy with a new id in G3c, so that the G3d case
        # itself stays byte-identical (criteria 二.2: the translation applies to every G3c case)
        archs = sorted(set(ks.values()))
        constid = {}
        for i in used:
            if i in relid:
                continue
            tr1, _ = TR.translate_cases([C[i]], table, archs)
            if any(tr1[a][0] is not C[i] for a in archs):
                new.append(dict(C[i], id=nid, const_copy_of=i))
                constid[i] = nid
                nid += 1
        g3c = {s: [relid.get(i, constid.get(i, i)) for i in g3d[s]] for s in SEEDS}
        only_c = {c["id"] for c in new}
        cases = [C[i] for i in used] + new
        changed_const = {}
        for k, a in ks.items():
            out = []
            for c in cases:
                if "rel" in c:
                    args = list(c["args"])
                    for j, d in c["rel"]["args"].items():
                        args[int(j)] = "i:%x" % ((lim[k]["m"] + d) % 2**64)
                    for j in c["rel"]["obits"]:
                        args[j] = "o:%s:%d" % (OTOK.match(args[j]).group(1), lim[k]["bit"])
                    c = dict(c, args=args)
                if c["id"] in only_c:
                    t1, _ = TR.translate_cases([c], table, [a])
                    if t1[a][0] is not c:
                        changed_const[k] = changed_const.get(k, 0) + 1
                    c = t1[a][0]
                out.append(c)
            ls = ML.lines(out, lay, nrt, meta["NR_syscalls"])[a]
            (HERE / f"cases_{g}_{k}.txt").write_text("\n".join(ls) + "\n", newline="\r\n")
        m2 = {k: v for k, v in meta.items() if k != "cases"}
        m2.update({"cases": cases, "merge": {
            "limits": {k: {"mmap_top": format(v["m"], "x"), "bit": v["bit"]} for k, v in lim.items()},
            "relative_cases": len(new), "only_integer_form": n_int, "only_o_form": n_o, "both_forms": n_both,
            "const_copies": len(constid), "lines_changed_by_constants": changed_const}})
        (HERE / f"cases_{g}.json").write_text(json.dumps(m2, indent=0))
        (HERE / f"lists_{g}.json").write_text(json.dumps({"G3d": g3d, "G3c": g3c}))
        for k, a in ks.items():
            old = {l.split(" ", 1)[0]: l for l in (DG / f"cases_{g}_{a}.txt").read_text().splitlines()}
            mine = {l.split(" ", 1)[0]: l for l in (HERE / f"cases_{g}_{k}.txt").read_text().splitlines()}
            assert all(mine[str(i)] == old[str(i)] for i in used), (g, k)
        print(g, "cases", len(cases), json.dumps(m2["merge"]))


if __name__ == "__main__":
    main()
