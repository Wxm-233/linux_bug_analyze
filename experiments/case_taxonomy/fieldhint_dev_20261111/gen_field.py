"""G0d/G2d/G3d/G3c at B=2000 and G3f = G3c with field variants (fieldhint criteria 三). Pure Python (Windows).

    python gen_field.py <group>...   -> ws/..., run/<group>/{cases.json, lists.json, cases_<kernel>.txt}, field_stats.json
The frozen generator files are imported unchanged (generate_x.B and path variables are set, as in budget_dev).
"""
import json
import random
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "diverse_dev_20261110" / "gen"))
sys.path.insert(0, str(CT / "merge_dev_20261111" / "gen"))
import calib  # noqa: E402
import generate_x  # noqa: E402
import generate_c  # noqa: E402

TR, ML = generate_c.TR, generate_c.ML
DG = CT / "diverse_dev_20261110" / "gen"
SEEDS = ("1", "2", "3")
OTOK = re.compile(r"o:([zag]):52$")


def kernels(g):
    if g == "CUR":
        return {"cur_riscv": "riscv", "cur_arm64": "arm64", "cur_x86_64": "x86_64"}
    p = g.lower()
    return {f"{p}_pre": "riscv", f"{p}_fix": "riscv", f"{p}_ref_arm64": "arm64", f"{p}_ref_x86_64": "x86_64"}


def field_value(rng, e, size, signed):
    """criteria 三: one of four categories, chosen uniformly among the available ones"""
    consts = sorted(set(e["eq"]) | set(e["bounds"]))
    cats = (["const", "pm1"] if consts else []) + (["bits"] if e["bits"] else []) + ["outside"]
    cat = rng.choice(cats)
    if cat == "const":
        v = rng.choice(consts)
    elif cat == "pm1":
        v = rng.choice(consts) + rng.choice((-1, 1))
    elif cat == "bits":
        v = 0
        for b in rng.sample(e["bits"], min(len(e["bits"]), rng.choice((1, 2)))):
            v |= b
    else:
        v = (max(consts) + 1) if consts and rng.random() < 0.5 else rng.getrandbits(32)
    return cat, v & ((1 << (8 * size)) - 1)


