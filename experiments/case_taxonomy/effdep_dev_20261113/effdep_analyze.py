"""Effect-dependency candidates, horizontal qualification, scores, suggestions (effdep criteria 五～八). WSL.

    python3 effdep_analyze.py <tree id>      tree id: CUR_riscv or a sample id (A043, X1, ...)
        reads /root/work/effdep/facts/{<id>_pre|CUR_riscv,CUR_arm64,CUR_x86_64}.json.gz, <id>_fix.json
        writes out/<id>.json (candidates, hits) and out/<id>_suggestions.md
"""
import glob
import gzip
import json
import math
import os
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
F = Path("/root/work/effdep/facts")
POOLS = sorted(glob.glob(str(CT / "boundary_audit_20261107/revised/*/*/symbols_runtime_*.json")))
GENERIC = ("include/linux/", "include/asm-generic/")
FORM_W = {"F1": 1, "F2": 2, "F3": 2}


def load(p):
    return json.load(gzip.open(p, "rt"))


def by_name(facts):
    out = {}
    for f in facts["functions"].values():
        out.setdefault(f["name"], []).append(f)
    return out


def impl_of(name, bn, arch_dir):
    """the implementation of interface `name` for one architecture: arch definition, else generic default"""
    defs = bn.get(name, [])
    a = [d for d in defs if d["file"].startswith(arch_dir)]
    if a:
        return a[0], "arch"
    g = [d for d in defs if d["file"].startswith(GENERIC)]
    if g:
        return g[0], "generic"
    return None, None


def effect(impl, bn, r):
    """criteria 六: 'effect' | 'none' | 'unknown' of implementation on resource r ('ret' or arg index)"""
    if impl is None:
        return "unknown"  # amendment 1: macro-only or no definition seen
    s = impl["summary"]
    if s["empty"]:
        return "none"
    if r == "ret":
        return "none" if s["const_ret"] else "effect"
    if s["const_ret"]:
        return "none"
    if r in s["writes"]:
        return "effect"
    for pi, callee, j in s["passes"]:
        if pi == r:
            for d in bn.get(callee, [])[:1]:
                if j in d["summary"]["writes"]:
                    return "effect"
    return "unknown"


def patch_names(cutoff):
    p = "/root/work/pgdev/patches_x86_arm64.json.gz"
    if not os.path.exists(p):
        return set()
    d = json.load(gzip.open(p, "rt"))
    return {h["func"] for c in d["commits"] if cutoff is None or c["cdate"] < cutoff for h in c["hunks"] if h.get("func")}


def fix_locations(parent, fix):
    """amendment 2: names of changed definitions from hunk headers (functions, macros, initialized variables)"""
    import re
    import subprocess
    diff = subprocess.run(["git", "-C", "/root/repos/linux", "diff", "-U0", parent, fix],
                          capture_output=True, text=True, errors="replace").stdout
    names = set()
    for l in diff.splitlines():
        m = re.match(r"^@@ [^@]* @@ (.*)", l)
        if m:
            h = m.group(1)
            ids = re.findall(r"([A-Za-z_]\w*)\s*\(", h)
            if ids:
                names.add(ids[-1] if not h.lstrip().startswith("#define") else ids[0])
            else:
                v = re.findall(r"([A-Za-z_]\w*)\s*(?:\[[^\]]*\]\s*)*(?:__\w+\s*)*=", h) or re.findall(r"([A-Za-z_]\w*)\s*\[", h)
                if v:
                    names.add(v[-1])
        m2 = re.match(r"^[-+]\s*#\s*define\s+([A-Za-z_]\w*)", l)
        if m2:
            names.add(m2.group(1))
    return sorted(names)


