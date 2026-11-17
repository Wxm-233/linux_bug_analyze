"""Per-arch values for the I1 tree-own object-like macros (criteria 二 I1, same probe as round 1 4.5). Runs in WSL.

    python3 macro_values2.py <group> <facts2.json.gz> -> /root/work/static2/values/<group>.json

Round-1 values (/root/work/semhint/values/<group>.json) are copied unchanged, so the baseline reproduces round 1;
only names not probed in round 1 are probed here (object-like macros defined under arch/riscv/ or
include/asm-generic/), with round 1's probe code (imported read-only from ../../semhint_dev_20261109/static).
"""
import gzip
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "semhint_dev_20261109" / "static"))
import macro_values as mv  # noqa: E402

ARCH_MAC_FILE = re.compile(r"(^|/)(arch/riscv/|include/asm-generic/)")


def main():
    group, facts = sys.argv[1], sys.argv[2]
    d = json.load(gzip.open(facts, "rt"))
    old = json.loads(Path(f"/root/work/semhint/values/{group}.json").read_text())
    known = set(old["riscv"])
    new = sorted(n for n, m in d["macros"].items()
                 if m.get("file") and ARCH_MAC_FILE.search(m["file"]) and not m["fl"] and n not in known)
    kinds = {n: "macro" for n in new}
    defhdr = {}
    for n in new:
        f = d["macros"][n]["file"] or ""
        m = re.match(r"(?:.*/)?(?:include/|arch/riscv/include/)(.*\.h)$", f)
        if m and not m.group(1).startswith(("generated/", "uapi/")):
            defhdr[n] = m.group(1)
    out = dict(old)
    out["i1_probed"] = len(new)
    chunks = [new[i:i + 60] for i in range(0, len(new), 60)]
    for arch, build in mv.BUILDS[group].items():
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
    os.makedirs("/root/work/static2/values", exist_ok=True)
    Path(f"/root/work/static2/values/{group}.json").write_text(json.dumps(out, indent=0))


if __name__ == "__main__":
    main()
