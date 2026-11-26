"""taskcard2 criteria 二: task cards v2 - entries by kind (top N per kind, boot-time entries, dispatchers for callbacks) and
consequence-side observation points (CTX effect chain, page-table/swap-entry decoders, ORD limit checks). The v1 generator
(taskcard_20261125/taskcard.py) and its call-graph cache are imported read-only; only reach / entry_kind are replaced at run time.
WSL.

    python3 taskcard2.py run    -> cards/, cards_gold.json, result.json
"""
import json
import re
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "taskcard_20261125"))
import taskcard as T  # noqa: E402

CAP = {"系统调用": 15, "回调": 15, "启动时": 5, "架构入口": 5}            # criteria 二.1.1
INITCALL = re.compile(r"\b(?:(?:early|core|postcore|arch|subsys|fs|rootfs|device|late|pure)_initcall(?:_sync)?|module_init)"
                      r"\s*\(\s*(\w+)\s*\)")
DISPATCH = {("vm_operations_struct", "fault"): "handle_mm_fault", ("vm_operations_struct", "huge_fault"): "handle_mm_fault",
            ("vm_operations_struct", "page_mkwrite"): "handle_mm_fault", ("vm_operations_struct", "pfn_mkwrite"): "handle_mm_fault",
            ("file_operations", "read"): "sys_read", ("file_operations", "read_iter"): "sys_read",
            ("file_operations", "write"): "sys_write", ("file_operations", "write_iter"): "sys_write",
            ("file_operations", "mmap"): "sys_mmap", ("file_operations", "unlocked_ioctl"): "sys_ioctl",
            ("proc_ops", "proc_read"): "sys_read", ("proc_ops", "proc_write"): "sys_write",
            ("seq_operations", "show"): "seq_read（读这个文件）", ("cftype", "write"): "cgroup_file_write（写 cgroup 文件）",
            ("cftype", "seq_show"): "读 cgroup 文件", ("kobj_attribute", "store"): "写 sysfs 文件", ("kobj_attribute", "show"): "读 sysfs 文件",
            ("device_attribute", "store"): "写 sysfs 文件", ("device_attribute", "show"): "读 sysfs 文件"}
CTXPRED = re.compile(r"\b(in_task|in_interrupt|in_softirq|in_atomic|irqs_disabled|preemptible|lockdep_assert_irqs_enabled|"
                     r"might_sleep|might_resched|in_nmi)\b")
ERRK = ("pr_err", "pr_crit", "pr_alert", "pr_emerg", "pr_err_ratelimited", "pte_ERROR", "pmd_ERROR", "pud_ERROR", "p4d_ERROR",
        "pgd_ERROR", "BUG", "BUG_ON", "WARN", "WARN_ON", "WARN_ON_ONCE", "WARN_ONCE")
COMMON = ("include/linux/", "mm/", "kernel/", "fs/", "lib/")
LIMIT_EXTRA = {"XA_CHUNK_SHIFT", "MAX_PAGE_ORDER", "MAX_FOLIO_ORDER"}
EXTRA = {}


def extras(G):
    """boot-time registrations; decoder functions (softleaf_t / swp_entry_t parameters); ORD limit-check sites"""
    boot = set()
    files = sorted({d[0] for v in G["defs"].values() for d in v})
    for f in files:
        for m in INITCALL.finditer("\n".join(T.stripped(f))):
            if m.group(1) in G["defs"]:
                boot.add(m.group(1))
    dec = []
    for name, ds in G["defs"].items():
        for f, a, b, lab, st in ds[:1]:
            if not f.startswith(COMMON) and not f.startswith("include/"):
                continue
            hdr = " ".join(T.stripped(f)[a - 1:min(b, a + 4)]).split("{")[0]
            if re.search(r"\b(softleaf_t|swp_entry_t)\b", hdr):
                dec.append(name)
    sys.path.insert(0, str(CT / "orddom_20261116"))
    import orddom as O
    lim = set(O.L0) | LIMIT_EXTRA
    ordsites = []
    for name, ds in G["defs"].items():
        for f, a, b, lab, st in ds[:1]:
            if not f.startswith(COMMON):
                continue
            for i, l in enumerate(T.stripped(f)[a - 1:b], a):
                m = T.WARN.search(l)
                if m and re.search(r"\border\b", l) and set(T.IDENT.findall(l)) & lim:
                    ordsites.append({"func": name, "file": f, "line": i, "kind": m.group(1), "text": T.raw(f)[i - 1].strip()[:100],
                                     "why": "后果处：ORD 上限的执行处"})
    EXTRA.update(boot=boot, dec=dec, ordsites=ordsites)
    print("extras: boot", len(boot), "decoders", len(dec), "ord limit sites", len(ordsites), flush=True)


