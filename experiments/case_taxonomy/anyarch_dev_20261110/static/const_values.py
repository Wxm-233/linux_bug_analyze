"""Per-architecture values of the interface constants compared with syscall parameters (anyarch criteria 三).
Runs in WSL.

    python3 const_values.py CUR  -> ../gen/consts_CUR.json

hints4.py (casemodel round) is loaded read-only and patched in memory so that its vocabulary loop also records the
macro names on the constant side of each comparison; the vocabulary itself must stay identical (asserted).
"""
import gzip
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parents[1]
H4 = CT / "casemodel_dev_20261110" / "static" / "hints4.py"
sys.path.insert(0, str(CT / "semhint_dev_20261109" / "static"))
import macro_values as mv  # noqa: E402

PATCHES = [
    ("    vocab = {}\n    for sc, eusr in sorted(entries.items()):",
     "    vocab = {}\n    vnames = {}\n    for sc, eusr in sorted(entries.items()):"),
    ("        voc = {}\n        for u, m in maps.items():",
     "        voc = {}\n        vn = {}\n        for u, m in maps.items():"),
    ('                            e = voc.setdefault(p, {"eq": set(), "bits": set()})\n',
     '                            e = voc.setdefault(p, {"eq": set(), "bits": set()})\n'
     '                            for x in c["sides"][b]["items"]:\n'
     '                                if x.startswith("#"):\n'
     '                                    vn.setdefault(p, {})[x[1:]] = min(vn.get(p, {}).get(x[1:], 99), depth[u])\n'),
    ("        if voc:\n            vocab[sc] = ",
     "        if vn:\n            vnames[sc] = {str(p): dict(sorted(v.items())) for p, v in vn.items() if v}\n"
     "        if voc:\n            vocab[sc] = "),
    ('"vocab": vocab,', '"vocab": vocab, "vocab_names": vnames,'),
]


def load_hints():
    src = H4.read_text()
    for a, b in PATCHES:
        assert src.count(a) == 1, a
        src = src.replace(a, b)
    ns = {"__file__": str(H4), "__name__": "hints4_patched"}
    exec(compile(src, str(H4), "exec"), ns)
    return ns["run"]


def header_of(f):
    """header to include so that every architecture sees its own definition"""
    m = re.match(r"(?:.*/)?(?:arch/[^/]+/include/|include/)(.*\.h)$", f or "")
    if not m:
        return None
    h = m.group(1)
    if h.startswith("generated/"):
        return None
    h = re.sub(r"^uapi/", "", h)
    return re.sub(r"^asm-generic/", "asm/", h)


