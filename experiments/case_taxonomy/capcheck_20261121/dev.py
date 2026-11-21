"""capcheck criteria 三: dev acceptance on the 19 design roots + 6 legal controls. WSL.

    python3 dev.py [tag]     -> dev_<tag>.json (per root: targets, hit on parent, hit on fix), controls
Also importable: targets(fix) and hits(cands, targets) (used by the replay script).
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(HERE))
import capcheck as K  # noqa: E402
C = K.C

CAPRX = re.compile(r"\b(boot_cpu_has|static_cpu_has|cpu_feature_enabled|this_cpu_has|cpus_have_\w+|alternative_has_cap_\w+|system_supports_\w+|"
                   r"riscv_has_extension_(likely|unlikely)|riscv_isa_extension_available|has_vector|cpu_has_feature|mmu_has_feature|firmware_has_feature|"
                   r"radix_enabled|early_cpu_has|test_facility|MACHINE_HAS_\w+|cpu_has_\w+)\b|"
                   r"\b(arch_has_\w+|hugepages_supported|has_transparent_hugepage|can_set_direct_map|pgtable_l[45]_enabled|\w+_supported|\w+_available)\s*\(\s*\)")
CONTROLS = [  # criteria 三: (id, file, funcs (empty = any), cap (None = any))
    ("C1", "mm/secretmem.c", {"secretmem_fault"}, None),
    ("C2", "mm/hugetlb.c", {"hugetlb_init"}, None),
    ("C3", "arch/x86/crypto/aesni-intel_glue.c", set(), None),
    ("C4", "arch/arm64/kernel/ptrace.c", {"fpr_get", "fpr_set", "__fpr_get", "__fpr_set"}, None),
    ("C5", "arch/arm64/mm/hugetlbpage.c", set(), "hugepages_supported"),
    ("C6", "mm/hugetlb.c", {"size_to_hstate"}, None),
]


def git(*a):
    return subprocess.run(["git", "-C", K.REPO, *a], capture_output=True, text=True, errors="replace").stdout


def targets(fix):
    """{(path, func)} in fix^ whose body receives an added line with a capability predicate"""
    patch = git("show", "--format=", "--no-color", "-U0", fix)
    hunks, path = [], None
    cur = None
    for ln in patch.split("\n"):
        if ln.startswith("--- "):
            path = ln[6:] if ln.startswith("--- a/") else None
        elif ln.startswith("@@"):
            m = re.match(r"@@ -(\d+)(?:,(\d+))? \+", ln)
            cur = [path, int(m.group(1)), False] if m and path else None
            if cur:
                hunks.append(cur)
        elif ln.startswith("+") and not ln.startswith("+++") and cur and CAPRX.search(ln[1:]):
            cur[2] = True
    out = set()
    srcs = {}
    for p, start, hit in hunks:
        if not hit or not p.endswith(".c") and not p.endswith(".h"):
            continue
        if p not in srcs:
            srcs[p] = git("show", f"{fix}^:{p}")
        t = C.tokenize(C.strip(srcs[p]))
        for name, params, lo, hi in C.functions(t):
            if t[lo][1] - 1 <= start <= t[hi][1]:
                out.add((p, name))
                break
    return out


def hits(cands, tg):
    return [c for c in cands if (c["file"], c["func"]) in tg]


def main(tag):
    t0 = time.time()
    pos = json.loads((CT / "capsupply_20261121/design_positives.json").read_text(encoding="utf-8"))
    roots = {}
    for p in pos:
        roots.setdefault(p["root"], p)
    out = []
    for r, p in sorted(roots.items(), key=lambda kv: int(kv[0][1:])):
        fix = p["commit"]
        tg = targets(fix)
        par = K.run(fix + "^")
        h = hits(par["cands"], tg)
        aft = K.run(fix) if h else None
        ha = hits(aft["cands"], tg) if aft else []
        gone = [x for x in h if not any((y["file"], y["func"], y["op"], y["cap"]) == (x["file"], x["func"], x["op"], x["cap"]) for y in ha)]
        out.append({"root": r, "fix": fix, "family": p["family"], "targets": sorted(tg), "parent_cands": len(par["cands"]),
                    "hit": bool(h), "hits": h[:5], "gone_after_fix": len(gone), "hits_after_fix": len(ha)})
        print(r, fix, "targets", len(tg), "hit", bool(h), "cands", len(par["cands"]), round(time.time() - t0), "s", flush=True)
    cur = json.loads(Path("/root/work/capcheck/df2908090cda.json").read_text())
    ctl = []
    for cid, f, fns, cap in CONTROLS:
        rep = [c for c in cur["cands"] if c["file"] == f and (not fns or c["func"] in fns) and (cap is None or c["cap"] == cap)]
        ctl.append({"id": cid, "reported": bool(rep), "examples": rep[:3]})
    summ = {"roots": len(out), "strict_hits": sum(x["hit"] for x in out), "roots_with_targets": sum(bool(x["targets"]) for x in out),
            "hit_gone_after_fix": sum(1 for x in out if x["hit"] and x["gone_after_fix"]),
            "controls_reported": sum(c["reported"] for c in ctl), "secs": round(time.time() - t0)}
    (HERE / f"dev_{tag}.json").write_text(json.dumps({"summary": summ, "roots": out, "controls": ctl}, indent=1, ensure_ascii=False))
    print(json.dumps(summ))


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    main(sys.argv[1] if len(sys.argv) > 1 else "run1")