def entry_kind2(G, n):
    if n.startswith(("sys_", "compat_sys_")) and n in G["defs"]:
        return "系统调用", "系统调用", None
    rt = sorted(x for x in G["regtype"].get(n, ()) if x[0] in T.USER_TYPES)
    if rt:
        t, v, fld = rt[0]
        return "回调", f"回调：{t} {v}.{fld}", (t, fld)
    if n in EXTRA["boot"]:
        return "启动时", "启动时（initcall）", None
    ds = G["defs"].get(n, [])
    if ds and all(d[0].startswith("arch/") for d in ds) and not any(not p.startswith("var:") for p, _ in G["rev"].get(n, ())):
        return "架构入口", "架构入口（没有 C 调用者）", None
    return None


def reach2(G, sources, maxd=16, cap=None):
    par, dist = {}, {}
    q = deque()
    for s in sources:
        if s in G["defs"] and s not in dist:
            dist[s] = 0
            q.append(s)
    while q:
        n = q.popleft()
        if dist[n] >= maxd:
            continue
        for p, k in G["rev"].get(n, ()):
            if p not in dist:
                dist[p] = dist[n] + 1
                par[p] = (n, k)
                q.append(p)
    byk = defaultdict(list)
    for n, d in dist.items():
        ek = entry_kind2(G, n)
        if ek:
            byk[ek[0]].append((d, n, ek[1], ek[2]))

    def path(n):
        out = [n]
        while n in par:
            n2, k = par[n]
            out += [f"—{k}→", n2]
            n = n2
        return out
    ents = []
    for kind in ("系统调用", "回调", "启动时", "架构入口"):
        for d, n, desc, tf in sorted(byk.get(kind, []))[:CAP[kind]]:
            p = path(n)
            disp = DISPATCH.get(tf) if tf else None
            if disp:
                p = [disp, f"—经 {tf[0]}.{tf[1]} 分发→"] + p           # criteria 二.1.3
            ents.append({"entry": n, "kind": desc, "depth": d, "path": p, "dispatcher": disp})
    return ents, sum(len(v) for v in byk.values()), len(dist)


def ctx_witness():
    d = json.loads((T.Path("/root/work/commitmode_cache/CTX3") / f"{T.REV}.json").read_text())
    return {(x["hook"], x["arch"], x.get("site", "")): x.get("witness", []) for x in d["cands"]}


def downstream(G, row, wit):
    eng, sig = row["engine"], row["sig"]
    out = []
    if eng == "CTX":
        site = sig.split("调用点 ")[-1]
        parts = sig.split("|")
        w = wit.get((parts[0], parts[1], site), [])
        for fn in w:
            for c, d in [(fn, 0)] + T.callees(G, [fn], 3):
                for p in T.warns_in(G, c, f"后果处：CTX 效果链（{fn} 往下第 {d} 层）", cap=8):
                    if CTXPRED.search(T.stripped(p["file"])[p["line"] - 1]):
                        out.append(p)
    fam = sig.split("|")[1] if eng == "EC" and "|" in sig else ""
    if eng in ("P1", "XV") or fam in ("PT", "SW"):
        pts = []
        for n in EXTRA["dec"]:
            pts += T.warns_in(G, n, "后果处：页表项、交换项的解码点", cap=4)
        pts.sort(key=lambda p: (0 if p["kind"] in ERRK else 1, p["file"], p["line"]))
        out += pts
    if eng == "ORD":
        out += sorted(EXTRA["ordsites"], key=lambda p: (p["file"], p["line"]))
    seen, res = set(), []
    for p in out:
        k = (p["file"], p["line"])
        if k not in seen:
            seen.add(k)
            res.append(p)
    return res[:30]


