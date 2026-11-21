"""Debug helper (dev only): show per-implementation status for functions / ops groups on a cached facts file. WSL.

    python3 debug.py <rev12> name <func> [...]
    python3 debug.py <rev12> ops <struct> <member>
"""
import gzip
import pickle
import sys
from collections import defaultdict

import effzero as E


def main():
    rev = sys.argv[1]
    data = pickle.load(gzip.open(f"{E.WORK}/facts_{rev}.pkl.gz"))
    defs = defaultdict(list)
    ops = defaultdict(list)
    for p, f in data["files"].items():
        for d in f["fns"]:
            defs[d["n"]].append(d)
        for T, m, fn, line in f["ops"]:
            ops[(T, m)].append((p, fn))
    ix = E.Index(data["files"])
    ret, pzs, path_zero, _ = E.summaries(data["files"], ix)
    if sys.argv[2] == "name":
        names = sys.argv[3:]
    else:
        lst = ops[(sys.argv[3], sys.argv[4])]
        print("ops members:", len(lst))
        names = sorted({fn for _, fn in lst})
    for n in names:
        print("==", n)
        for d in defs.get(n, []):
            st, bad = E.impl_status(d, path_zero)
            print(f"  {d['f']}:{d['l']} static={d['st']} rk={d['rk']} unknown={d['unknown']} status={st} ret={ret.get(d['id'])} pz={pzs.get(d['id'])} fw={d.get('fw', [])[:6]}")
            for r in d["rets"][:6]:
                print("     ret", r[0], r[1], "->", path_zero(r[0], r[1], d["f"]), list(r[2])[-2:], r[3])
            print("     pz", d["pz"][:4], "req", [(r[0], r[2]) for r in d.get("req", [])][:4], "e2", d["e2"][:2], "e3", d["e3"][:3])


if __name__ == "__main__":
    main()
