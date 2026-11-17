"""xvdom criteria 二: extended encoding probe (new input classes: none, present variants; new interface groups S, MG, MS).
Reuses encrank's prepared build dirs /root/work/encprobe/<arch> (no kernel build). WSL.

    python3 probe2.py            -> ctors.json, encoding2.json
Phase 1 compiles every input-class constructor on its own (to know which classes exist per arch);
phase 2 compiles one file per (level, interface, class group) with the available constructors only.
"""
import json
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "encrank_20261115"))
import probe as E  # noqa: E402  (read-only import of encrank's probe: kinds, mods, arch list)

SRC, W, ARCHS, P = E.SRC, E.W, E.ARCHS, E.P
INC = ["#include <linux/mm.h>", "#include <linux/swapops.h>", "#include <linux/leafops.h>", "#include <linux/pgtable.h>",
       "#include <linux/userfaultfd_k.h>"]

# ---- input classes: name -> (preprocessor condition, constructor)
def classes(level):
    out = {}
    kinds, mods = (E.PTE_KINDS, E.PTE_MODS) if level == "pte" else (E.PMD_KINDS, E.PMD_MODS)
    npcond = "1" if level == "pte" else "defined(CONFIG_ARCH_HAS_PMD_SOFTLEAVES)"
    for k, (cond, cons) in kinds.items():
        for m, mf in mods.items():
            out[f"np.{k}.{m}"] = (f"({cond}) && {npcond}", f"{mf}({cons})" if mf else cons)
    out["none"] = ("1", f"__{level}(0)")
    if level == "pte":
        base, pc = f"pfn_pte({P}, PAGE_SHARED)", "1"
    else:
        base, pc = f"pmd_mkhuge(pfn_pmd({P}, PAGE_SHARED))", "defined(CONFIG_TRANSPARENT_HUGEPAGE)"
    L = level
    pres = {"plain": base, "dirty": f"{L}_mkdirty({base})", "young": f"{L}_mkyoung({base})",
            "write": f"{L}_mkwrite_novma({base})", "special": f"{L}_mkspecial({base})",
            "sd": f"{L}_mksoft_dirty({base})", "uffd": f"{L}_mkuffd({base})",
            "all": f"{L}_mkuffd({L}_mksoft_dirty({L}_mkspecial({L}_mkwrite_novma({L}_mkyoung({L}_mkdirty({base}))))))",
            "protnone": f"{L}_modify({base}, PAGE_NONE)"}
    for v, c in pres.items():
        out[f"pr.{v}"] = (pc, c)
    return out


# ---- interface groups
R = {"pte": [a for a in E.PTE_ACC if a != "MKOLD"], "pmd": [a for a in E.PMD_ACC if a != "MKOLD"]}
S = {"pte": ["swp_soft_dirty", "swp_exclusive", "swp_uffd"], "pmd": ["swp_soft_dirty", "swp_uffd"]}
MG = {lv: ["mkold", "mkyoung", "mkdirty", "mkclean", "wrprotect", "mkwrite_novma", "mksoft_dirty", "clear_soft_dirty",
           "mkuffd", "clear_uffd", "mkspecial"] for lv in ("pte", "pmd")}
MS = {"pte": ["swp_mksoft_dirty", "swp_clear_soft_dirty", "swp_mkexclusive", "swp_clear_exclusive", "swp_mkuffd", "swp_clear_uffd"],
      "pmd": ["swp_mksoft_dirty", "swp_clear_soft_dirty", "swp_mkuffd", "swp_clear_uffd"]}
RT = {"pte": [("swp_mksoft_dirty", "swp_clear_soft_dirty"), ("swp_mkexclusive", "swp_clear_exclusive"), ("swp_mkuffd", "swp_clear_uffd")],
      "pmd": [("swp_mksoft_dirty", "swp_clear_soft_dirty"), ("swp_mkuffd", "swp_clear_uffd")]}


def plan(level):
    """list of (group, acc, class prefix filter, test(cls)->expr or None)"""
    L, out = level, []
    for a in R[level]:
        def t(c, a=a):
            if a == "pfn":
                k = c.split(".")[1] if c.startswith("np.") else None
                return f"({L}_pfn(e) == {P})" if k in E.HAS_PFN else None
            return f"!!{L}_{a}(e)"
        out.append(("R", a, ("np.", "none"), t))
    for a in S[level]:
        out.append(("S", a, ("pr.", "none", "np."), lambda c, a=a: f"!!{L}_{a}(e)"))
    for a in MG[level]:
        out.append(("MG", a, ("np.", "none"), lambda c, a=a: f"({L}_val({L}_{a}(e)) != {L}_val(e))"))
    for a in MS[level]:
        out.append(("MS", a, ("pr.", "none"), lambda c, a=a: f"({L}_val({L}_{a}(e)) != {L}_val(e))"))
    for mk, cl in RT[level]:
        out.append(("RT", f"{mk}+{cl}", ("np.",),
                    lambda c, mk=mk, cl=cl: f"({L}_val({L}_{cl}({L}_{mk}(e))) == {L}_val(e))" if c.endswith(".plain") else None))
    return out


