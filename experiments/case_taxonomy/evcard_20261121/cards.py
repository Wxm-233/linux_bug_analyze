"""evcard criteria 一～五: reviewed set, merge, evidence cards, two queues, card-check sample. WSL.

    python3 cards.py run      -> cards.jsonl, inventory.csv, queues.csv, card_sample.json (positions only), cards_summary.json
"""
import csv
import json
import os
import random
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "p1check_20261115"))
import p1check as C  # noqa: E402

REPO = "/root/repos/linux"
REV = "df2908090cda"
SRC = "/root/repos/linux/"
BUILDS = {a: f"/root/work/boundary_build/{a}_defconfig" for a in ("riscv", "arm64", "x86_64")}
CHECK_OF = {"WT": "类型一致性", "ORD": "类型一致性", "P1": "实现一致性", "XV": "实现一致性", "TLB": "实现一致性", "WK": "实现一致性",
            "XA": "实现一致性", "EZ": "实现一致性", "CTX": "调用上下文"}
REVIEW_PAT = re.compile(r"(review|judg|label|adjudic|verdict|audit)", re.I)
T64 = {"u64", "s64", "loff_t", "phys_addr_t", "resource_size_t", "dma_addr_t", "__u64", "__s64", "uint64_t", "int64_t", "sector_t",
       "blkcnt_t", "pgoff_t_64"}
CASTS = ("(u64)", "(loff_t)", "(phys_addr_t)", "(resource_size_t)", "(s64)", "(unsignedlonglong)", "(__u64)", "(sector_t)")
ORD_GUARD = re.compile(r"\b(MAX_PAGECACHE_ORDER|thp_vma_suitable_order|thp_vma_allowable_orders?)\b|folio_order\s*\([^)]*\)\s*<=|order\s*<=")
_SRC = {}


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, errors="replace").stdout


def source(path):
    if path not in _SRC:
        _SRC[path] = git("show", f"{REV}:{path}")
    return _SRC[path]


def func_body(path, func, line):
    """(head_text, body_text, lo_line, hi_line) of the definition of func containing line (or nearest)"""
    src = source(path)
    if not src:
        return None
    t = C.tokenize(C.strip(src))
    best = None
    for name, params, lo, hi in C.functions(t):
        if name != func:
            continue
        l0, l1 = t[lo][1], t[hi][1]
        if line and l0 - 40 <= line <= l1:
            best = (lo, hi)
            break
        best = best or (lo, hi)
    if not best:
        return None
    lo, hi = best
    j = lo - 1
    while j >= 0 and t[j][0] not in (";", "}"):
        j -= 1
    lines = src.split("\n")
    return (" ".join(x[0] for x in t[j + 1:lo]), "\n".join(lines[t[lo][1] - 1:t[hi][1]]), t[lo][1], t[hi][1])


def reviewed_index():
    files = []
    for root, dirs, fs in os.walk(CT):
        if "evcard_20261121" in root or "sealed" in root or "__pycache__" in root:
            continue
        for fn in fs:
            hit = REVIEW_PAT.search(fn) or fn == "README.md" or "packet" in fn.lower() or "packets" in root  # amendment 1
            if hit and fn.endswith((".json", ".md", ".csv", ".txt")) and "sealed" not in fn:
                files.append(os.path.join(root, fn))
    texts = []
    for p in files:
        try:
            texts.append(open(p, encoding="utf-8", errors="ignore").read())
        except Exception:
            pass
    return texts, len(files)


def compiled_sets():
    out = {}
    for a, d in BUILDS.items():
        cc = json.load(open(d + "/compile_commands.json"))
        out[a] = {e["file"][len(SRC):] for e in cc if e["file"].startswith(SRC)}
    return out