def main():
    g = sys.argv[1]
    assert g == "CUR", "source trees of the sample groups were removed; only CUR is supported"
    facts = json.load(gzip.open(f"/root/work/casemodel/facts/{g}.json.gz", "rt"))
    vals = json.loads(Path(f"/root/work/static2/values/{g}.json").read_text())
    h = load_hints()(facts, vals, {"I1", "I2", "I3", "I4"})
    old = json.loads((CT / "casemodel_dev_20261110" / "gen" / f"vocab_{g}.json").read_text())["vocab"]
    assert h["vocab"] == old, "patched hints4 changed the vocabulary"
    M = facts["macros"]
    (HERE.parent / "gen").mkdir(exist_ok=True)
    (HERE.parent / "gen" / f"vocab_names_{g}.json").write_text(json.dumps(
        {"entries": h["entries"], "vocab_names": h["vocab_names"],
         "macro_files": {n: M[n].get("file") for ps in h["vocab_names"].values() for ns in ps.values() for n in ns
                         if n in M}}))

    def expand(n, seen):
        if n in seen or n not in M:
            return
        seen.add(n)
        for b in M[n].get("body") or []:
            expand(b, seen)

    per = {}
    for sc, ps in h["vocab_names"].items():
        for p, ns in ps.items():
            s = set()
            for n in ns:
                expand(n, s)
            per.setdefault(sc, {})[p] = sorted(n for n in s if not M[n]["fl"])
    names = sorted({n for ps in per.values() for ns in ps.values() for n in ns})
    kinds = {n: "macro" for n in names}
    hdr = {n: header_of(M[n].get("file")) for n in names}
    values, st = {}, {}
    for arch, build in mv.BUILDS[g].items():
        chunks = [names[i:i + 60] for i in range(0, len(names), 60)]
        with ThreadPoolExecutor(12) as ex:
            parts = list(ex.map(lambda c: mv.probe(build, c, kinds), chunks))
        got = {}
        for p, err in parts:
            if err:
                print(arch, "HEADER ERROR", err[-400:])
                sys.exit(3)
            got.update(p)
        byhdr = {}
        for n, v in got.items():
            if v == "undefined" and hdr.get(n):
                byhdr.setdefault(hdr[n], []).append(n)

        def p2(item):
            hh, ns = item
            r, err = mv.probe(build, ns, kinds, hh)
            return ns, (r if not err else {})
        with ThreadPoolExecutor(12) as ex:
            for ns, r in ex.map(p2, byhdr.items()):
                for n in ns:
                    if r.get(n) not in (None, "undefined"):
                        got[n] = r[n]
        values[arch] = got
        c = {}
        for v in got.values():
            k = v if isinstance(v, str) else "const"
            c[k] = c.get(k, 0) + 1
        st[arch] = c
    archs = list(values)
    div = {n: {a: values[a][n] for a in archs} for n in names
           if all(isinstance(values[a].get(n), int) for a in archs) and len({values[a][n] for a in archs}) > 1}
    ref = archs[0]  # facts come from this architecture's build
    assert ref == "riscv"
    table, ambiguous = {}, {}
    for sc, ps in per.items():
        for p, ns in ps.items():
            dn = [n for n in ns if n in div]
            if not dn:
                continue
            byref = {}
            for n in dn:
                byref.setdefault(div[n][ref], []).append(n)
            bits, whole = {}, {}
            for rv, nn in byref.items():
                if len({tuple(div[n][a] for a in archs) for n in nn}) > 1:
                    ambiguous.setdefault(f"{sc}/{p}", []).append(nn)
                    continue
                n = nn[0]
                single = rv and rv & (rv - 1) == 0
                if single and all(div[n][a] and div[n][a] & (div[n][a] - 1) == 0 for a in archs):
                    bits[format(rv, "x")] = {"name": "|".join(nn), **{a: format(div[n][a], "x") for a in archs}}
                elif not single:
                    whole[format(rv, "x")] = {"name": "|".join(nn), **{a: format(div[n][a], "x") for a in archs}}
            if bits or whole:
                table.setdefault(sc, {})[p] = {"bits": bits, "whole": whole}
    out = {"group": g, "archs": archs, "ref": ref,
           "stats": {"names": len(names), "probe": st, "divergent": len(div),
                     "params_with_names": sum(len(ps) for ps in per.values()),
                     "table_params": sum(len(ps) for ps in table.values()), "table_syscalls": len(table),
                     "ambiguous": len(ambiguous)},
           "divergent": {n: {a: format(v, "x") for a, v in d.items()} for n, d in sorted(div.items())},
           "files": {n: M[n].get("file") for n in sorted(div)},
           "expanded": {sc: {p: [n for n in ns if n in div] for p, ns in ps.items() if any(n in div for n in ns)}
                        for sc, ps in per.items() if any(n in div for ns in ps.values() for n in ns)},
           "ambiguous": ambiguous, "table": table}
    (HERE.parent / "gen").mkdir(exist_ok=True)
    (HERE.parent / "gen" / f"consts_{g}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out["stats"]))
    for n in ("O_DIRECT", "O_DIRECTORY", "O_NOFOLLOW", "O_LARGEFILE", "MAP_GROWSDOWN", "SO_RCVBUF"):
        print(n, {a: (hex(values[a][n]) if isinstance(values[a].get(n), int) else values[a].get(n)) for a in archs})


if __name__ == "__main__":
    main()