def fname(s):
    return re.sub(r"[^A-Za-z0-9_]", "_", s)


def compile_dir(arch, m, names):
    o = W / arch
    (m / "Kbuild").write_text("obj-m := " + " ".join(f"{n}.o" for n in names) + "\nccflags-y += -Wno-missing-prototypes -Wno-error\n")
    cmd = ["make", "-C", SRC, f"O={o}", f"ARCH={ARCHS[arch]}", "LLVM=1", f"M={m}", "-k", "-j6"] + [f"{n}.ll" for n in names]
    log = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    (m / "build.log").write_text(log.stdout + log.stderr)


def read_ll(path):
    txt = path.read_text(errors="replace")
    got = {}
    for fm in re.finditer(r"define [^@]*@probe__(\w+)\(\)[^{]*\{\n(.*?)\n\}", txt, re.S):
        body = [l.strip() for l in fm.group(2).split("\n") if l.strip()
                and not re.match(r"(tail )?call void @(llvm\.dbg\.\w+|_mcount|__fentry__|mcount)\(", l.strip())]
        mm = re.fullmatch(r"ret i32 (\d+)(, !dbg !\d+)?", body[-1]) if body else None
        got[fm.group(1)] = int(mm.group(1)) if (mm and len(body) == 2) else "unknown"
    return got


def run_arch(arch):
    m1, m2 = W / f"xv1_{arch}", W / f"xv2_{arch}"
    for m in (m1, m2):
        shutil.rmtree(m, ignore_errors=True)
        m.mkdir(parents=True)
    # phase 1: constructors
    cls = {lv: classes(lv) for lv in ("pte", "pmd")}
    names, idx = [], {}
    for lv, cs in cls.items():
        for c, (cond, cons) in cs.items():
            n = fname(f"c__{lv}__{c}")
            (m1 / f"{n}.c").write_text("\n".join(INC + [f"#if {cond}", f"int probe__x(void) {{ {lv}_t e = {cons}; return {lv}_val(e) == 1; }}",
                                                         "#endif"]) + "\n")
            names.append(n)
            idx[n] = (lv, c)
    compile_dir(arch, m1, names)
    avail = {"pte": [], "pmd": []}
    for n, (lv, c) in idx.items():
        ll = m1 / f"{n}.ll"
        if ll.exists() and "probe__x" in ll.read_text(errors="replace"):
            avail[lv].append(c)
    # phase 2: probes
    names, idx = [], {}
    for lv in ("pte", "pmd"):
        for grp, acc, pref, test in plan(lv):
            buckets = {}
            for c in avail[lv]:
                if not c.startswith(pref):
                    continue
                key = "np" if c.startswith("np.") else c.split(".")[0]
                buckets.setdefault(key, []).append(c)
            for key, cs in buckets.items():
                lines = list(INC)
                for c in cs:
                    te = test(c)
                    if te is None:
                        continue
                    cond, cons = cls[lv][c]
                    lines += [f"#if {cond}", f"int probe__{fname(c)}(void) {{ {lv}_t e = {cons}; return {te}; }}", "#endif"]
                if len(lines) == len(INC):
                    continue
                n = fname(f"p__{lv}__{grp}__{acc}__{key}")
                (m2 / f"{n}.c").write_text("\n".join(lines) + "\n")
                names.append(n)
                idx[n] = (lv, grp, acc, {fname(c): c for c in cs})
    compile_dir(arch, m2, names)
    res, fails = {}, 0
    for n, (lv, grp, acc, back) in idx.items():
        cell = res.setdefault(lv, {}).setdefault(grp, {}).setdefault(acc, {})
        ll = m2 / f"{n}.ll"
        if not ll.exists():
            fails += 1
            cell.setdefault("_unavailable", []).append(n.rsplit("__", 1)[1])
            continue
        for k, v in read_ll(ll).items():
            cell[back.get(k, k)] = v
    return arch, avail, res, fails, len(names)


def main():
    enc, ctors = {}, {}
    with ThreadPoolExecutor(4) as ex:
        for arch, avail, res, fails, total in ex.map(run_arch, ARCHS):
            enc[arch], ctors[arch] = res, avail
            print(arch, "classes", {k: len(v) for k, v in avail.items()}, "files", total, "unavailable", fails, flush=True)
    (HERE / "ctors.json").write_text(json.dumps(ctors, indent=1))
    (HERE / "encoding2.json").write_text(json.dumps(enc, indent=1))


if __name__ == "__main__":
    main()