def main():
    tid = sys.argv[1]
    T = load(F / (f"{tid}_pre.json.gz" if tid != "CUR_riscv" else "CUR_riscv.json.gz"))
    A = load(F / "CUR_arm64.json.gz")
    X = load(F / "CUR_x86_64.json.gz")
    bnT, bnA, bnX = by_name(T), by_name(A), by_name(X)
    fix = json.load(open(F / f"{tid}_fix.json")) if tid != "CUR_riscv" else None
    cutoff = None
    if fix:
        cutoff = int(os.popen(f"git -C /root/repos/linux log -1 --format=%ct {fix['fix']}").read().strip() or 0) or None
    pnames = patch_names(cutoff)
    # interfaces (criteria 五)
    pool = set()
    for p in POOLS:
        for s in json.load(open(p)):
            if s.get("direction") == "public_to_arch" and s.get("definition_layer") == "arch" and s.get("kind") in ("function", "macro"):
                pool.add(s["name"])
    generic_def = {n for bn in (bnT, bnA, bnX) for n, ds in bn.items() if any(d["file"].startswith(GENERIC) for d in ds)}
    generic_def |= {n for fx in (T, A, X) for n, f in fx["macros"].items() if f.startswith(GENERIC)}
    arch_def = {n for n, ds in bnT.items() if any(d["file"].startswith("arch/riscv/") for d in ds)}
    arch_def |= {n for n, ds in bnA.items() if any(d["file"].startswith("arch/arm64/") for d in ds)}
    arch_def |= {n for n, ds in bnX.items() if any(d["file"].startswith("arch/x86/") for d in ds)}
    arch_def |= {n for fx, ad in ((T, "arch/riscv/"), (A, "arch/arm64/"), (X, "arch/x86/"))
                 for n, f in fx["macros"].items() if f.startswith(ad)}
    interfaces = pool | (generic_def & arch_def)
    common = [f for f in T["functions"].values() if not f["file"].startswith("arch/")]
    # interface has a return value if some call site uses it
    has_ret = {c[2] for f in T["functions"].values() for c in f["calls"] if c[4] not in ("discard", "macro")}
    ncalls = {}
    for f in common:
        for c in f["calls"]:
            if c[2] in interfaces:
                ncalls[c[2]] = ncalls.get(c[2], 0) + 1
    cands = []
    for f in common:
        for c in f["calls"]:
            off, line, I, bases, ret = c
            if I not in interfaces:
                continue
            later_uses = [u for u in f["uses"] if u[0] > off and u[1] != line]
            later_checks = [k for k in f["checks"] if k[0] > off]

            def first_unchecked(var):
                us = [u for u in later_uses if u[2] == var]
                if not us:
                    return None
                u = us[0]
                if any(var in k[2] and k[0] < u[0] for k in later_checks):
                    return None
                return u
            forms = []
            for k, R in enumerate(bases):
                if not R:
                    continue
                u = first_unchecked(R)
                if u:
                    forms.append(("F3", k, R, u))
                    if ret == "discard" and I in has_ret:
                        forms.append(("F1", k, R, u))
            if ret.startswith("="):
                v = ret[1:]
                u = first_unchecked(v)
                if u:
                    forms.append(("F2", "ret", v, u))
            if ret == "return":
                forms.append(("F3", "ret", "<return>", [off, line, "<return>", "return", None]))
            seen = set()
            for form, r, R, u in forms:
                if (r, form) in seen:
                    continue
                seen.add((r, form))
                eff = {}
                for arch, bn, ad in (("riscv", bnT, "arch/riscv/"), ("arm64", bnA, "arch/arm64/"), ("x86_64", bnX, "arch/x86/")):
                    impl, where = impl_of(I, bn, ad)
                    eff[arch] = {"effect": effect(impl, bn, r), "where": where,
                                 "loc": f"{impl['file']}:{impl['line']}" if impl else None}
                vals = [e["effect"] for e in eff.values()]
                qual = "effect" in vals and "none" in vals
                rar = 1 / math.log2(1 + ncalls.get(I, 1))
                P = 1.5 if (f["name"] in pnames or I in pnames) else 1.0
                score = FORM_W[form] * (3 if qual else 1) * rar * P
                cands.append({"fn": f["name"], "file": f["file"], "line": line, "interface": I, "resource": r,
                              "var": R, "form": form, "use": {"line": u[1], "kind": u[3], "callee": u[4]},
                              "horizontal": eff, "qualified": qual, "score": round(score, 4), "P": P})
    # merge forms per (fn, line, interface, resource): keep the highest score, record every form (amendment 1)
    best, forms_at = {}, {}
    for c in cands:
        k = (c["fn"], c["file"], c["line"], c["interface"], str(c["resource"]))
        forms_at.setdefault(k, set()).add(c["form"])
        if k not in best or c["score"] > best[k]["score"]:
            best[k] = c
    for k, c in best.items():
        c["forms"] = sorted(forms_at[k])
    cands = sorted(best.values(), key=lambda c: (-c["score"], c["file"], c["line"]))
    res = {"tree": tid, "interfaces": len(interfaces), "candidates": len(cands),
           "by_form": {f: sum(1 for c in cands if f in c["forms"]) for f in FORM_W},
           "qualified": sum(1 for c in cands if c["qualified"])}
    if fix:
        fx = set(fix_locations(fix["parent"], fix["fix"]))
        hits = [i for i, c in enumerate(cands) if c["fn"] in fx or c["interface"] in fx]
        ffiles = set(fix["files"])
        fhits = [i for i, c in enumerate(cands)
                 if c["file"] in ffiles or (c["horizontal"]["riscv"]["loc"] or ":").rsplit(":", 1)[0] in ffiles]
        res.update({"fix_functions": sorted(fx), "fix_functions_prep": fix["functions"], "fix_files": sorted(ffiles),
                    "located": bool(hits),
                    "qualified_hit": any(cands[i]["qualified"] for i in hits),
                    "first_hit_rank": hits[0] + 1 if hits else None,
                    "first_qualified_hit_rank": next((i + 1 for i in hits if cands[i]["qualified"]), None),
                    "file_located": bool(fhits),
                    "file_qualified_hit": any(cands[i]["qualified"] for i in fhits),
                    "first_file_hit_rank": fhits[0] + 1 if fhits else None,
                    "hits": [dict(cands[i], rank=i + 1) for i in hits[:10]],
                    "file_hits": [dict(cands[i], rank=i + 1) for i in fhits[:10]]})
    if tid == "CUR_riscv":
        q = [c for c in cands if c["qualified"]]
        rng = random.Random(20261113)
        res["review_sample"] = rng.sample(q, min(40, len(q)))
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    (out / f"{tid}.json").write_text(json.dumps({**res, "top": cands[:200]}, indent=1, ensure_ascii=False))
    lines = [f"# 人工分析建议：{tid}", "",
             f"接口 {res['interfaces']} 个；候选 {res['candidates']} 个（F1 {res['by_form']['F1']}、F2 {res['by_form']['F2']}、"
             f"F3 {res['by_form']['F3']}）；横向定性成立 {res['qualified']} 个。以下为前 50 条。", ""]
    for i, c in enumerate(cands[:50], 1):
        h = c["horizontal"]
        on = [a for a, e in h.items() if e["effect"] == "effect"]
        off = [a for a, e in h.items() if e["effect"] == "none"]
        res_txt = "返回值" if c["resource"] == "ret" else f"第 {c['resource'] + 1} 个实参 `{c['var']}`"
        lines += [f"## {i}. `{c['fn']}` 调用 `{c['interface']}`（{c['file']}:{c['line']}）", "",
                  f"- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 {'、'.join(c['forms'])}",
                  f"- 依据：调用后 {res_txt} 在第 {c['use']['line']} 行被直接使用（{c['use']['kind']}"
                  f"{'，传给 `' + c['use']['callee'] + '`' if c['use']['callee'] else ''}），其间没有检查；"
                  f"产生效果的架构：{'、'.join(on) or '无'}；不产生效果的架构：{'、'.join(off) or '无'}"
                  + ("（横向定性成立）" if c["qualified"] else ""),
                  "- 各架构实现：" + "；".join(f"{a} {e['where'] or '无实现'} {e['loc'] or ''} → {e['effect']}" for a, e in h.items()),
                  "- 为什么需要人看：本轮未做动态确认",
                  f"- 建议怎么查：对照{('、'.join(on) + ' 的实现') if on else '各架构实现'}，看公共层依赖的效果在 {'、'.join(off) or '其他架构'} 上是否由别处保证",
                  f"- 得分 {c['score']}" + ("（别的架构修过此处）" if c["P"] > 1 else ""), ""]
    (out / f"{tid}_suggestions.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k not in ("hits", "file_hits", "review_sample")}, ensure_ascii=False))
    if fix:
        for h in res["hits"][:3]:
            print("  hit", h["rank"], h["fn"], h["interface"], h["form"], h["qualified"], {a: e["effect"] for a, e in h["horizontal"].items()})


if __name__ == "__main__":
    main()
