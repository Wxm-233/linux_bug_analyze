"""taskcard3 criteria 一: task cards v3 - consumer gaps fixed (EC evidence, CTX site), trigger entries ranked by specificity
(hub functions on the path, then distance), precondition entries (reverse search from producers), consequence points per row.
Imports taskcard2 / taskcard read-only and replaces functions at run time. WSL.

    python3 taskcard3.py run    -> cards/, cards_gold.json, result.json
"""
import heapq
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "taskcard2_20261125"))
import taskcard2 as T2  # noqa: E402
T = T2.T
HUB_IN = 100
PRE_CAP = 5
PRODUCER = {"迁移项": r"\b(make_readable_migration_entry|make_writable_migration_entry|make_readable_exclusive_migration_entry|"
                      r"set_pmd_migration_entry)\s*\(",
            "device-exclusive 项": r"\bmake_device_exclusive_entry\s*\(|^make_device_exclusive$",
            "device-private 项": r"\b(make_readable_device_private_entry|make_writable_device_private_entry)\s*\(",
            "uffd-wp 标记": r"make_pte_marker\s*\(\s*PTE_MARKER_UFFD_WP",
            "hwpoison 标记": r"\b(make_hwpoison_entry|make_poisoned_swp_entry)\s*\(",
            "交换项": r"\bswp_entry_to_pte\s*\("}
KIND_OF = {"交换项": "交换项", "迁移项": "迁移项", "THP 迁移项": "迁移项", "device-private 项": "device-private 项",
           "device-exclusive 项": "device-exclusive 项", "uffd-wp 标记": "uffd-wp 标记", "hwpoison 标记": "hwpoison 标记",
           "guard 标记（MADV_GUARD_INSTALL）": "guard 标记"}
X3 = {}


def extras3(G):
    indeg = Counter()
    for n, ps in G["rev"].items():
        indeg[n] = sum(1 for p, k in ps if k in ("调用", "函数指针"))
    hubs = {n for n, c in indeg.items() if c > HUB_IN}
    prod = defaultdict(set)
    bodies = {}
    for name, ds in G["defs"].items():
        for f, a, b, lab, st in ds[:1]:
            body = "\n".join(T.stripped(f)[a - 1:b])
            bodies[name] = body
            for kind, rx in PRODUCER.items():
                if rx.startswith(r"\bmake_device_exclusive_entry") and name == "make_device_exclusive":
                    prod[kind].add(name)
                if re.search(rx.split("|^")[0], body):
                    if kind == "交换项" and not re.search(r"unmap|swap", name):
                        continue
                    prod[kind].add(name)
    # decoder subsets (criteria 一.3)
    dec = T2.EXTRA["dec"]
    sub = {"迁移项": [n for n in dec if "migration" in n or "softleaf_is_migration" in bodies.get(n, "")],
           "swap": [n for n in dec if re.search(r"\bswp_entry_t\b", " ".join(T.stripped(G["defs"][n][0][0])[G["defs"][n][0][1] - 1:
                                                                                                          G["defs"][n][0][1] + 3]).split("{")[0])
                    or "device" in n],
           "marker": [n for n in dec if "marker" in n or "marker" in bodies.get(n, "")]}
    X3.update(hubs=hubs, prod=prod, sub=sub, bodies=bodies)
    print("extras3: hubs", len(hubs), "producers", {k: len(v) for k, v in prod.items()}, "decoder subsets",
          {k: len(v) for k, v in sub.items()}, flush=True)


def search(G, sources, maxd=16):
    """reverse search minimising (hub functions on the path, distance)"""
    best, par, h = {}, {}, []
    for s in sources:
        if s in G["defs"] and s not in best:
            best[s] = (0, 0)
            heapq.heappush(h, (0, 0, s))
    while h:
        hu, d, n = heapq.heappop(h)
        if best.get(n) != (hu, d) or d >= maxd:
            continue
        for p, k in G["rev"].get(n, ()):
            c = (hu + (p in X3["hubs"]), d + 1)
            if p not in best or c < best[p]:
                best[p] = c
                par[p] = (n, k)
                heapq.heappush(h, (c[0], c[1], p))
    return best, par


def entries(G, sources, cap):
    best, par = search(G, sources)
    byk = defaultdict(list)
    for n, (hu, d) in best.items():
        ek = T2.entry_kind2(G, n)
        if ek:
            byk[ek[0]].append((hu, d, n, ek[1], ek[2]))

    def path(n):
        out = [n]
        while n in par:
            n2, k = par[n]
            out += [f"—{k}→", n2]
            n = n2
        return out
    ents = []
    for kind in ("系统调用", "回调", "启动时", "架构入口"):
        for hu, d, n, desc, tf in sorted(byk.get(kind, []))[:cap[kind]]:
            p = path(n)
            disp = T2.DISPATCH.get(tf) if tf else None
            if disp:
                p = [disp, f"—经 {tf[0]}.{tf[1]} 分发→"] + p
            ents.append({"entry": n, "kind": desc, "depth": d, "hubs": hu, "path": p, "dispatcher": disp})
    return ents, sum(len(v) for v in byk.values()), len(best)


