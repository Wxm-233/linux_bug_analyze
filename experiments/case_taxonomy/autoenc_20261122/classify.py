"""autoenc criteria 二.2: classify every discovered interface on every build by typed wrappers that clang accepts. WSL.

    python3 classify.py [builds...]      -> sigs_<build>.json  ({name: [template, ...]})
One translation unit per build, one wrapper per line; a wrapper fails iff clang reports an error on its line (errors from macro bodies
are reported at the expansion line in the main file).
"""
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "swapsym_20261121"))
import swaparch as A  # noqa: E402  (registers the 14 header-only variants; imported, not modified)
S = A.S

BUILDS = ["riscv64", "rv32_abi", "x86_64", "i386", "i386_pae", "arm64", "ppc64le", "ppc64le_hash", "ppc64e", "ppc32s", "ppc44x", "ppc8xx",
          "s390", "loongarch", "mips32", "mips32xpa", "mips64", "arm", "arm_lpae", "hexagon"]
WORK = Path("/root/work/autoenc")
HDR = "#include <linux/mm.h>\n#include <linux/pgtable.h>\n#include <linux/swapops.h>\n#include <linux/leafops.h>\n"
T = ["pte_t", "pmd_t", "pud_t"]
E = ["swp_entry_t", "softleaf_t"]


def templates(name):
    """{template key: wrapper source with @W@ for the wrapper name}"""
    if name.startswith("PAGE_"):
        return {"prot": "pgprot_t @W@(void) { return @N@; }".replace("@N@", name)}
    out = {}
    for t in T:
        out[f"mod:{t}"] = f"{t} @W@({t} x) {{ return @N@(x); }}"
        out[f"obs:{t}"] = f"unsigned long long @W@({t} x) {{ return @N@(x); }}"
        out[f"cons:{t}"] = f"{t} @W@(unsigned long a, pgprot_t p) {{ return @N@(a, p); }}"
        for e in E:
            out[f"enc:{e}>{t}"] = f"{t} @W@({e} e) {{ return @N@(e); }}"
            out[f"dec:{t}>{e}"] = f"{e} @W@({t} x) {{ return @N@(x); }}"
    for e in E:
        out[f"scons1:{e}"] = f"{e} @W@(unsigned long a) {{ return @N@(a); }}"
        out[f"scons2:{e}"] = f"{e} @W@(unsigned long a, unsigned long b) {{ return @N@(a, b); }}"
        out[f"sobs:{e}"] = f"unsigned long long @W@({e} e) {{ return @N@(e); }}"
        out[f"smod:{e}"] = f"{e} @W@({e} e) {{ return @N@(e); }}"
    return {k: v.replace("@N@", name) for k, v in out.items()}


def classify(b, names):
    WORK.mkdir(parents=True, exist_ok=True)
    lines, where = [HDR], {}
    base = HDR.count("\n")
    for nm in names:
        if re.search(r"_val$", nm):
            continue                                   # raw value accessors are not interfaces of the encoding (criteria 二.2)
        for tk, tpl in templates(nm).items():
            w = f"EC_W{len(where)}"
            lines.append("static __attribute__((used)) " + tpl.replace("@W@", w) + "\n")   # static: kernel flags make missing prototypes an error
            where[base + len(where) + 1] = (nm, tk, w)
    p = WORK / f"probe_{b}.c"
    p.write_text("".join(lines))
    args, cwd = S.base_args(b)
    r = subprocess.run(args + ["-fsyntax-only", "-ferror-limit=0", "-fno-caret-diagnostics", str(p)], cwd=cwd, capture_output=True, text=True,
                       errors="replace")
    bad = set()
    for m in re.finditer(r"probe_" + re.escape(b) + r"\.c:(\d+):\d+: error:", r.stderr):
        bad.add(int(m.group(1)))
    sigs = {}
    for ln, (nm, tk, w) in where.items():
        if ln not in bad:
            sigs.setdefault(nm, []).append(tk)
    # softleaf_t may be a typedef of swp_entry_t: keep only the swp_entry_t spelling when both pass
    for nm, ts in sigs.items():
        sigs[nm] = sorted(set(t.replace("softleaf_t", "swp_entry_t") for t in ts))
    return sigs, len(where), len(bad)


def main(builds):
    names = sorted(json.loads((HERE / "names.json").read_text(encoding="utf-8"))["names"])
    for b in builds:
        if b in A.ARCHES or b == "ppc64le_hash":
            A.register(b)
        sigs, nw, nb = classify(b, names)
        (HERE / f"sigs_{b}.json").write_text(json.dumps(sigs, indent=1, ensure_ascii=False), encoding="utf-8")
        kinds = {}
        for ts in sigs.values():
            for t in ts:
                k = t.split(":")[0]
                kinds[k] = kinds.get(k, 0) + 1
        print(b, "wrappers", nw, "error lines", nb, "names with a signature", len(sigs), json.dumps(kinds), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:] or BUILDS)