def card2(G, row, recs, ec, ord_hz, wit):
    c = T.card(G, row, recs, ec, ord_hz)                     # uses reach2 / entry_kind2 (patched below)
    c["观测点"]["near"] = c["观测点"].pop("points")
    c["观测点"]["consequence"] = downstream(G, row, wit)
    c["观测点"]["points"] = c["观测点"]["near"] + c["观测点"]["consequence"]
    if c["观测点"]["consequence"]:
        c["自动程度"]["观测点"] = "半自动（附近 + 后果处）"
    if row["engine"] == "CTX":                                # criteria 二.3
        arch = row.get("arch", "")
        b5 = {"riscv": "riscv", "arm64": "arm64", "x86": "x86_64", "arm": "arm", "powerpc": "powerpc"}
        c["差分对照"] = {"deviant": [b5.get(arch, arch)], "normal": [b for b in T.BUILDS if b != b5.get(arch, arch)],
                       "source": "CTX 引擎：报告的架构有这个效果，其余架构的实现判为没有"}
        c["自动程度"]["差分对照"] = "自动"
    return c


GOLD2 = T.GOLD + [
    {"id": "H", "exp": "s5dyn", "engine": "P1", "file": "mm/internal.h", "line": 422, "func": "folio_pte_batch_flags", "sig": "pte_pfn",
     "entry": ["memory_reclaim"], "cfg": {"MMU"}, "diff": None, "obs": [(None, "mm/internal.h:420")], "pre": ["device-exclusive"],
     "switch": [], "plat": ["DEVICE_PRIVATE"], "set": "验证"},
    {"id": "I", "exp": "lpaeinv", "engine": "EC", "file": "arch/arm/include/asm/pgtable-3level.h", "line": 217, "func": "pmd_mkinvalid",
     "sig": "pmd_present", "entry": ["debug_vm_pgtable"], "cfg": set(), "diff": ({"arm_lpae"}, None),
     "obs": [(None, "mm/debug_vm_pgtable.c:929"), (None, "mm/debug_vm_pgtable.c:930")], "pre": [], "switch": [], "plat": ["ARM_LPAE"],
     "set": "验证（入口不独立）"},
    {"id": "J", "exp": "s8dyn", "engine": "CTX", "file": "include/linux/mm.h", "line": 4999, "func": "__kernel_map_pages", "sig": "riscv",
     "entry": ["sys_clone", "sys_fork", "sys_pipe2", "sys_pipe", "sys_mmap", "sys_mmap_pgoff", "sys_munmap", "sys_read"],
     "cfg": {"DEBUG_PAGEALLOC"}, "diff": ({"riscv"}, {"x86_64"}), "obs": [("smp_call_function_many_cond", None)], "pre": [], "switch": [],
     "plat": [], "set": "验证"}]
for g in GOLD2:
    g.setdefault("set", "开发")
    if isinstance(g["entry"], str):
        g["entry"] = [g["entry"]]


def check(cards, rows):
    res = []
    for g in GOLD2:
        r = T.pick(rows, g)
        if r is None:
            res.append({"id": g["id"], "row": None})
            continue
        c = cards[r["no"]]
        t1 = g["cfg"] <= set(c["触发配置"]["compile_configs"])
        d = c["差分对照"]
        if g["diff"] is None:
            t2 = isinstance(d.get("deviant"), str) and d["deviant"].startswith("需人工")
        else:
            dev, nor = g["diff"]
            t2 = isinstance(d.get("deviant"), list) and dev <= set(d["deviant"]) and (nor is None or nor <= set(d.get("normal", []))) \
                and not (set(d.get("normal", [])) & set(d["deviant"]))
        E = c["到达路径"]["entries"]
        hit = next((e for e in E if e["entry"] in g["entry"] or any(x in g["entry"] for x in e["path"])), None)
        pts = c["观测点"]["points"]
        om = [{"gold": fn or fl, "ok": any((fn and p["func"] == fn) or (fl and f'{p["file"]}:{p["line"]}' == fl) for p in pts),
               "where": next((p["why"] for p in pts if (fn and p["func"] == fn) or (fl and f'{p["file"]}:{p["line"]}' == fl)), None)}
              for fn, fl in g["obs"]]
        res.append({"id": g["id"], "exp": g["exp"], "set": g["set"], "row": r["no"], "T1": t1, "T2": t2, "T3": hit is not None,
                    "T3_entry": hit["entry"] if hit else None, "T3_kind": hit["kind"] if hit else None,
                    "T3_path": hit["path"] if hit else None, "T4": om,
                    "n_entries": len(E), "n_obs_near": len(c["观测点"]["near"]), "n_obs_conseq": len(c["观测点"]["consequence"])})
    return res


