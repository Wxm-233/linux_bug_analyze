"""pgassert amendment 1: arm64 defconfig + three header-only variants, reusing evalpg's interpreter. WSL.

    python3 evalarm.py run [builds...]      -> eval_<build>.json
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import evalpg as E  # noqa: E402
I = E.I

VARIANTS = {"arm64_16k": "/root/work/pgassert/cfg_arm64_16k", "arm64_64k": "/root/work/pgassert/cfg_arm64_64k",
            "arm64_pa48": "/root/work/pgassert/cfg_arm64_pa48"}
PAGE = {"arm64": 12, "arm64_16k": 14, "arm64_64k": 16, "arm64_pa48": 12}
PA = {"arm64": 52, "arm64_16k": 52, "arm64_64k": 52, "arm64_pa48": 48}
I.BUILDS.update(VARIANTS)
for b in PAGE:
    E.LONGW[b] = 64
    E.PHYS_BITS[b] = PA[b]
    E.PROTMAP_TU[b] = "arch/arm64/mm/mmap.c"
    E.PROTMAP_NOTE[b] = "保护值取四套：静态初值、EPAN 调整（VM_EXEC 两项为 PAGE_EXECONLY）、LPA2 调整（清 PTE_SHARED）、两者都调整"

_orig_ccdb = I.ccdb


def ccdb(d):
    """variants reuse arm64 defconfig compile commands, executed in the variant's output directory"""
    if d in VARIANTS.values():
        base = _orig_ccdb(I.BUILDS["arm64"])
        return {f: dict(e, directory=d) for f, e in base.items()}
    return _orig_ccdb(d)


I.ccdb = ccdb
E.I.ccdb = ccdb

_orig_protmap = E.protmap
_orig_synth = E.synth


def synth(assertions, binding=None, cfg=None):
    src, names = _orig_synth(assertions, binding, cfg)
    src += "pgprot_t P_execonly(void) { return PAGE_EXECONLY; }\nunsigned long P_shared(void) { return PTE_SHARED; }\n"
    return src, names


E.synth = synth
_CUR = {}


def protmap(b):
    base = _orig_protmap(b)
    funcs = _CUR.get("funcs") or {}
    it = E.Interp(funcs, 64, {})
    execonly = it.call("P_execonly", []) if "P_execonly" in funcs else None
    shared = it.call("P_shared", []) if "P_shared" in funcs else None
    if execonly is None or shared is None:
        raise E.Unsupported("PAGE_EXECONLY / PTE_SHARED not evaluated")
    ex = execonly if isinstance(execonly, dict) else {"_0": execonly}
    sets = [base]
    epan = [dict(v) for v in base]
    epan[4], epan[12] = dict(ex), dict(ex)
    sets.append(epan)
    if E.config_of(b).get("ARM64_LPA2"):
        def clr(lst):
            return [{"_0": E.b_and(v["_0"], E.b_not(shared))} for v in lst]
        sets += [clr(base), clr(epan)]
    return [v for s in sets for v in s]


E.protmap = protmap
_orig_dump = E.dump_unit


def dump_unit(b, path, filters):
    got = _orig_dump(b, path, list(filters) + (["P_"] if "A_" in filters else []))
    if "A_" in filters:
        _CUR["funcs"] = got
    else:
        _CUR.setdefault("funcs", {}).update(got)
    return got


E.dump_unit = dump_unit


def run(builds):
    inv = json.loads((HERE / "inventory.json").read_text(encoding="utf-8"))
    for b in builds:
        if b not in inv["binding"]:
            inv["binding"][b] = inv["binding"]["arm64"]       # variants share arm64's helper binding
    (HERE / "inventory_arm64.json").write_text(json.dumps(inv, indent=1, ensure_ascii=False))
    orig_inv = HERE / "inventory.json"
    saved = orig_inv.read_text(encoding="utf-8")
    try:
        orig_inv.write_text(json.dumps(inv, indent=1, ensure_ascii=False), encoding="utf-8")
        out = {}
        for b in builds:
            E.PAGE_SHIFT = PAGE[b]
            _CUR.clear()
            out.update(E.run([b]))
        return out
    finally:
        orig_inv.write_text(saved, encoding="utf-8")


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    if sys.argv[1] == "run":
        print(run(sys.argv[2:] or ["arm64", "arm64_16k", "arm64_64k", "arm64_pa48"]))
