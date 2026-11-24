"""autoenc criteria 二.1: discover page-table / swap-entry interfaces from source text only (no hand lists). WSL.

    python3 discover.py [rev]      -> names.json
Rule (criteria 一.1): identifiers in the namespace below that are defined (macro or static inline) in >= 2 arch directories under
arch/*/include/asm/, plus public static inline functions of include/linux/{pgtable.h,swapops.h,leafops.h} in the same namespace.
"""
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = "/root/repos/linux"
NS = re.compile(r"^(pte_|pmd_|pud_|pfn_|__swp_|__pte_to_swp|__pmd_to_swp|swp_|softleaf_|make_|PAGE_)")
PUBLIC = ["include/linux/pgtable.h", "include/linux/swapops.h", "include/linux/leafops.h"]
DEF_MACRO = re.compile(r"^[ \t]*#[ \t]*define[ \t]+([A-Za-z_]\w*)(\(([^)]*)\))?", re.M)
DEF_INLINE = re.compile(r"^[ \t]*static[ \t]+(?:__always_inline[ \t]+|inline[ \t]+|__init[ \t]+)+(?:const[ \t]+)?[\w \t\*]*?\b([A-Za-z_]\w*)[ \t]*\(([^)]*)\)[ \t]*\n?\{",
                        re.M)


def git(*a):
    return subprocess.run(["git", "-C", SRC, *a], capture_output=True, text=True, errors="replace").stdout


def cat_files(rev, paths):
    p = subprocess.Popen(["git", "-C", SRC, "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    out, _ = p.communicate("".join(f"{rev}:{x}\n" for x in paths).encode())
    res, i = {}, 0
    for path in paths:
        j = out.index(b"\n", i)
        hdr = out[i:j].decode().split()
        if len(hdr) < 3 or hdr[1] != "blob":
            i = j + 1
            continue
        n = int(hdr[2])
        res[path] = out[j + 1:j + 1 + n].decode(errors="replace")
        i = j + 1 + n + 1
    return res


def params_of(text):
    if text is None:
        return None
    out = []
    for p in text.split(","):
        p = p.strip()
        if not p or p == "void":
            continue
        m = re.search(r"([A-Za-z_]\w*)\s*(\[[^\]]*\])?$", p)
        out.append(m.group(1) if m else p)
    return out


def scan(text):
    """{name: (kind, params, line)}"""
    res = {}
    for m in DEF_MACRO.finditer(text):
        nm = m.group(1)
        if NS.match(nm):
            res.setdefault(nm, ("macro", params_of(m.group(3)) if m.group(2) else None, text.count("\n", 0, m.start()) + 1))
    for m in DEF_INLINE.finditer(text):
        nm = m.group(1)
        if NS.match(nm):
            res.setdefault(nm, ("inline", params_of(m.group(2)), text.count("\n", 0, m.start()) + 1))
    return res


def main(rev):
    files = [p for p in git("ls-tree", "-r", "--name-only", rev, "arch").splitlines() if re.match(r"^arch/[^/]+/include/asm/.*\.h$", p)]
    blobs = cat_files(rev, files + PUBLIC)
    names = defaultdict(lambda: {"archs": set(), "defs": {}, "params": None, "kind": None, "public": None})
    for path in files:
        arch = path.split("/")[1]
        for nm, (kind, params, line) in scan(blobs.get(path, "")).items():
            d = names[nm]
            d["archs"].add(arch)
            d["defs"].setdefault(arch, f"{path}:{line}")
            if d["params"] is None and params is not None:
                d["params"], d["kind"] = params, kind
    pub = {}
    for path in PUBLIC:
        for nm, (kind, params, line) in scan(blobs.get(path, "")).items():
            pub[nm] = {"def": f"{path}:{line}", "params": params, "kind": kind}
    out = {}
    for nm, d in names.items():
        if len(d["archs"]) >= 2:
            out[nm] = {"archs": sorted(d["archs"]), "defs": d["defs"], "params": d["params"], "kind": d["kind"],
                       "public": pub.get(nm, {}).get("def")}
    for nm, d in pub.items():
        if nm not in out:
            out[nm] = {"archs": [], "defs": {}, "params": d["params"], "kind": d["kind"], "public": d["def"]}
    (HERE / "names.json").write_text(json.dumps({"rev": rev, "n_arch_files": len(files), "names": out}, indent=1, ensure_ascii=False),
                                     encoding="utf-8")
    narch = sum(1 for d in out.values() if d["archs"])
    print(json.dumps({"rev": rev, "arch_headers": len(files), "names": len(out), "arch_defined_ge2": narch, "public_only": len(out) - narch}))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "df2908090cda")