def run():
    T.reach, T.entry_kind = reach2, (lambda G, n: (lambda k: (0, k[1]) if k else None)(entry_kind2(G, n)))
    G = T.build_graph()
    extras(G)
    rows = json.load(open(CT / "task4_20261125" / "out" / "table.json", encoding="utf-8"))["rows"]
    df = json.load(open(CT / "outfmt_20261124" / "tables" / "df2908090cda.json", encoding="utf-8"))["rows"]
    j = next(r for r in df if r["engine"] == "CTX" and r["file"] == "include/linux/mm.h" and r["line"] == 4999)
    rows = rows + [dict(j, no=10000 + j["no"], evidence=[], verdict="原表行（不在主表）")]
    recs = defaultdict(list)
    for b in T.BUILDS:
        for r in json.load(T.gzip.open(T.W / f"rec_{b}.json.gz", "rt")):
            if r["kind"] in ("调用", "宏"):
                recs[r["iface"]].append(r)
    ecd = json.load(open("/root/work/ec_cache/r10/df/df.json"))
    devs = json.load(open("/root/work/ec_cache/r10/df/df2908090cda/deviations.json"))
    ec = {"devs": devs, "builds": sorted(ecd.get("builds") or {d["build"] for d in devs})}
    sys.path.insert(0, str(CT / "orddom_20261116"))
    import orddom as O
    _, sets = O.analyze(O.blobs_of(T.REV))
    ord_hz = {}
    for s, bases in sets["S"].items():
        hz = [O.HZ[b] for b in bases if b in O.HZ]
        ord_hz[s] = {"M": sorted({c for h in hz for c in h["M"]}), "avail": sorted({c for h in hz for c in h["avail"]}), "bases": bases}
    wit = ctx_witness()
    cards = {}
    (HERE / "cards").mkdir(exist_ok=True)
    for r in rows:
        c = card2(G, r, recs, ec, ord_hz, wit)
        cards[r["no"]] = c
        json.dump(c, open(HERE / "cards" / f"{r['no']:05d}.json", "w"), ensure_ascii=False, indent=1)
    gold = check(cards, rows)
    json.dump({g["id"]: cards.get(g["row"]) for g in gold if g.get("row")}, open(HERE / "cards_gold.json", "w"), ensure_ascii=False, indent=1)
    dev = [g for g in gold if g["set"] == "开发"]
    val = [g for g in gold if g["set"].startswith("验证")]
    v4 = [o for g in val for o in g["T4"]]
    d4 = [o for g in dev for o in g["T4"]]
    main = [c for no, c in cards.items() if no < 10000]
    noise = {"entries_avg": round(sum(len(c["到达路径"]["entries"]) for c in main) / len(main), 1),
             "obs_near_avg": round(sum(len(c["观测点"]["near"]) for c in main) / len(main), 1),
             "obs_conseq_avg": round(sum(len(c["观测点"]["consequence"]) for c in main) / len(main), 1)}
    auto = defaultdict(Counter)
    for c in main:
        for k, v in c["自动程度"].items():
            auto[k][v.split("（")[0]] += 1
    res = {"V1": all(g["T1"] for g in val), "V2": all(g["T2"] for g in val), "V3": all(g["T3"] for g in val if g["id"] in "HJ"),
           "V3_I": next(g["T3"] for g in val if g["id"] == "I"),
           "V4": {"matched": sum(o["ok"] for o in v4), "n": len(v4), "pass": sum(o["ok"] for o in v4) >= 3},
           "D1": all(g["T1"] and g["T2"] for g in dev), "D2": {"T3": sum(g["T3"] for g in dev), "T4": sum(o["ok"] for o in d4), "T4_n": len(d4)},
           "N": noise, "gold": gold, "automation": {k: dict(v) for k, v in auto.items()}, "cards": len(cards)}
    json.dump(res, open(HERE / "result.json", "w"), ensure_ascii=False, indent=1)
    for g in gold:
        print("GOLD", g["id"], g["set"], "row", g["row"], "T1", g["T1"], "T2", g["T2"], "T3", g["T3"], g["T3_entry"], g["T3_kind"],
              "T4", [(o["gold"], o["ok"], o["where"]) for o in g["T4"]], "sizes", g["n_entries"], g["n_obs_near"], g["n_obs_conseq"], flush=True)
    print("V1", res["V1"], "V2", res["V2"], "V3", res["V3"], "V3_I", res["V3_I"], "V4", res["V4"], "D1", res["D1"], "D2", res["D2"], "N", noise)


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    {"run": run}[sys.argv[1]]()
