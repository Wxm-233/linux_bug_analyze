"""Limit-relative hint values on the CUR subset (rtprobe criteria 五 + amendment 3). Pure Python.

    python hint_rel.py gen      -> gen/cases_REL.json, gen/cases_REL_<arch>.txt, gen/rel_stats.json
    python hint_rel.py eval     -> rel_eval.json   (after run + compare_any on kernels_REL.json)
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "anyarch_dev_20261110" / "gen"))
import translate as TR  # noqa: E402  (constant translation of the previous round; also puts mutate_lib on the path)

ML = TR.ML
S = [1 << 52]  # known static values of TASK_SIZE_MAX (CUR: arm64 only)
KERNEL = {"riscv": "cur_riscv", "arm64": "cur_arm64", "x86_64": "cur_x86_64"}


def limit_of(probes, k):
    v = probes[k]["values"]
    m, u = int(v["mmap_top"], 16), int(v["uaccess_top"], 16)
    assert u in (m, m + 1), (k, hex(m), hex(u))
    return m


def main():
    mode = sys.argv[1]
    consts, vn, meta, lay, nrt, bases = TR.load()
    archs = consts["archs"]
    probes = json.loads((HERE / "probes.json").read_text())
    L = {a: limit_of(probes, KERNEL[a]) for a in archs}
    hint = {s + d: (s, d) for s in S for d in (-1, 0, 1)}
    sub = [c for c in meta["cases"] if any(t.startswith("i:") and int(t[2:], 16) in hint for t in c["args"])]
    if mode == "gen":
        fam, _ = TR.families(consts, vn, bases)
        conf = json.loads((CT / "anyarch_dev_20261110/gen/confirmed.json").read_text())["confirmed"]
        per, st = TR.translate_cases(sub, TR.table_of(fam, conf), archs)  # constants first (as in CURt)
        (HERE / "gen").mkdir(exist_ok=True)
        before = {a: ML.lines(per[a], lay, nrt, meta["NR_syscalls"])[a] for a in archs}
        changed = {a: 0 for a in archs}
        for a in archs:
            new = []
            for c in per[a]:
                args, ch = list(c["args"]), False
                for i, t in enumerate(args):
                    if t.startswith("i:") and int(t[2:], 16) in hint:
                        s, d = hint[int(t[2:], 16)]
                        nt = "i:%x" % (L[a] + d)
                        ch |= nt != t
                        args[i] = nt
                changed[a] += ch
                new.append(dict(c, args=args) if ch else c)
            per[a] = new
        for a in archs:
            ls = ML.lines(per[a], lay, nrt, meta["NR_syscalls"])[a]
            (HERE / "gen" / f"cases_REL_{a}.txt").write_text("\n".join(ls) + "\n", newline="\r\n")
            if a == "arm64":
                assert ls == before[a], "arm64 list must not change"
        (HERE / "gen" / "cases_REL.json").write_text(json.dumps({"group": "REL", "cases": sub}, indent=0))
        sc = {}
        for c in sub:
            sc[c["sc"]] = sc.get(c["sc"], 0) + 1
        st = {"limits": {a: format(L[a], "x") for a in archs}, "subset_cases": len(sub), "changed": changed,
              "by_syscall": dict(sorted(sc.items(), key=lambda x: -x[1]))}
        (HERE / "gen" / "rel_stats.json").write_text(json.dumps(st, indent=1))
        print(json.dumps(st))
    else:
        old = json.loads((CT / "anyarch_dev_20261110/runs/CURt/compare_any.json").read_text(encoding="utf8"))
        new = json.loads((HERE / "runs/REL/compare_any.json").read_text(encoding="utf8"))
        ids = [str(c["id"]) for c in sub]
        cases = {str(c["id"]): c for c in sub}
        so, sn = old["sets"]["cur_riscv"], new["sets"]["cur_riscv"]

        def summ(s):
            d, cl = {}, {}
            for i in ids:
                v = s["verdicts"].get(i, "same")
                d[v] = d.get(v, 0) + 1
            for a, c in s["clusters"].items():
                n = {k for k, m in c.items() if set(m) & set(ids)}
                if n:
                    cl[a] = sorted(n)
            return dict(sorted(d.items())), cl
        bo, co = summ(so)
        bn, cn = summ(sn)
        moves = {}
        for i in ids:
            a, b = so["verdicts"].get(i, "same"), sn["verdicts"].get(i, "same")
            if a != b:
                moves.setdefault(f"{a} -> {b}", []).append(i)
        det = [{"id": i, "move": k, "sc": cases[i]["sc"], "args": cases[i]["args"], "after": new["values"].get(i)}
               for k, v in sorted(moves.items()) for i in v]
        out = {"subset_cases": len(ids), "before": bo, "after": bn, "clusters_before": co, "clusters_after": cn,
               "moves": {k: len(v) for k, v in sorted(moves.items())}, "detail": det}
        (HERE / "rel_eval.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf8")
        for k in ("subset_cases", "before", "after", "clusters_before", "clusters_after", "moves"):
            print(k, json.dumps(out[k], ensure_ascii=False))
        for d in det:
            print(" ", d["id"], d["move"], d["sc"], d["args"])
            for kk, vv in (d["after"] or {}).items():
                print("      ", kk, vv[:110])


if __name__ == "__main__":
    main()