def main():
    groups = sys.argv[1:]
    ws = HERE / "ws"
    xg, cg = ws / "diverse_dev_20261110" / "gen", ws / "merge_dev_20261111" / "gen"
    for d in (xg, cg, ws / "rankprune_dev_20261110" / "gen", ws / "twostage_dev_20261109", ws / "rtprobe_dev_20261110",
              ws / "anyarch_dev_20261110" / "gen"):
        d.mkdir(parents=True, exist_ok=True)
    for f in ("nr_tables.json", "bases.json"):
        shutil.copy(DG / f, xg / f)
    shutil.copy(CT / "twostage_dev_20261109" / "version_tables.json", ws / "twostage_dev_20261109")
    shutil.copy(CT / "rtprobe_dev_20261110" / "probes.json", ws / "rtprobe_dev_20261110")
    shutil.copy(CT / "anyarch_dev_20261110" / "gen" / "confirmed.json", ws / "anyarch_dev_20261110" / "gen")
    generate_x.B = 2000
    generate_x.HERE = calib.HERE = generate_c.DG = xg
    generate_c.CT, generate_c.HERE = ws, cg
    probes = json.loads((CT / "rtprobe_dev_20261110" / "probes.json").read_text())
    consts, vn, _, _, _, bases = TR.load()
    fam, _ = TR.families(consts, vn, bases)
    table = TR.table_of(fam, json.loads((CT / "anyarch_dev_20261110/gen/confirmed.json").read_text())["confirmed"])
    allstats = {}
    for g in groups:
        for f in (f"vocab_{g}.json", f"layouts_{g}.json"):
            shutil.copy(DG / f, xg / f)
        shutil.copy(CT / "rankprune_dev_20261110" / "gen" / f"hints_{g}.json", ws / "rankprune_dev_20261110" / "gen")
        sys.argv = ["generate_x.py", g]
        generate_x.main()
        sys.argv = ["generate_c.py", g]
        generate_c.main()
        lay = json.loads((xg / f"layouts_{g}.json").read_text())
        fv = json.loads((HERE / "static" / f"fieldvocab_{g}.json").read_text())["vocab"]
        xm = json.loads((xg / f"cases_{g}.json").read_text())
        cm = json.loads((cg / f"cases_{g}.json").read_text())
        xl, cl = json.loads((xg / f"lists_{g}.json").read_text()), json.loads((cg / f"lists_{g}.json").read_text())
        C = {c["id"]: c for c in xm["cases"] + cm["cases"]}
        nid = max(C) + 1
        used = sorted({i for s in SEEDS for i in cl["G3c"][s]})
        variant, new, st = {}, [], {"eligible": 0, "variants": 0, "by_cat": {}, "by_field": {}}
        for i in used:
            c = C[i]
            voc = fv.get(c["sc"], {})
            opts = []
            for k, b in enumerate(c.get("structs", [])):
                t = b.get("type")
                if not t or t not in lay["riscv"]:
                    continue
                fl = {x["name"]: x for x in lay["riscv"][t]["fields"]}
                for m, e in voc.items():
                    mt, mf = m.split("|", 1)
                    if mt == t and mf in fl and fl[mf]["off"] is not None and fl[mf]["size"] in (1, 2, 4, 8):
                        opts.append((k, mf, m, e, fl[mf]))
            if not opts:
                continue
            st["eligible"] += 1
            rng = random.Random(f"{g}/field/{i}")
            if rng.random() < 0.5:
                continue
            k, mf, m, e, fld = rng.choice(opts)
            cat, v = field_value(rng, e, fld["size"], fld["signed"])
            c2 = json.loads(json.dumps(c))
            c2["structs"][k].setdefault("set", {})[mf] = ["int", "%x" % v]
            c2["id"], c2["fvar"] = nid, {"of": i, "field": m, "cat": cat, "value": "%x" % v}
            variant[i] = nid
            new.append(c2)
            nid += 1
            st["variants"] += 1
            st["by_cat"][cat] = st["by_cat"].get(cat, 0) + 1
            st["by_field"][m] = st["by_field"].get(m, 0) + 1
        g3f = {s: [variant.get(i, i) for i in cl["G3c"][s]] for s in SEEDS}
        # per-kernel lines of the variants: relative values and constant translation exactly as generate_c does
        lim = {k: int(probes[k]["values"]["mmap_top"], 16) for k in kernels(g)}
        out = HERE / "run" / g
        out.mkdir(parents=True, exist_ok=True)
        xids = {c["id"] for c in xm["cases"]}
        cnew = [c for c in cm["cases"] if c["id"] not in xids]
        meta = {k: v for k, v in xm.items() if k != "cases"}
        meta["cases"] = xm["cases"] + cnew + new
        (out / "cases.json").write_text(json.dumps(meta, indent=0))
        (out / "lists.json").write_text(json.dumps({"G0d": xl["G0d"], "G2d": xl["G2d"], "G3d": xl["G3d"],
                                                    "G3c": cl["G3c"], "G3f": g3f}))
        cnewids = {str(c["id"]) for c in cnew}
        for kname, a in kernels(g).items():
            vs = []
            for c in new:
                if "rel" in c:
                    args = list(c["args"])
                    for j, d in c["rel"]["args"].items():
                        args[int(j)] = "i:%x" % ((lim[kname] + d) % 2**64)
                    for j in c["rel"]["obits"]:
                        args[j] = "o:%s:%d" % (OTOK.match(args[j]).group(1), (lim[kname] - 1).bit_length())
                    c = dict(c, args=args)
                t1, _ = TR.translate_cases([c], table, [a])
                vs.append(t1[a][0])
            vlines = ML.lines(vs, lay, json.loads((xg / "nr_tables.json").read_text()), meta["NR_syscalls"])[a]
            base = (xg / f"cases_{g}_{a}.txt").read_text().splitlines()
            add = [l for l in (cg / f"cases_{g}_{kname}.txt").read_text().splitlines() if l.split(" ", 1)[0] in cnewids]
            (out / f"cases_{kname}.txt").write_text("\n".join(base + add + vlines) + "\n")
        allstats[g] = st
        print(g, "cases", len(meta["cases"]), "G3f variants", st["variants"], "of eligible", st["eligible"],
              "top fields", sorted(st["by_field"].items(), key=lambda x: -x[1])[:5])
    (HERE / "field_stats.json").write_text(json.dumps(allstats, indent=1))


if __name__ == "__main__":
    main()
