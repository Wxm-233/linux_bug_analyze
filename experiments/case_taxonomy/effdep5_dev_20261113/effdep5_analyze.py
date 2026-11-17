"""Vertical effect-dependency signal (effdep5 criteria 三, 四). WSL.

    python3 effdep5_analyze.py <tree id>     CUR_riscv or a sample id
        reads /root/work/effdep5/facts/<id>_pre.json.gz | CUR_riscv.json.gz, <id>_fix.json,
              /root/work/effdep3/scan_<id|CUR>.json.gz (same-revision definitions),
              /root/work/effdep/facts/CUR_{arm64,x86_64}.json.gz (names only, interface set as effdep2)
        writes out/<id>.json, out/<id>_suggestions.md
"""
import glob
import gzip
import json
import math
import os
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "effdep_dev_20261113"))
from effdep_analyze import fix_locations, patch_names  # noqa: E402  (read-only)

F5 = Path("/root/work/effdep5/facts")
F1 = Path("/root/work/effdep/facts")
S3 = Path("/root/work/effdep3")
POOLS = sorted(glob.glob(str(CT / "boundary_audit_20261107/revised/*/*/symbols_runtime_*.json")))
GENERIC = ("include/linux/", "include/asm-generic/")
WRITE_FN = re.compile(r"^(memset|__memset|memcpy|__memcpy|memmove|memzero_explicit|clear_page|clear_user_page|clear_highpage"
                      r"|\w*clear\w*|\w*zero\w*|copy_page|copy_highpage|copy_user_highpage|\w*_init|init_\w+|\w*_set|set_\w+)$")
CATS = {
    "tlb": re.compile(r"^(\w*flush_tlb\w*|\w*tlb_flush\w*|sfence_vma\w*|\w*tlbi\w*|arch_tlbbatch_\w+)$"),
    "cache": re.compile(r"^(\w*flush_(dcache|icache|cache)\w*|\w*dcache_(clean|inval)\w*|\w*icache_inval\w*|caches_clean_inval\w*)$"),
    "pgtable": re.compile(r"^(set_(pte|pmd|pud|p4d|pgd)\w*|__set_pte\w*|(pte|pmd|pud)_clear\w*|set_memory_\w+|\w*change_page_attr\w*"
                          r"|apply_to_page_range|\w*set_direct_map\w*)$"),
    "barrier": re.compile(r"^((smp_)?[rw]?mb|dsb|isb|fence\w*|\w*_mb__\w+)$"),
    "register": re.compile(r"^(register_\w+|list_add\w*|hlist_add\w*|rb_insert\w*|xa_store\w*|idr_alloc\w*)$"),
}
VALBIT = re.compile(r"^\w*_bits?$")
NOT_IF = re.compile(r"^([A-Z0-9_]+|assert|panic|static_assert|WARN\w*|BUG\w*)$")  # amendment 2.1
SWITCH_CONST = {"true", "false", "0", "1"}  # amendment 2.3
PROP = {"mem": "已写入（清零或初始化）", "tlb": "TLB 已刷新", "cache": "缓存已同步", "pgtable": "页表项已设置",
        "barrier": "写入已排序", "register": "已登记"}  # amendment 1


def load(p):
    return json.load(gzip.open(p, "rt"))


def by_name(facts):
    out = {}
    for f in facts["functions"].values():
        f["file"] = os.path.normpath(f["file"])
        out.setdefault(f["name"], []).append(f)
    return out


class Cats:
    def __init__(self, bn):
        self.bn, self.memo = bn, {}

    def own(self, f):
        c = set()
        if f["summary"]["writes"]:
            c.add("mem")
        for call in f["calls"]:
            n = call[2]
            if VALBIT.match(n):
                continue
            if WRITE_FN.match(n):
                c.add("mem")
            for k, rx in CATS.items():
                if rx.match(n):
                    c.add(k)
        return c

    def of(self, name, depth=3):
        key = (name, depth)
        if key in self.memo:
            return self.memo[key]
        self.memo[key] = set()
        out = set()
        if VALBIT.match(name):
            return out
        if WRITE_FN.match(name):
            out.add("mem")
        for k, rx in CATS.items():
            if rx.match(name):
                out.add(k)
        ds = self.bn.get(name, [])
        if ds:
            out |= self.own(ds[0])
            if depth > 0:
                for call in ds[0]["calls"]:
                    if call[2] != name:
                        out |= self.of(call[2], depth - 1)
        self.memo[key] = out
        return out