def card(c, cs):
    e, f, fn, line, sig = c["engine"], c["file"], c["func"], c["line"], c["sigs"][0]
    src_lines = source(f).split("\n")
    sl = src_lines[line - 1] if 0 < line <= len(src_lines) else ""
    fb = func_body(f, fn, line)
    body = fb[1] if fb else ""
    head = fb[0] if fb else ""
    # 1. consumer
    cons, why = "未知", ""
    if e == "WT":
        k = sig.split("|")
        if len(k) > 1 and (k[1].startswith("assign:") or k[1].startswith("return")):
            cons, why = "有", f"{k[1]}（{f}:{line}）"
        else:
            why = f"特征 {k[1] if len(k) > 1 else sig} 不是赋值或返回"
    elif e == "ORD":
        orders = [x for x in sig.split("|") if x]
        if any(re.search(r"\w+\s*\([^;]*\b" + re.escape(o) + r"\b", sl) for o in orders):
            cons, why = "有", f"报告行把阶数宏传给调用：{sl.strip()[:90]}"
        else:
            why = "报告行没有以阶数宏为实参的调用"
    elif e == "P1":
        acc = sig.split("|")[0]
        if re.search(r"\b(if|while|return)\b.*\b" + re.escape(acc) + r"\s*\(", sl) or re.search(r"=\s*[^=].*\b" + re.escape(acc) + r"\s*\(", sl) \
                or re.search(r"\w+\s*\([^;]*\b" + re.escape(acc) + r"\s*\(", sl):
            cons, why = "有", f"访问函数结果被使用：{sl.strip()[:90]}"
        else:
            why = "报告行看不出结果怎么用"
    elif e == "XV":
        if re.search(r"\b(set_pte\w*|set_pmd\w*|set_pud\w*|ptep_\w+|pmdp_\w+|return)\b|\*\s*\w+\s*=", sl):
            cons, why = "有", f"编码后的值被写回或返回：{sl.strip()[:90]}"
        else:
            why = "报告行没有写回或返回"
    elif e in ("CTX", "WK"):
        cons, why = "有", "原始特征给出了调用处或调用方依赖"
    elif e == "EZ":
        cons, why = "有", "E1 返回给调用方 / E2、E3 有调用方"
    else:
        why = f"{e} 的消费位置词法看不出"
    # 2. arch / config
    comp = "".join(a[0] for a in ("riscv", "arm64", "x86_64") if f in cs[a])
    archb, awhy = "有", ""
    if e in ("WK", "XA", "CTX"):
        archb = "有" if c.get("arch") else "未知"
        awhy = f"受影响架构：{c.get('arch') or '空'}"
    elif e == "EZ":
        archb = "有" if c.get("ez_arch") else "否"
        awhy = "E-ZERO 架构证据标记"
    elif e == "WT":
        if f.startswith("arch/arm64/") or re.search(r"arch/x86/.*_64\.c$", f) or re.search(r"arch/riscv/.*64.*\.c$", f):
            archb, awhy = "否", "文件只在 64 位架构上编译，不存在 32 位截断"
        else:
            awhy = "32 位架构上 unsigned long 只有 32 位"
    elif e == "ORD":
        awhy = "大页面配置（如 arm64 64K）下阶数可能超过页缓存上限"
    elif e in ("P1", "XV"):
        awhy = "各架构页表项编码不同"
    elif e == "TLB":
        awhy = "各架构 TLB 刷新语义不同"
    # 3. counter-evidence
    cnt, cwhy = "没有检查", ""
    if e == "WT":
        cnt, cwhy = "查过未见补偿", "目标类型和转换都不是 64 位"
        k = sig.split("|")
        expr = k[2] if len(k) > 2 else ""
        if any(x in expr.replace(" ", "") for x in CASTS) or any(x in sl.replace(" ", "") for x in CASTS):
            cnt, cwhy = "看到补偿", "表达式里有 64 位转换"
        elif len(k) > 1 and k[1].startswith("assign:"):
            tgt = k[1][7:]
            if re.match(r"^[A-Za-z_]\w*$", tgt):
                m = re.search(r"\b(" + "|".join(sorted(T64)) + r"|unsigned\s+long\s+long)\b[^;=(]*\b" + re.escape(tgt) + r"\b", body)
                if m:
                    cnt, cwhy = "看到补偿", f"目标 {tgt} 声明为 {m.group(1)}"
            else:
                cnt, cwhy = "没有检查", f"目标 {tgt} 是成员，类型没查"
        elif len(k) > 1 and k[1].startswith("return"):
            if re.search(r"\b(" + "|".join(sorted(T64)) + r"|unsigned\s+long\s+long)\b", head):
                cnt, cwhy = "看到补偿", "函数返回类型是 64 位"
    elif e == "ORD":
        m = ORD_GUARD.search(body)
        cnt, cwhy = ("看到补偿", f"函数里有上限检查：{m.group(0)}") if m else ("查过未见补偿", "函数里没有 MAX_PAGECACHE_ORDER 一类检查")
    elif e == "EZ":
        cnt, cwhy = "查过未见补偿", "五类反证都没看到"
        pats = [(r"\bflags?\s*\|=\s*__GFP_ZERO", "局部变量里 |= __GFP_ZERO"), (r"\bgfp\s*=\s*GFP_PGTABLE_\w+", "局部 gfp 是含 __GFP_ZERO 的常量"),
                (r"want_init_on_alloc\s*\(", "辅助判断函数 want_init_on_alloc"), (r"kmem_cache_alloc\s*\(\s*(pgd_cachep|pgtable_cache)", "slab 构造函数清零"),
                (r"\*\s*\w+\s*=\s*\*", "解引用写入")]
        for p, w in pats:
            if re.search(p, body):
                cnt, cwhy = "看到补偿", w
                break
    return {"consumer": [cons, why], "compiled": comp or "-", "arch_basis": [archb, awhy], "counter": [cnt, cwhy]}


