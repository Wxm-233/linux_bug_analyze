"""Per-architecture translation of interface constants (anyarch criteria 三 + amendment 1). Pure Python.

    python translate.py calib            -> calib_cases.json, cases_calib_<arch>.txt      (amendment 二)
    python translate.py confirm <compare_any.json>  -> confirmed.json
    python translate.py apply [--off]    -> cases_CURt_<arch>.txt (or cases_CURoff_<arch>.txt), apply_stats.json
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parents[1]
DG = CT / "diverse_dev_20261110" / "gen"
sys.path.insert(0, str(DG))
import mutate_lib as ML  # noqa: E402

GM = ML.GM
ADDR_NAMES = {"addr", "start", "brk", "uaddr", "uaddr2", "new_addr", "old_addr", "start_addr", "addr_hint"}
G = "CUR"


def load():
    consts = json.loads((HERE / f"consts_{G}.json").read_text())
    vn = json.loads((HERE / f"vocab_names_{G}.json").read_text())
    meta = json.loads((DG / f"cases_{G}.json").read_text())
    lay = json.loads((DG / f"layouts_{G}.json").read_text())
    nrt = json.loads((DG / "nr_tables.json").read_text())
    bases = json.loads((DG / "bases.json").read_text())["bases"]
    return consts, vn, meta, lay, nrt, bases


def families(consts, vn, bases):
    """amendment 一: {(sc, p, header): {riscv bit hex: {name, arch: hex}}}"""
    archs, div, files = consts["archs"], consts["divergent"], consts["files"]
    fam, why = {}, {}
    # names compared with the parameter, including those reached by expanding macro bodies (criteria 三)
    for sc, ps in consts["expanded"].items():
        for p, ns in ps.items():
            pname, ptype = vn["entries"][sc][int(p)]
            for n in ns:
                if n not in div:
                    continue
                f = files.get(n) or ""
                if "include/uapi/" not in f:
                    r = "not_uapi"
                elif ptype.strip().endswith("*"):
                    r = "pointer"
                elif pname in GM.RES:
                    r = "resource"
                elif pname in ADDR_NAMES:
                    r = "address"
                elif not any(len(b["args"]) > int(p) and b["args"][int(p)].startswith("i:")
                             for b in bases.get(sc, {}).get("bases", [])):
                    r = "no_integer_base"
                else:
                    r = None
                if r:
                    why[r] = why.get(r, 0) + 1
                    continue
                v = {a: int(div[n][a], 16) for a in archs}
                if not all(x and x & (x - 1) == 0 for x in v.values()):
                    why["not_single_bit"] = why.get("not_single_bit", 0) + 1
                    continue
                hdr = re.sub(r"^.*include/uapi/", "", f)
                fam.setdefault(f"{sc}/{p}/{hdr}", {})[format(v[archs[0]], "x")] = dict(
                    {a: format(x, "x") for a, x in v.items()}, name=n)
    return fam, why


def tr(value, bits, arch):
    """bit translation; None on collision"""
    sel = [b for b in bits if value & int(b, 16)]
    if not sel:
        return value
    rest = value
    for b in sel:
        rest &= ~int(b, 16)
    new = 0
    for b in sel:
        t = int(bits[b][arch], 16)
        if new & t or rest & t:
            return None
        new |= t
    return rest | new


def translate_cases(cases, table, archs, enabled=lambda c: True):
    """table: {sc: {param idx: bits}} -> {arch: [cases]}, stats"""
    out = {a: [] for a in archs}
    st = {a: {"changed": 0, "collision": 0} for a in archs}
    for c in cases:
        tab = table.get(c["sc"]) if enabled(c) else None
        for a in archs:
            if not tab:
                out[a].append(c)
                continue
            args, ch = list(c["args"]), False
            for p, bits in tab.items():
                i = int(p)
                if i < len(args) and args[i].startswith("i:"):
                    v = int(args[i][2:], 16)
                    nv = tr(v, bits, a)
                    if nv is None:
                        st[a]["collision"] += 1
                    elif nv != v:
                        args[i] = "i:%x" % nv
                        ch = True
            st[a]["changed"] += ch
            out[a].append(dict(c, args=args) if ch else c)
    return out, st


def write_lines(tag, per_arch, lay, nrt, NR, archs):
    for a in archs:
        ls = ML.lines(per_arch[a], lay, nrt, NR)[a]
        # CRLF on purpose: byte-identical to the lists the earlier rounds actually ran (written on Windows)
        (HERE / f"cases_{tag}_{a}.txt").write_text("\n".join(ls) + "\n", newline="\r\n")


def table_of(fam, keys):
    t = {}
    for k in keys:
        sc, p, _ = k.split("/", 2)
        t.setdefault(sc, {}).setdefault(p, {}).update(fam[k])
    return t


def main():
    mode = sys.argv[1]
    consts, vn, meta, lay, nrt, bases = load()
    archs = consts["archs"]
    fam, why = families(consts, vn, bases)
    NR = meta["NR_syscalls"]
    if mode == "calib":
        cases, info = [], []
        for k in sorted(fam):
            sc, p, _ = k.split("/", 2)
            i = int(p)
            for bi, b in enumerate(bases[sc]["bases"]):
                if len(b["args"]) <= i or not b["args"][i].startswith("i:"):
                    continue
                for bit in sorted(fam[k], key=lambda x: int(x, 16)):
                    v = int(b["args"][i][2:], 16) | int(bit, 16)
                    for variant in ("U", "T"):
                        c = {kk: vv for kk, vv in b.items() if kk != "cand"}
                        c["args"] = list(b["args"])
                        c["args"][i] = "i:%x" % v
                        c["id"] = len(cases) + 1
                        cases.append(c)
                        info.append({"id": c["id"], "family": k, "base": bi, "bit": bit, "name": fam[k][bit]["name"],
                                     "variant": variant})
        # each T case translates only the family under test (otherwise a base whose other argument already
        # carries a divergent bit would be "fixed" by that other family and credited to this one)
        per, st = {a: [] for a in archs}, {a: {"changed": 0, "collision": 0} for a in archs}
        for c, x in zip(cases, info):
            one, s1 = translate_cases([c], table_of(fam, [x["family"]] if x["variant"] == "T" else []), archs)
            for a in archs:
                per[a] += one[a]
                for kk in s1[a]:
                    st[a][kk] += s1[a][kk]
        write_lines("calib", per, lay, nrt, NR, archs)
        (HERE / "calib_cases.json").write_text(json.dumps(
            {"group": "calib", "families": fam, "rejected_by_filter": why, "info": info, "translate_stats": st,
             "cases": cases}, indent=0))
        print("families", len(fam), sorted(fam), "filtered", why, "calib cases", len(cases), st)
    elif mode == "confirm":
        cmp_ = json.loads(Path(sys.argv[2]).read_text(encoding="utf8"))
        s = next(iter(cmp_["sets"].values()))  # CUR: every set is the same triple
        info = json.loads((HERE / "calib_cases.json").read_text())["info"]
        vd = lambda i: s["verdicts"].get(str(i), "same")  # noqa: E731
        res = {}
        pairs = {}
        for x in info:
            pairs.setdefault((x["family"], x["base"], x["bit"]), {})[x["variant"]] = x["id"]
        for (k, base, bit), ids in sorted(pairs.items()):
            u, t = vd(ids["U"]), vd(ids["T"])
            r = res.setdefault(k, {"support": [], "against": [], "neutral": 0, "skipped": 0})
            if u in ("unstable", "excluded") or t in ("unstable", "excluded"):
                r["skipped"] += 1
            elif u != "same" and t == "same":
                r["support"].append([base, fam[k][bit]["name"], u])
            elif u == "same" and t != "same":
                r["against"].append([base, fam[k][bit]["name"], t])
            else:
                r["neutral"] += 1
        conf = sorted(k for k, r in res.items() if r["support"] and not r["against"])
        (HERE / "confirmed.json").write_text(json.dumps({"confirmed": conf, "detail": res}, indent=1))
        for k, r in res.items():
            print(k, "CONFIRMED" if k in conf else "no", "support", len(r["support"]), "against", len(r["against"]),
                  "neutral", r["neutral"], "skipped", r["skipped"])
    elif mode == "apply":
        off = "--off" in sys.argv
        conf = [] if off else json.loads((HERE / "confirmed.json").read_text())["confirmed"]
        per, st = translate_cases(meta["cases"], table_of(fam, conf), archs)
        tag = "CURoff" if off else "CURt"
        write_lines(tag, per, lay, nrt, NR, archs)
        if off:
            for a in archs:
                same = (HERE / f"cases_{tag}_{a}.txt").read_bytes() == (DG / f"cases_{G}_{a}.txt").read_bytes()
                print("regress", a, "identical" if same else "DIFFERENT")
                assert same
                (HERE / f"cases_{tag}_{a}.txt").unlink()
        else:
            changed = {a: [c["id"] for c, o in zip(per[a], meta["cases"]) if c is not o] for a in archs}
            (HERE / "apply_stats.json").write_text(json.dumps(
                {"confirmed": conf, "stats": st, "changed_ids": changed}, indent=0))
            print("apply", conf, st)


if __name__ == "__main__":
    main()
