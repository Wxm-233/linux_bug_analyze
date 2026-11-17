"""Per-arch values for the I1 tree-own object-like macros (criteria 二 I1, same probe as round 1 4.5). Runs in WSL.

    TARGET=<目标> python3 macro_values2.py <group> <facts2.json.gz> --base-values <values.json> --out <out.json>

Explicit base values are copied unchanged; only new object-like macros defined under arch/<target>/ or
include/asm-generic/ are probed here, using this directory's macro_values module.
"""
import gzip
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
import macro_values as mv
from settings import TARGET, ARCH_MAC_FILE, builds_for, require_values


def main():
    from cli import parse
    args = parse('macro2')
    group, facts = args.group, args.facts
    d = json.load(gzip.open(facts, "rt"))
    old = json.loads(Path(args.base_values).read_text())
    require_values(old)
    known = set(old[TARGET])
    new = sorted(n for n, m in d["macros"].items()
                 if m.get("file") and ARCH_MAC_FILE.search(m["file"]) and not m["fl"] and n not in known)
    kinds = {n: "macro" for n in new}
    defhdr = {}
    for n in new:
        f = d["macros"][n]["file"] or ""
        m = re.match(rf"(?:.*/)?(?:include/|arch/{TARGET}/include/)(.*\.h)$", f)
        if m and not m.group(1).startswith(("generated/", "uapi/")):
            defhdr[n] = m.group(1)
    out = dict(old)
    out["builds"] = builds_for(group)
    out["i1_probed"] = len(new)
    chunks = [new[i:i + 60] for i in range(0, len(new), 60)]
    for arch, build in builds_for(group).items():
        vals = dict(old[arch])
        with ThreadPoolExecutor(12) as ex:
            parts = list(ex.map(lambda c: mv.probe(build, c, kinds), chunks))
        add = {}
        for p, err in parts:
            if err:
                print(arch, "HEADER ERROR", err[-400:])
                sys.exit(3)
            add.update(p)
        byhdr = {}
        for n, v in add.items():
            if v == "undefined" and defhdr.get(n):
                byhdr.setdefault(defhdr[n], []).append(n)

        def p2(item):
            h, ns = item
            r, err = mv.probe(build, ns, kinds, h)
            return ns, r if not err else {}
        with ThreadPoolExecutor(12) as ex:
            for ns, r in ex.map(p2, byhdr.items()):
                for n in ns:
                    if r.get(n) not in (None, "undefined"):
                        add[n] = r[n]
        vals.update(add)
        out[arch] = vals
        st = {}
        for n in new:
            v = add.get(n)
            k = v if isinstance(v, str) else "const"
            st[k] = st.get(k, 0) + 1
        print(group, arch, "new", len(new), st, "VA_USER_SV39", vals.get("VA_USER_SV39"))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=0))


if __name__ == "__main__":
    main()