def tier(cd):
    if cd["counter"][0] == "看到补偿":
        return 4
    a = cd["consumer"][0] == "有"
    b = cd["arch_basis"][0] == "有"
    return 1 if a and b else (2 if a or b else 3)


def main():
    tab = json.loads((CT / "scan3_20261119/tables/df2908090cda.json").read_text(encoding="utf-8"))["rows"]
    ez = json.loads((CT / "effzero_20261120/cur/effzero.json").read_text())["cands"]
    raw = [{"engine": r["engine"], "file": r["file"], "line": r["line"], "func": r["func"], "arch": r["arch"], "sig": r["sig"],
            "prio": r["prio"], "old": i} for i, r in enumerate(tab)]
    base = len(raw)
    for c in ez:
        raw.append({"engine": "EZ", "file": c["file"], "line": c["line"], "func": c["func"], "arch": "", "sig": f"{c['form']}|{c['group']}",
                    "prio": 1, "old": base + c["rank"], "ez_arch": c["arch"]})
    texts, nfiles = reviewed_index()

    def reviewed(r):
        fnre = re.compile(r"\b" + re.escape(r["func"]) + r"\b")
        return any(r["file"] in t and fnre.search(t) for t in texts)
    merged = {}
    for r in raw:
        k = (r["file"], r["func"], r["engine"])
        m = merged.setdefault(k, {**{x: r[x] for x in ("engine", "file", "line", "func", "arch", "prio", "old")}, "sigs": [],
                                  "ez_arch": r.get("ez_arch")})
        m["sigs"].append(r["sig"])
        m["old"] = min(m["old"], r["old"])
    cs = compiled_sets()
    inv, pool = [], []
    for k, m in merged.items():
        m["reviewed"] = reviewed(m)
        m["card"] = card(m, cs)
        m["tier"] = tier(m["card"])
        m["check"] = CHECK_OF[m["engine"]]
        m["id"] = f"{m['engine']}:{m['file']}:{m['func']}"
        inv.append(m)
        if not m["reviewed"]:
            pool.append(m)
    old_q = sorted(pool, key=lambda m: m["old"])
    new_q = sorted(pool, key=lambda m: (m["tier"], m["old"]))
    with open(HERE / "cards.jsonl", "w") as f:
        for m in inv:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    with open(HERE / "inventory.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "check", "engine", "file", "line", "func", "prio", "old_order", "reviewed", "tier", "consumer", "compiled",
                    "arch_basis", "counter"])
        for m in sorted(inv, key=lambda m: m["old"]):
            cd = m["card"]
            w.writerow([m["id"], m["check"], m["engine"], m["file"], m["line"], m["func"], m["prio"], m["old"], m["reviewed"], m["tier"],
                        cd["consumer"][0], cd["compiled"], cd["arch_basis"][0], cd["counter"][0]])
    with open(HERE / "queues.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "old_queue", "new_queue"])
        for i in range(max(len(old_q), len(new_q))):
            w.writerow([i + 1, old_q[i]["id"] if i < len(old_q) else "", new_q[i]["id"] if i < len(new_q) else ""])
    # card-check sample (criteria 五): positions only
    rnd = random.Random(20261121)
    by = defaultdict(list)
    for m in sorted(pool, key=lambda m: m["id"]):
        by[m["check"]].append(m)
    pick = []
    for ck in ("类型一致性", "实现一致性", "调用上下文"):
        pick += rnd.sample(by[ck], min(2, len(by[ck])))
    rest = [m for m in sorted(pool, key=lambda m: m["id"]) if m not in pick]
    pick += rnd.sample(rest, 12 - len(pick))
    (HERE / "card_sample.json").write_text(json.dumps([{"id": m["id"], "engine": m["engine"], "file": m["file"], "line": m["line"],
                                                         "func": m["func"], "sig": m["sigs"][0]} for m in pick], indent=1, ensure_ascii=False))
    summ = {"candidates": len(raw), "merged": len(inv), "review_files": nfiles, "reviewed": sum(m["reviewed"] for m in inv),
            "pool": len(pool), "pool_by_engine": dict(Counter(m["engine"] for m in pool)), "pool_by_tier": dict(Counter(m["tier"] for m in pool)),
            "top12_old": [m["id"] for m in old_q[:12]], "top12_new": [m["id"] for m in new_q[:12]],
            "overlap_top12": len({m["id"] for m in old_q[:12]} & {m["id"] for m in new_q[:12]})}
    (HERE / "cards_summary.json").write_text(json.dumps(summ, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in summ.items() if not k.startswith("top12")}, indent=1, ensure_ascii=False))
    print("overlap", summ["overlap_top12"])


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    if sys.argv[1] == "run":
        main()