def horizontal(I, scan):
    """纵横: some arch has a trivial (own or generic default) definition, some arch a nontrivial one"""
    d = scan["defs"].get(I, {})
    eff = {}
    for a in scan["archs"]:
        eff[a] = d.get(a) or d.get("generic")
    triv = sorted(a for a, v in eff.items() if v == "trivial")
    non = sorted(a for a, v in eff.items() if v == "nontrivial")
    return bool(triv and non), triv, non


def main():
    tid = sys.argv[1]
    T = load(F5 / (f"{tid}_pre.json.gz" if tid != "CUR_riscv" else "CUR_riscv.json.gz"))
    A = load(F1 / "CUR_arm64.json.gz")
    X = load(F1 / "CUR_x86_64.json.gz")
    scan = load(S3 / f"scan_{'CUR' if tid == 'CUR_riscv' else tid}.json.gz")
    bnT, bnA, bnX = by_name(T), by_name(A), by_name(X)
    cats = Cats(bnT)
    fix = json.load(open(F5 / f"{tid}_fix.json")) if tid != "CUR_riscv" else None
    cutoff = None
    if fix:
        cutoff = int(os.popen(f"git -C /root/repos/linux log -1 --format=%ct {fix['fix']}").read().strip() or 0) or None
    pnames = patch_names(cutoff)
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
    scan_if = {n for n, d in scan["defs"].items() if "generic" in d and any(a != "generic" for a in d)}
    interfaces = pool | (generic_def & arch_def) | scan_if
    common = [f for f in T["functions"].values() if not f["file"].startswith("arch/")]
    ncalls = {}
    for f in common:
        for c in f["calls"]:
            if c[2] in interfaces:
                ncalls[c[2]] = ncalls.get(c[2], 0) + 1
    best, skipped_all, skipped_res = {}, {}, {}
    n_raw = 0
    for f in common:
        assigns = f.get("assigns", [])
        if not assigns:
            continue
        for c in f["calls"]:
            off, line, I = c[0], c[1], c[2]
            if I not in interfaces or NOT_IF.match(I):
                continue
            cg = set(c[5])
            for a in assigns:
                aoff, aline, v, const, ag = a
                if not (aoff > off and 0 <= aline - line <= 8 and set(ag) <= cg):
                    continue
                if const.strip() not in SWITCH_CONST:  # amendment 2.3
                    continue
                if any(k[1] == aline and v in k[2] for k in f["checks"]):  # amendment 2.2: loop variable
                    continue
                for e in f["calls"]:
                    if e[0] <= aoff or v not in e[5] or e[2] == I:
                        continue
                    ec = cats.of(e[2])
                    if not ec:
                        continue
                    n_raw += 1
                    qual, triv, non = horizontal(I, scan)
                    rar = 1 / math.log2(1 + ncalls.get(I, 1))
                    P = 1.5 if (f["name"] in pnames or I in pnames) else 1.0
                    score = 3 * rar * P * (2 if qual else 1)
                    k = (f["name"], f["file"], I)
                    skipped_all.setdefault(k, set()).add(e[2])
                    skipped_res.setdefault(k, set()).update(b for b in e[3] if b and b != v)
                    cand = {"fn": f["name"], "file": f["file"], "interface": I, "call_line": line,
                            "flag": v, "const": const, "assign_line": aline, "skipped": e[2], "skipped_line": e[1],
                            "skipped_cats": sorted(ec), "qualified": qual,
                            "resources": sorted({b for b in e[3] if b and b != v}),
                            "property": "、".join(PROP[x] for x in sorted(ec)), "trivial_archs": triv, "nontrivial_archs": non,
                            "score": round(score, 4), "P": P}
                    if k not in best or cand["score"] > best[k]["score"]:
                        best[k] = cand
    for k, c in best.items():
        c["skipped_all"] = sorted(skipped_all[k])  # presentation only
        c["resources"] = sorted(skipped_res[k])
    cands = sorted(best.values(), key=lambda x: (-x["score"], x["file"], x["call_line"]))
    res = {"tree": tid, "interfaces": len(interfaces), "raw_matches": n_raw, "candidates": len(cands),
           "qualified": sum(1 for c in cands if c["qualified"])}
    if fix:
        fx = set(fix_locations(fix["parent"], fix["fix"]))
        hits = [i for i, c in enumerate(cands) if c["fn"] in fx or c["interface"] in fx]
        res.update({"fix_functions": sorted(fx), "located": bool(hits),
                    "qualified_hit": any(cands[i]["qualified"] for i in hits),
                    "first_hit_rank": hits[0] + 1 if hits else None,
                    "hits": [dict(cands[i], rank=i + 1) for i in hits[:5]]})
    if tid == "CUR_riscv":
        q = [c for c in cands if c["qualified"]]
        pick = q if len(q) <= 40 else random.Random(20261113).sample(q, 40)
        res["review_sample"] = [(c["fn"], c["interface"]) for c in pick]
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    (out / f"{tid}.json").write_text(json.dumps({**res, "candidates_list": cands}, indent=1, ensure_ascii=False))
    L = [f"# 人工分析建议（纵向信号）：{tid}", "",
         f"接口 {res['interfaces']} 个；纵向候选 {res['candidates']} 个，其中有横向差异的 {res['qualified']} 个（只用于排序，不是判错依据）。以下为前 50 条。", ""]
    for i, c in enumerate(cands[:50], 1):
        L += [f"## {i}. `{c['fn']}` 调用 `{c['interface']}` 后跳过 `{c['skipped']}`（{c['file']}:{c['call_line']}）", "",
              "- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）",
              f"- 依赖性质：`{'、'.join(c['resources']) or '（资源未识别）'}` 在 `{c['fn']}` 之后被使用或发布之前，必须{c['property']}；"
              f"公共层在调用 `{c['interface']}` 后把 `{c['flag']}` 设为 `{c['const']}`，不再自己保证",
              f"- 动态阶段可检查：后续使用 `{'、'.join(c['resources']) or '该资源'}` 时，它是否{c['property']}（各架构分别检查性质，不比较架构间差异）",
              f"- 依据：第 {c['call_line']} 行调用 `{c['interface']}` 后，第 {c['assign_line']} 行把 `{c['flag']}` 设为 `{c['const']}`；"
              f"第 {c['skipped_line']} 行的 `{c['skipped']}`（{'+'.join(c['skipped_cats'])} 类效果）受 `{c['flag']}` 控制；"
              f"受它控制、有效果的调用共 {len(c['skipped_all'])} 个：{'、'.join('`' + x + '`' for x in c['skipped_all'][:6])}",
              f"- 横向：`{c['interface']}` 平凡定义的架构 {'、'.join(c['trivial_archs'][:8]) or '无'}；"
              f"非平凡的 {'、'.join(c['nontrivial_archs'][:8]) or '无'}" + ("（有横向差异，用于定向）" if c["qualified"] else ""),
              "- 为什么需要人看：本轮未做动态确认",
              f"- 建议怎么查：在平凡定义的架构上，`{c['interface']}` 是否产生了“{c['property']}”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反",
              f"- 得分 {c['score']}", ""]
    (out / f"{tid}_suggestions.md").write_text("\n".join(L) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k not in ("hits", "review_sample")}, ensure_ascii=False))
    for h in res.get("hits", [])[:3]:
        print("  hit", h["rank"], h["fn"], h["interface"], h["flag"], h["const"], h["skipped"], h["qualified"])


if __name__ == "__main__":
    main()