def reach3(G, sources, maxd=16, cap=None):
    return entries(G, sources, T2.CAP)


class Recs(dict):
    """per-row view of the consumer index: EC gets the row's evidence F added (criteria 一.1)"""
    def __init__(self, base, row):
        super().__init__()
        self.base, self.row = base, row

    def get(self, k, default=None):
        out = list(self.base.get(k, []))
        if self.row["engine"] == "EC" and k == self.row["func"]:
            for e in self.row["evidence"]:
                fl, name = e["F"].split(" ", 1)
                out.append({"F": {"file": fl.rsplit(":", 1)[0], "name": name}, "line": e["line"]})
        return out


def fix_row(row):
    """criteria 一.1: CTX consumer = the call site named in the signature"""
    if row["engine"] == "CTX" and not row.get("evidence"):
        loc = row["sig"].split("调用点 ")[-1]
        fl, _, rest = loc.partition(":")
        ln, _, fn = rest.partition(" ")
        row = dict(row, evidence=[{"build": "", "unit": "", "F": f"{fl}:0 {fn}", "line": int(ln) if ln.isdigit() else 0,
                                   "kind": "调用", "iface": row["func"], "bind": "", "guards": [], "config": []}])
    return row


def kinds_of(card, row):
    pre = card["前置状态"]
    ks = set()
    if isinstance(pre, dict) and pre.get("kinds"):
        ks = {KIND_OF.get(k["kind"], k["kind"]) for k in pre["kinds"]}
    if row["engine"] == "EC":
        for d in (card["资源与性质"].get("expected_actual") or []):
            key = d["key"] if isinstance(d, dict) else ""
            if "migration" in key:
                ks.add("迁移项")
            if "device_exclusive" in key:
                ks.add("device-exclusive 项")
            if "device_private" in key:
                ks.add("device-private 项")
    return ks


def producers(G, card, row):
    srcs, how = set(), []
    for k in kinds_of(card, row):
        if k in X3["prod"]:
            srcs |= X3["prod"][k]
            how.append(k)
    if row["engine"] == "EC":
        for d in (card["资源与性质"].get("expected_actual") or []):
            key = d["key"] if isinstance(d, dict) else ""
            for tok in re.split(r"[|>]", key):
                if tok in G["defs"] and any(not x[0].startswith("arch/") for x in G["defs"][tok]):
                    callers = {p for p, kk in G["rev"].get(tok, ()) if kk == "调用"}
                    srcs |= callers or {tok}
                    how.append(f"调用 {tok} 的函数")
            if "PAGE_NONE" in key:
                srcs.add("mprotect_fixup")
                how.append("PAGE_NONE → mprotect_fixup")
    return srcs, sorted(set(how))


def consequence(G, card, row, wit):
    base = T2.downstream(G, row, wit)                       # CTX chain / all decoders / ORD limit sites
    eng = row["engine"]
    fam = row["sig"].split("|")[1] if eng == "EC" and "|" in row["sig"] else ""
    if not (eng in ("P1", "XV") or fam in ("PT", "SW")):
        return base
    keep = set()
    ks = kinds_of(card, row)
    if "迁移项" in ks:
        keep |= set(X3["sub"]["迁移项"])
    if ks & {"device-exclusive 项", "device-private 项", "交换项"}:
        keep |= set(X3["sub"]["swap"])
    if ks & {"uffd-wp 标记", "guard 标记", "hwpoison 标记"}:
        keep |= set(X3["sub"]["marker"])
    if fam == "SW":
        for d in (card["资源与性质"].get("expected_actual") or []):
            key = d["key"] if isinstance(d, dict) else ""
            for tok in key.split(">")[1:]:
                tok = tok.split("|")[0]
                if tok in G["defs"]:
                    keep.add(tok)
                    keep |= {c for c, dd in T.callees(G, [tok], 1)}
    pts = []
    for n in sorted(keep):
        pts += T.warns_in(G, n, "后果处：与前置状态有关的解码点", cap=4)
    pts.sort(key=lambda p: (0 if p["kind"] in T2.ERRK else 1, p["file"], p["line"]))
    seen, res = set(), []
    for p in pts:
        k = (p["file"], p["line"])
        if k not in seen:
            seen.add(k)
            res.append(p)
    return res[:30]


