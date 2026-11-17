"""Effect dependency, third version: effdep2 (I1-I7, amendments 1-2) + effdep3 J1-J4. WSL.

    python3 effdep3_analyze.py <tree id>     CUR_riscv or a sample id
        reads /root/work/effdep/facts/*, /root/work/effdep3/scan_<id|CUR>.json.gz
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
from effdep_analyze import fix_locations, patch_names, impl_of  # noqa: E402  (previous round, read-only)

F = Path("/root/work/effdep/facts")
S = Path("/root/work/effdep3")
POOLS = sorted(glob.glob(str(CT / "boundary_audit_20261107/revised/*/*/symbols_runtime_*.json")))
GENERIC = ("include/linux/", "include/asm-generic/")
FORM_W = {"F1": 1, "F2": 2, "F3": 2}
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
QF = {"Q-特性": 4, "Q-多数": 3, "Q-类别": 2, None: 1, "特性专有": 0.5, "特性未开启": 0.3, "有意空实现": 0.5, "已判断": 0.5}
QUAL = ("Q-特性", "Q-多数", "Q-类别")
CAP = re.compile(r"^(arch_has_\w+|\w*supports?_\w*|\w*_enabled|\w*_available|static_branch_\w+|static_key_\w+|\w*cpu_has\w*"
                 r"|\w*has_feature\w*|IS_ENABLED)$")
VALBIT = re.compile(r"^\w*_bits?$")  # J3


def load(p):
    return json.load(gzip.open(p, "rt"))


def by_name(facts):
    out = {}
    for f in facts["functions"].values():
        f["file"] = os.path.normpath(f["file"])  # I7
        out.setdefault(f["name"], []).append(f)
    return out


def const_ret(f):
    return f["summary"]["const_ret"] and not f["checks"]  # I2


class Cats:
    """I1: effect categories of a function and its call closure (depth 3) within one tree"""
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
        ds = self.bn.get(name, [])
        out = set()
        if ds:
            f = ds[0]
            out |= self.own(f)
            if depth > 0:
                for call in f["calls"]:
                    if call[2] != name:
                        out |= self.of(call[2], depth - 1)
        self.memo[key] = out
        return out


def effect(impl, bn, r, cats):
    if impl is None:
        return "unknown", set()
    s = impl["summary"]
    cs = cats.of(impl["name"])
    if s["empty"]:
        return "none", cs
    if r == "ret":
        return ("none" if const_ret(impl) else "effect"), cs
    if const_ret(impl):
        return "none", cs
    if r in s["writes"]:
        return "effect", cs
    for pi, callee, j in s["passes"]:
        if pi == r:
            for d in bn.get(callee, [])[:1]:
                if j in d["summary"]["writes"]:
                    return "effect", cs
    return ("effect:" + "+".join(sorted(cs)) if cs else "unknown"), cs


def arch_status(name, scan):
    """I3: (riscv lacks?, n_impl, impl archs) from same-revision source"""
    d = scan["defs"].get(name, {})
    impl = sorted(a for a, v in d.items() if a not in ("riscv", "generic") and v == "nontrivial")
    rv = d.get("riscv")
    if rv is None:
        lacks = d.get("generic") in (None, "trivial")
    else:
        lacks = rv == "trivial"
    return lacks, len(impl), impl


def main():
    tid = sys.argv[1]
    T = load(F / (f"{tid}_pre.json.gz" if tid != "CUR_riscv" else "CUR_riscv.json.gz"))
    A = load(F / "CUR_arm64.json.gz")
    X = load(F / "CUR_x86_64.json.gz")
    scan = load(S / f"scan_{'CUR' if tid == 'CUR_riscv' else tid}.json.gz")
    bnT, bnA, bnX = by_name(T), by_name(A), by_name(X)
    cT, cA, cX = Cats(bnT), Cats(bnA), Cats(bnX)
    fix = json.load(open(F / f"{tid}_fix.json")) if tid != "CUR_riscv" else None
    cutoff = None
    if fix:
        cutoff = int(os.popen(f"git -C /root/repos/linux log -1 --format=%ct {fix['fix']}").read().strip() or 0) or None
    pnames = patch_names(cutoff)
    # interfaces: previous round + amendment 1 (same-revision generic + arch definitions)
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
    has_ret = {c[2] for f in T["functions"].values() for c in f["calls"] if c[4] not in ("discard", "macro")}
    ncalls = {}
    for f in common:
        for c in f["calls"]:
            if c[2] in interfaces:
                ncalls[c[2]] = ncalls.get(c[2], 0) + 1
    sites = []
    for f in common:
        arg_lines = {(u[1], u[2]) for u in f["uses"] if u[3] == "arg"}
        checks = [k for k in f["checks"]]
        for c in f["calls"]:
            off, line, I, bases, ret = c
            if I not in interfaces:
                continue
            later_uses = [u for u in f["uses"] if u[0] > off and u[1] != line]
            later_checks = [k for k in checks if k[0] > off]

            def first_unchecked(var):
                us = [u for u in later_uses if u[2] == var]
                if not us:
                    return None
                u = us[0]
                # I5: a variable that is only a call argument on the condition's line is not checked there
                # (conditions may span lines: an arg use within the next 2 lines of the condition start counts)
                if any(var in k[2] and not any((k[1] + d, var) in arg_lines for d in (0, 1, 2)) and k[0] < u[0]
                       for k in later_checks):
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
                u = first_unchecked(ret[1:])
                if u:
                    forms.append(("F2", "ret", ret[1:], u))
            if ret == "return":
                forms.append(("F3", "ret", "<return>", [off, line, "<return>", "return", None]))
            if ret == "expr" and not any(k[1] == line for k in checks):  # I6
                forms.append(("F2", "ret", "<expr>", [off, line, "<expr>", "expr", None]))
            for form, r, R, u in forms:
                rar = 1 / math.log2(1 + ncalls.get(I, 1))
                P = 1.5 if (f["name"] in pnames or I in pnames) else 1.0
                guarded = any(c2[0] < off and c2[4] in ("cond", "macro") and CAP.match(c2[2]) for c2 in f["calls"])
                sites.append({"fn": f["name"], "file": f["file"], "line": line, "interface": I, "resource": r, "var": R, "guarded": guarded,
                              "form": form, "use": {"line": u[1], "kind": u[3], "callee": u[4]},
                              "score": FORM_W[form] * rar * P, "P": P})
    # I7: aggregate per interface
    agg = {}
    for s in sites:
        agg.setdefault(s["interface"], []).append(s)
    items = []
    for I, ss in agg.items():
        lacks, n_impl, impl_archs = arch_status(I, scan)
        hz = {}
        for arch, bn, ad, cats in (("riscv", bnT, "arch/riscv/", cT), ("arm64", bnA, "arch/arm64/", cA), ("x86_64", bnX, "arch/x86/", cX)):
            impl, where = impl_of(I, bn, ad)
            rs = sorted({str(s["resource"]) for s in ss})
            e, cs = effect(impl, bn, "ret" if rs == ["ret"] else int(next((x for x in rs if x != "ret"), 0)), cats)
            hz[arch] = {"effect": e, "cats": sorted(cs), "where": where, "loc": f"{impl['file']}:{impl['line']}" if impl else None,
                        "pure": bool(impl) and not impl["summary"]["writes"] and not impl["calls"]}
        q, gate = None, None
        if lacks:  # J1
            guards = scan["guards"].get(I, [])
            sel = scan["selects"]
            on_impl = [g for g in guards if any(g in sel.get(a, ()) for a in impl_archs)]
            on_rv = [g for g in guards if g in sel.get("riscv", ())]
            own_triv = scan["defs"].get(I, {}).get("riscv") == "trivial"
            if on_impl and not on_rv:
                q, gate = "特性未开启", on_impl
            elif on_rv:
                q, gate = "Q-特性", on_rv
            elif own_triv:
                q = "有意空实现"
            elif all(s["guarded"] for s in ss):
                q = "已判断"
            elif n_impl >= 3:
                q = "Q-多数"
            elif n_impl >= 1:
                q = "特性专有"
        elif hz["arm64"]["where"] and hz["x86_64"]["where"] and hz["riscv"]["where"] and not hz["riscv"]["pure"]:  # J4
            miss = (set(hz["arm64"]["cats"]) & set(hz["x86_64"]["cats"])) - set(hz["riscv"]["cats"])
            if miss:
                q = "Q-类别"
                hz["riscv"]["missing"] = sorted(miss)
        ss.sort(key=lambda s: (-s["score"], s["file"], s["line"]))
        # dedupe sites by normalized (fn, file, line, resource)
        seen, uniq = set(), []
        for s in ss:
            k = (s["fn"], s["file"], s["line"], str(s["resource"]))
            if k not in seen:
                seen.add(k)
                uniq.append(s)
        items.append({"interface": I, "q": q, "gate": gate, "score": round(uniq[0]["score"] * QF[q], 4), "lacks": lacks,
                      "n_impl": n_impl, "impl_archs": impl_archs, "horizontal": hz, "n_sites": len(uniq),
                      "forms": sorted({s["form"] for s in uniq}), "sites": uniq[:20],
                      "fns": sorted({s["fn"] for s in uniq})})
    items.sort(key=lambda it: (-it["score"], it["interface"]))
    res = {"tree": tid, "interfaces": len(interfaces), "sites": len(sites), "items": len(items),
           "by_q": {k or "none": sum(1 for it in items if it["q"] == k) for k in QF}}
    if fix:
        fx = set(fix_locations(fix["parent"], fix["fix"]))
        hits = [i for i, it in enumerate(items) if it["interface"] in fx or fx & set(it["fns"])]
        res.update({"fix_functions": sorted(fx), "located": bool(hits),
                    "qualified_hit": any(items[i]["q"] in QUAL for i in hits),
                    "first_hit_rank": hits[0] + 1 if hits else None,
                    "top50": bool(hits and hits[0] < 50),
                    "hits": [{"rank": i + 1, "interface": items[i]["interface"], "q": items[i]["q"], "gate": items[i]["gate"], "score": items[i]["score"],
                              "n_impl": items[i]["n_impl"], "lacks": items[i]["lacks"],
                              "effects": {a: (e["effect"], e["cats"]) for a, e in items[i]["horizontal"].items()},
                              "fns": [f for f in items[i]["fns"] if f in fx] or items[i]["fns"][:3]} for i in hits[:5]]})
    if tid == "CUR_riscv":
        q = [it for it in items if it["q"] in QUAL]
        res["review_sample"] = [it["interface"] for it in random.Random(20261113).sample(q, min(40, len(q)))]
        prev = json.load(open(CT / "effdep2_dev_20261113/out/CUR_riscv.json"))["review_sample"]
        qmap = {it["interface"]: it["q"] for it in items}
        res["prev_review"] = {n: qmap.get(n, "absent") for n in prev}
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    (out / f"{tid}.json").write_text(json.dumps({**res, "top": items[:300]}, indent=1, ensure_ascii=False))
    L = [f"# 人工分析建议（第三版）：{tid}", "",
         f"接口 {res['interfaces']} 个；候选位置 {res['sites']} 个，按接口聚合为 {res['items']} 条；"
         "；".join(f"{k} {v}" for k, v in res["by_q"].items()) + "。以下为前 50 条。", ""]
    for i, it in enumerate(items[:50], 1):
        h = it["horizontal"]
        if it["q"] == "Q-特性":
            why = f"riscv 选了特性开关 {'、'.join('CONFIG_' + g for g in it['gate'])}，却没有自己的实现（通用桩是空的）"
        elif it["q"] == "Q-多数":
            why = f"riscv 没有实现或是空实现，而 {it['n_impl']} 个其他架构有实际实现（{'、'.join(it['impl_archs'][:8])}）"
        elif it["q"] == "Q-类别":
            why = f"riscv 的实现缺少 {'、'.join(h['riscv'].get('missing', []))} 类效果，arm64 和 x86_64 的实现都有"
        elif it["q"] == "特性专有":
            why = f"只有 {'、'.join(it['impl_archs'])} 实现，可能是特性专有，优先级低"
        else:
            why = "横向比对不成立"
        L += [f"## {i}. 接口 `{it['interface']}`（{it['q'] or '未定性'}，{it['n_sites']} 处调用）", "",
              "- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 " + "、".join(it["forms"]),
              f"- 依据：{why}",
              "- 各架构实现：" + "；".join(f"{a} {e['where'] or '无实现'} {e['loc'] or ''} → {e['effect']}"
                                         + (f"（{'+'.join(e['cats'])}）" if e["cats"] else "") for a, e in h.items()),
              "- 可疑调用位置：" + "；".join(f"`{s['fn']}` {s['file']}:{s['line']}（{s['form']}，第 {s['use']['line']} 行使用）"
                                          for s in it["sites"][:3]),
              "- 为什么需要人看：本轮未做动态确认",
              f"- 建议怎么查：对照 {'、'.join((it['impl_archs'] or ['arm64', 'x86_64'])[:3])} 的实现，看公共层依赖的效果在 riscv 上由谁保证",
              f"- 得分 {it['score']}", ""]
    (out / f"{tid}_suggestions.md").write_text("\n".join(L) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k not in ("hits", "review_sample", "prev_review")}, ensure_ascii=False))
    for h in res.get("hits", [])[:3]:
        print("  hit", json.dumps(h, ensure_ascii=False))


if __name__ == "__main__":
    main()