def card3(G, row, recs, ec, ord_hz, wit):
    row = fix_row(row)
    c = T2.card2(G, row, Recs(recs, row), ec, ord_hz, wit)
    c["观测点"]["consequence"] = consequence(G, c, row, wit)
    c["观测点"]["points"] = c["观测点"]["near"] + c["观测点"]["consequence"]
    srcs, how = producers(G, c, row)
    if srcs:
        ents, n, _ = entries(G, sorted(srcs), {k: PRE_CAP for k in T2.CAP})
        c["前置状态入口"] = {"producers": sorted(srcs)[:20], "n_producers": len(srcs), "how": how, "entries": ents, "n_entries": n}
        c["自动程度"]["前置状态入口"] = "半自动（按产生者表）"
    else:
        c["前置状态入口"] = "需人工"
        c["自动程度"]["前置状态入口"] = "需人工"
    return c


PRE_GOLD = {"A": ["sys_move_pages"], "B": ["dmirror_fops_unlocked_ioctl"], "C": ["dmirror_fops_unlocked_ioctl"],
            "H": ["dmirror_fops_unlocked_ioctl"], "D": ["userfaultfd_ioctl"], "F": ["split_huge_pages_write"],
            "G": ["sys_mprotect", "vfio_pci_mmap_huge_fault"], "I": ["debug_vm_pgtable"]}


def run():
    T.reach = reach3
    G = T.build_graph()
    T2.extras(G)
    extras3(G)
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
    wit = T2.ctx_witness()
    cards = {}
    (HERE / "cards").mkdir(exist_ok=True)
    for r in rows:
        c = card3(G, r, recs, ec, ord_hz, wit)
        cards[r["no"]] = c
        json.dump(c, open(HERE / "cards" / f"{r['no']:05d}.json", "w"), ensure_ascii=False, indent=1)
    gold = T2.check(cards, [fix_row(r) for r in rows])
    for g in gold:
        c = cards.get(g["row"])
        want = PRE_GOLD.get(g["id"])
        pe = c["前置状态入口"] if c else "需人工"
        if want is None:
            g["P3"] = "不算"
        elif isinstance(pe, str):
            g["P3"] = False
        else:
            hit = next((e for e in pe["entries"] if e["entry"] in want or any(x in want for x in e["path"])), None)
            g["P3"] = hit is not None
            g["P3_entry"] = hit["entry"] if hit else None
            g["P3_listed"] = [e["entry"] for e in pe["entries"]][:20]
    json.dump({g["id"]: cards.get(g["row"]) for g in gold if g.get("row")}, open(HERE / "cards_gold.json", "w"), ensure_ascii=False, indent=1)
    t4 = [o for g in gold for o in g["T4"]]
    main = [c for no, c in cards.items() if no < 10000]
    # overlap of consequence points between rows (criteria 二 N)
    sets_ = [frozenset((p["file"], p["line"]) for p in c["观测点"]["consequence"]) for c in main if c["观测点"]["consequence"]]
    same = Counter(sets_)
    noise = {"entries_avg": round(sum(len(c["到达路径"]["entries"]) for c in main) / len(main), 1),
             "obs_near_avg": round(sum(len(c["观测点"]["near"]) for c in main) / len(main), 1),
             "obs_conseq_avg": round(sum(len(c["观测点"]["consequence"]) for c in main) / len(main), 1),
             "conseq_distinct_lists": len(same), "conseq_rows": len(sets_), "largest_identical_group": max(same.values()) if same else 0}
    auto = defaultdict(Counter)
    for c in main:
        for k, v in c["自动程度"].items():
            auto[k][v.split("（")[0]] += 1
    res = {"P1": sum(g["T3"] for g in gold), "P2": {"matched": sum(o["ok"] for o in t4), "n": len(t4)},
           "P3": {"ok": sum(g.get("P3") is True for g in gold), "n": sum(g.get("P3") != "不算" for g in gold)},
           "P4": all(g["T1"] and g["T2"] for g in gold), "N": noise, "gold": gold,
           "automation": {k: dict(v) for k, v in auto.items()}, "cards": len(cards)}
    json.dump(res, open(HERE / "result.json", "w"), ensure_ascii=False, indent=1)
    for g in gold:
        print("GOLD", g["id"], "T1", g["T1"], "T2", g["T2"], "T3", g["T3"], g["T3_entry"], "T4",
              [(o["gold"], o["ok"], (o["where"] or "")[:20]) for o in g["T4"]], "P3", g.get("P3"), g.get("P3_entry"),
              "sizes", g["n_entries"], g["n_obs_near"], g["n_obs_conseq"], flush=True)
    print("P1", res["P1"], "/", len(gold), "P2", res["P2"], "P3", res["P3"], "P4", res["P4"], "N", noise)


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    {"run": run}[sys.argv[1]]()
