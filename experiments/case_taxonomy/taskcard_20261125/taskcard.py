"""taskcard criteria 一-四: dynamic-verification task cards for every row of the nine-engine main table (task4_20261125), and the
check against six dynamic experiments (criteria 三). Read-only. WSL.

    python3 taskcard.py run     -> /root/work/taskcard/graph.pkl (call graph cache), cards/<no>.json, cards_gold.json, result.json
"""
import gzip
import json
import os
import pickle
import re
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
SRC = Path("/root/repos/linux")
W = Path("/root/work/task4")
WT = Path("/root/work/taskcard")
REV = "df2908090cda368b01ff43709f51890076c56157"
BUILDS = ("riscv", "arm64", "x86_64", "arm", "powerpc")
IDENT = re.compile(r"[A-Za-z_]\w*")
sys.path.insert(0, str(CT / "bres_20261125"))
import layer_r as LR  # noqa: E402   (strip_code only)

USER_TYPES = {"file_operations", "proc_ops", "seq_operations", "cftype", "kernfs_ops", "vm_operations_struct",
              "kobj_attribute", "device_attribute", "attribute"}
KEYW = set("if for while switch return sizeof typeof __typeof__ do else case goto break continue defined".split())
WARN = re.compile(r"\b(WARN|WARN_ON|WARN_ON_ONCE|WARN_ONCE|BUG|BUG_ON|VM_WARN_ON|VM_WARN_ON_ONCE|VM_WARN_ONCE|VM_WARN_ON_FOLIO|"
                  r"VM_WARN_ON_ONCE_FOLIO|VM_WARN_ON_ONCE_PAGE|VM_BUG_ON|VM_BUG_ON_PAGE|VM_BUG_ON_FOLIO|VM_BUG_ON_VMA|VM_BUG_ON_MM|"
                  r"pr_err|pr_warn|pr_crit|pr_alert|pr_emerg|pr_err_ratelimited|pr_warn_ratelimited|printk|pte_ERROR|pmd_ERROR|"
                  r"pud_ERROR|p4d_ERROR|pgd_ERROR)\s*\(")
STRUCT_INIT = re.compile(r"struct\s+(\w+)\s+(?:(?:const|__\w+(?:\([^)]*\))?)\s+)*(\w+)\s*(\[[^\]]*\])?\s*(?:__\w+(?:\([^)]*\))?\s*)*=\s*\{")
ATTR_MAC = re.compile(r"(\w+)\s*=\s*__ATTR(_RW|_RO|_WO)?\s*\(\s*(\w+)\s*(?:,\s*[^,]+,\s*(\w+)\s*,\s*(\w+))?")
DEV_ATTR = re.compile(r"\bDEVICE_ATTR(_RW|_RO|_WO)?\s*\(\s*(\w+)")
SETUP = re.compile(r"\b(__setup|early_param)\s*\(\s*\"[^\"]*\"\s*,\s*(\w+)\s*\)")


# ------------------------------------------------------------------ source helpers
_raw, _strip = {}, {}


def raw(f):
    if f not in _raw:
        try:
            _raw[f] = (SRC / f).read_text(errors="replace").split("\n")
        except OSError:
            _raw[f] = []
    return _raw[f]


def stripped(f):
    if f not in _strip:
        _strip[f] = LR.strip_code("\n".join(raw(f))).split("\n")
    return _strip[f]


def ifstack(f, ln):
    """enclosing #if conditions at line ln (raw text, comments stripped)"""
    st = []
    for i, l in enumerate(stripped(f)[:ln], 1):
        m = re.match(r"\s*#\s*(if|ifdef|ifndef|elif|else|endif)\b(.*)", l)
        if not m:
            continue
        k, c = m.group(1), m.group(2).strip()
        if k in ("if", "ifdef", "ifndef"):
            st.append([k, c, i])
        elif k in ("elif", "else") and st:
            st[-1] = [k + "（接 " + st[-1][0] + " " + st[-1][1] + "）", c, i]
        elif k == "endif" and st:
            st.pop()
    return [{"cond": f"#{k} {c}".strip(), "line": i, "configs": sorted(set(re.findall(r"CONFIG_(\w+)", k + " " + c)))}
            for k, c, i in st if re.search(r"CONFIG_\w+", k + " " + c)]


_mk = {}


def makefile_chain(f):
    """criteria 一 触发配置: CONFIG symbols on the Makefile/Kbuild lines naming the object, then each parent directory"""
    if f in _mk:
        return _mk[f]
    out = []
    if f.endswith(".c"):
        d, name = os.path.dirname(f), os.path.basename(f)[:-2] + ".o"
        while d:
            for mk in ("Makefile", "Kbuild"):
                p = SRC / d / mk
                if not p.exists():
                    continue
                txt = p.read_text(errors="replace").replace("\\\n", " ")
                for l in txt.split("\n"):
                    if re.search(r"(^|[\s=])" + re.escape(name) + r"(\s|$)", l) and not l.lstrip().startswith("#"):
                        cs = re.findall(r"CONFIG_(\w+)", l)
                        out.append({"makefile": f"{d}/{mk}", "line": l.strip()[:120], "configs": sorted(set(cs))})
            name = os.path.basename(d) + "/"
            d = os.path.dirname(d)
        for mk in ("Makefile", "Kbuild"):                     # top level
            p = SRC / mk
            if p.exists():
                for l in p.read_text(errors="replace").replace("\\\n", " ").split("\n"):
                    if re.search(r"(^|[\s=])" + re.escape(name) + r"(\s|$)", l) and not l.lstrip().startswith("#"):
                        out.append({"makefile": mk, "line": l.strip()[:120], "configs": sorted(set(re.findall(r"CONFIG_(\w+)", l)))})
    _mk[f] = out
    return out


# ------------------------------------------------------------------ call graph (criteria 二)
def build_graph():
    WT.mkdir(exist_ok=True)
    gp = WT / "graph2.pkl"                                     # amendment 1: graph2 (graph.pkl kept as the run-1 cache)
    if gp.exists():
        with open(gp, "rb") as fh:
            return pickle.load(fh)
    import bisect
    E = json.load(gzip.open(W / "funcs.json.gz", "rt"))
    defs = defaultdict(list)                                   # node name -> [(file, start, end, label, static)]
    seen = set()
    franges = defaultdict(list)                                # file -> sorted (start, end) of every function definition
    for e in E:
        if e["kind"] != "func" or (e["file"], e["start"]) in seen:
            continue
        seen.add((e["file"], e["start"]))
        franges[e["file"]].append((e["start"], e["end"]))
        if not e["builds"]:
            continue
        name = e["name"]
        m = re.match(r"(COMPAT_)?SYSCALL_DEFINE\d", name)
        if m:
            hdr = " ".join(raw(e["file"])[e["start"] - 1:e["start"] + 1])
            mm = re.search(r"SYSCALL_DEFINE\d\s*\(\s*(\w+)", hdr)
            if mm:
                name = ("compat_sys_" if m.group(1) else "sys_") + mm.group(1)
        defs[name].append((e["file"], e["start"], e["end"], e["label"], e["static"]))
    for f in franges:
        franges[f].sort()

    def in_func(f, ln):
        rs = franges.get(f, [])
        i = bisect.bisect_right(rs, (ln, 10 ** 9)) - 1
        return i >= 0 and rs[i][0] <= ln <= rs[i][1]
    files = sorted({d[0] for v in defs.values() for d in v})
    reg = defaultdict(list)          # var key -> [(field, func, type, file)]
    vtype, var2ids, setup = {}, {}, {}
    fvars = defaultdict(dict)        # file -> {name: key} (static vars of this file)
    gvars = {}                       # name -> key (non-static vars)
    GLOB = set()
    DECL = re.compile(r"\s*(?:static\s+)?(?:const\s+|volatile\s+|__read_mostly\s+)*(?:unsigned\s+|signed\s+)?"
                      r"(?:int|long|bool|char|short|u8|u16|u32|u64|s32|s64|unsigned|atomic_t|atomic_long_t|enum\s+\w+)\b"
                      r"[\w\s\*]*?\b([A-Za-z_]\w*)\s*(?:\[[^\]]*\])?\s*(?:__\w+(?:\([^)]*\))?\s*)*(?:=|;)")
    for f in files:
        lines = stripped(f)
        txt = "\n".join(lines)
        depth = 0                                              # amendment 1.3: file-scope variables and static keys
        for i, l in enumerate(lines, 1):
            if depth == 0 and not in_func(f, i):
                m = DECL.match(l)
                if m and "(" not in l.split(m.group(1))[0]:
                    GLOB.add(m.group(1))
                for mm in re.finditer(r"\bDEFINE_STATIC_KEY_\w*\s*\(\s*(\w+)", l):
                    GLOB.add(mm.group(1))
            depth = max(depth + l.count("{") - l.count("}"), 0)
        for m in STRUCT_INIT.finditer(txt):
            ln = txt.count("\n", 0, m.start()) + 1
            if in_func(f, ln):                                 # amendment 1.1: local initializers make no node
                continue
            typ, var = m.group(1), m.group(2)
            pre = txt[max(0, m.start() - 60):m.start()].split("\n")[-1]
            key = f"{f}::{var}" if "static" in pre else var
            if key == var:
                gvars[var] = key
            else:
                fvars[f][var] = key
            i, d = m.end() - 1, 0
            j = i
            while j < len(txt):
                c = txt[j]
                d += c == "{"
                d -= c == "}"
                if d == 0:
                    break
                j += 1
            body = txt[i:j + 1]
            vtype[key] = typ
            for fm in re.finditer(r"\.(\w+)\s*=\s*&?\s*(\w+)", body):
                if fm.group(2) in defs:
                    reg[key].append((fm.group(1), fm.group(2), typ, f))
            var2ids[key] = (f, set(IDENT.findall(body)))
        for m in ATTR_MAC.finditer(txt):
            var, kind, nm = m.group(1), m.group(2), m.group(3)
            key = f"{f}::{var}"
            if kind:
                for suf, fld in (("_show", "show"), ("_store", "store")):
                    if (kind == "_RW" or (kind == "_RO" and suf == "_show") or (kind == "_WO" and suf == "_store")) and nm + suf in defs:
                        reg[key].append((fld, nm + suf, "kobj_attribute", f))
            else:
                for fn, fld in ((m.group(4), "show"), (m.group(5), "store")):
                    if fn and fn in defs:
                        reg[key].append((fld, fn, "kobj_attribute", f))
            vtype[key] = "kobj_attribute"
        for m in DEV_ATTR.finditer(txt):
            kind, nm = m.group(1) or "", m.group(2)
            key = f"{f}::dev_attr_{nm}"
            for suf, fld in (("_show", "show"), ("_store", "store")):
                if nm + suf in defs and (kind in ("_RW", "") or (kind == "_RO" and suf == "_show") or (kind == "_WO" and suf == "_store")):
                    reg[key].append((fld, nm + suf, "device_attribute", f))
            vtype[key] = "device_attribute"
        for m in SETUP.finditer(txt):
            setup[m.group(2)] = m.group(1)

    def resolve(f, x):
        return fvars.get(f, {}).get(x) or gvars.get(x)
    fwd = defaultdict(set)
    greads, gwrites = defaultdict(set), defaultdict(set)
    ASSIGN = re.compile(r"\b([A-Za-z_]\w*)\s*(?:\[[^\]]*\])?\s*(?:=(?!=)|\|=|&=|\+=|-=)")
    BITOP = re.compile(r"\b(?:set_bit|clear_bit|change_bit|static_branch_enable|static_branch_disable|static_branch_enable_cpuslocked|"
                       r"static_branch_disable_cpuslocked|static_key_enable|static_key_disable|static_branch_inc|static_branch_dec)\s*\(([^;]*)\)")
    for name, ds in defs.items():
        for f, a, b, lab, st in ds:
            body = "\n".join(stripped(f)[a - 1:b])
            calls = {m.group(1) for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", body)} - KEYW
            ids = set(IDENT.findall(body))
            for c in calls:
                if c in defs and c != name:
                    fwd[name].add((c, "调用"))
            for c in ids - calls:
                if c in defs and c != name:
                    fwd[name].add((c, "函数指针"))
                else:
                    k = resolve(f, c)
                    if k and vtype.get(k) not in USER_TYPES:       # amendment 1.2
                        fwd[name].add(("var:" + k, "引用结构"))
            for x in ids & GLOB:
                greads[x].add(name)
            for m in ASSIGN.finditer(body):
                if m.group(1) in GLOB:
                    gwrites[m.group(1)].add(name)
            for m in BITOP.finditer(body):
                for x in set(IDENT.findall(m.group(1))) & GLOB:
                    gwrites[x].add(name)
    for k, lst in reg.items():
        for fld, fn, typ, f in lst:
            fwd["var:" + k].add((fn, f"登记在 {k.split('::')[-1]}.{fld}"))
    for k, (f, ids) in var2ids.items():
        for x in ids:
            k2 = resolve(f, x)
            if k2 and k2 != k and vtype.get(k2) not in USER_TYPES:
                fwd["var:" + k].add(("var:" + k2, "结构内引用"))
    rev = defaultdict(set)
    for a, ss in fwd.items():
        for b, k in ss:
            rev[b].add((a, k))
    regtype = defaultdict(set)
    for k, lst in reg.items():
        for fld, fn, typ, f in lst:
            regtype[fn].add((typ, k.split("::")[-1], fld))
    G = {"defs": dict(defs), "fwd": dict(fwd), "rev": dict(rev), "regtype": dict(regtype), "setup": setup, "vtype": vtype,
         "glob": GLOB, "greads": dict(greads), "gwrites": dict(gwrites)}
    with open(gp, "wb") as fh:
        pickle.dump(G, fh)
    print("graph: nodes", len(defs), "struct vars", len(vtype), "globals", len(GLOB), "edges", sum(map(len, fwd.values())), flush=True)
    return G


def entry_kind(G, n):
    if n.startswith(("sys_", "compat_sys_")) and n in G["defs"]:
        return 0, "系统调用"
    rt = [x for x in G["regtype"].get(n, ()) if x[0] in USER_TYPES]
    if rt:
        t, v, fld = sorted(rt)[0]
        return 1, f"回调：{t} {v}.{fld}"
    ds = G["defs"].get(n, [])
    if ds and all(d[0].startswith("arch/") for d in ds) and not any(not p.startswith("var:") for p, _ in G["rev"].get(n, ())):
        return 2, "架构入口（没有 C 调用者）"
    return None


def reach(G, sources, maxd=16, cap=20):
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
    ents = []
    for n, d in dist.items():
        ek = entry_kind(G, n)
        if ek:
            ents.append((ek[0], d, n, ek[1]))
    ents.sort()

    def path(n):
        out = [n]
        while n in par:
            n2, k = par[n]
            out.append(f"—{k}→")
            out.append(n2)
            n = n2
        return out
    return [{"entry": n, "kind": k, "depth": d, "path": [x for x in path(n) if not x.startswith("var:") or True]} for _, d, n, k in ents[:cap]], \
        len(ents), len(dist)


def callees(G, srcs, depth=3):
    out, frontier, seen = [], list(srcs), set(srcs)
    for d in range(1, depth + 1):
        nxt = []
        for n in frontier:
            for c, k in G["fwd"].get(n, ()):
                if k == "调用" and c not in seen:
                    seen.add(c)
                    nxt.append(c)
                    out.append((c, d))
        frontier = nxt
    return out


def warns_in(G, name, why, cap=12):
    out = []
    for f, a, b, lab, st in G["defs"].get(name, [])[:3]:
        for i, l in enumerate(stripped(f)[a - 1:b], a):
            m = WARN.search(l)
            if m:
                out.append({"func": name, "file": f, "line": i, "kind": m.group(1), "text": raw(f)[i - 1].strip()[:100], "why": why})
                if len(out) >= cap:
                    return out
    return out


# ------------------------------------------------------------------ rule tables (criteria 一 半自动)
NP_KINDS = {
    "pte": [("交换项", "SWAP"), ("迁移项", "MIGRATION"), ("device-private 项", "DEVICE_PRIVATE"), ("device-exclusive 项", "DEVICE_PRIVATE"),
            ("uffd-wp 标记", "PTE_MARKER_UFFD_WP"), ("hwpoison 标记", "MEMORY_FAILURE"), ("guard 标记（MADV_GUARD_INSTALL）", "MMU")],
    "pmd": [("THP 迁移项", "ARCH_ENABLE_THP_MIGRATION"), ("device-private PMD 项", "DEVICE_PRIVATE")],
    "pud": [],
}
PLATFORM = {"NUMA": "多个 NUMA 节点（QEMU -numa node,...）", "FS_DAX": "持久内存：内核参数 memmap=nn!ss，再建 DAX 文件系统",
            "LIBNVDIMM": "持久内存：内核参数 memmap=nn!ss", "VFIO_PCI": "PCI 设备 BAR：如 QEMU ivshmem-plain + vfio-pci（no-IOMMU）",
            "ARCH_SUPPORTS_PUD_PFNMAP": "1GB 的 PFN 映射：如 VFIO 设备 BAR", "DEVICE_PRIVATE": "HMM 测试模块 lib/test_hmm（TEST_HMM）",
            "MEMCG": "cgroup v2（memory 控制器）", "SWAP": "交换设备（如 zram）", "ARM_LPAE": "arm LPAE：QEMU virt,highmem=on，大物理地址内存",
            "ARM64_64K_PAGES": "arm64 64K 页内核：QEMU -cpu cortex-a72，大内存（≥ 4G）", "USERFAULTFD": "用户态 userfaultfd（root 或 vm.unprivileged_userfaultfd）"}


def iface_level(name):
    m = re.match(r"(pte|pmd|pud)_", name or "")
    return m.group(1) if m else None


# ------------------------------------------------------------------ one card
def card(G, row, recs_by_iface, ec, ord_hz):
    eng, f, ln, fn, sig = row["engine"], row["file"], row["line"], row["func"], row["sig"]
    ev = row["evidence"]
    auto = {}
    # 定位
    if eng == "EC":
        cons = recs_by_iface.get(fn, [])
        consumers = sorted({(r["F"]["file"], r["F"]["name"], r["line"]) for r in cons})
    else:
        consumers = sorted({(e["F"].split(" ")[0].rsplit(":", 1)[0], e["F"].split(" ", 1)[1], e["line"]) for e in ev}) or [(f, fn, ln)]
    binds = defaultdict(set)
    for e in ev:
        binds[e["build"]].add(e["bind"])
    loc = {"rev": REV, "report": f"{f}:{ln} {fn}", "engine": eng, "consumers": [f"{a}:{c} {b}" for a, b, c in consumers[:30]],
           "n_consumers": len(consumers), "bindings": {b: sorted(v)[:2] for b, v in binds.items()}}
    auto["定位"] = "自动"
    # 资源与性质
    res = {"resource": row.get("resource", ""), "property": row.get("prop", ""), "ok_if": row.get("ok_if", "")}
    devs = []
    if eng == "EC":
        dbs = re.search(r"构建 ([\w,]+)", sig)
        dbs = dbs.group(1).split(",") if dbs else []
        fam = sig.split("|")[1] if "|" in sig else ""
        devs = [d for d in ec["devs"] if d["key"].split("|")[0] == fam and d["build"] in dbs]          # amendment 1.4
        devs = sorted(devs, key=lambda d: fn not in IDENT.findall(d["key"]))[:5]
        res["expected_actual"] = [{"key": d["key"], "多数": d.get("majority"), "偏离构建": d["build"], "偏离值": d.get("deviant_norm", d.get("deviant")),
                                   "截断": d.get("truncation"), "位数": d.get("nbits")} for d in devs]
        auto["资源与性质"] = "自动"
    elif eng == "ORD":
        srcs = [s for s in sig.split("|") if s]
        res["expected_actual"] = [{"来源": s, "期望": "阶数 ≤ MAX_PAGECACHE_ORDER", "违例组合": ord_hz.get(s, {}).get("M", [])} for s in srcs]
        auto["资源与性质"] = "自动"
    elif eng in ("P1", "XV"):
        res["expected_actual"] = "期望：调用时页表项是 present 项；实际：可能传入非 present 项（引擎判为未受保护）"
        auto["资源与性质"] = "自动"
    else:
        auto["资源与性质"] = "半自动（只有主表三列）"
    # 触发配置
    pts = [(f, ln)] + [(a, c) for a, b, c in consumers[:10]]
    comp = []
    for a, c in pts:
        if not raw(a):
            continue
        comp.append({"at": f"{a}:{c}", "ifs": ifstack(a, c), "makefile": makefile_chain(a)})
    comp_cfg = sorted({x for p in comp for g in p["ifs"] + p["makefile"] for x in g["configs"]})
    # 到达路径
    srcn = sorted({b for a, b, c in consumers})
    ents, n_ent, n_reach = reach(G, srcn)
    auto["到达路径"] = "自动（近似）" if ents else "需人工（找不到入口）"
    path_funcs = []
    for e in ents[:3]:
        for x in e["path"]:
            if not x.startswith(("—", "var:")) and x not in path_funcs:
                path_funcs.append(x)
    path_cfg = defaultdict(set)
    for n in path_funcs:
        for pf, a, b, lab, st in G["defs"].get(n, [])[:1]:
            for g in ifstack(pf, a) + makefile_chain(pf):
                for x in g["configs"]:
                    path_cfg[x].add(n)
    trig = {"compile": comp, "compile_configs": comp_cfg, "path_configs": {k: sorted(v)[:3] for k, v in sorted(path_cfg.items())}}
    auto["触发配置"] = "自动"
    # 运行时开关 (amendment 1.3)
    def user_writer(w):
        return any(t[0] in ("kobj_attribute", "device_attribute", "attribute") and t[2] == "store" for t in G["regtype"].get(w, ())) \
            or w in G["setup"]
    sw = []
    for n in ([fn] if eng != "EC" else []) + srcn[:5] + path_funcs[:8]:
        for pf, a, b, lab, st in G["defs"].get(n, [])[:1]:
            body = "\n".join(stripped(pf)[a - 1:b])
            for cm in re.finditer(r"\bif\s*\((.*)\)", body):
                cond = cm.group(1)
                cands = [(x, x) for x in set(IDENT.findall(cond)) if x in G["glob"]]
                for x in set(re.findall(r"\b([A-Za-z_]\w*)\s*\(\s*\)", cond)):
                    if x in G["defs"]:
                        for y in sorted(k for k, v in G["greads"].items() if x in v)[:5]:
                            cands.append((f"{x}()（读 {y}）", y))
                for label, y in cands:
                    wr = []
                    for w in G["gwrites"].get(y, ()):
                        if user_writer(w):
                            wr.append(w)
                        else:
                            wr += [p for p, k in G["rev"].get(w, ()) if k == "调用" and user_writer(p)]
                    if wr:
                        sw.append({"read_in": n, "switch": label, "writers": sorted(set(wr))[:3]})
    seen_sw, sw2 = set(), []
    for s_ in sw:
        if s_["switch"] not in seen_sw:
            seen_sw.add(s_["switch"])
            sw2.append(s_)
    auto["运行时开关"] = "半自动" if sw2 else "需人工（没找到 sysfs / 启动参数开关）"
    # 前置状态
    pre = {}
    if eng in ("P1", "XV"):
        parts = sig.split("|")
        A = parts[0] if eng == "P1" else parts[1] if parts[0] == "dom" else parts[2]
        lv = iface_level(A)
        pre = {"needs": f"调用 {A} 时页表项不 present", "kinds": [{"kind": k, "config": c} for k, c in NP_KINDS.get(lv or "", [])],
               "guards": sorted({g for e in ev for g in e["guards"]})[:6]}
        auto["前置状态"] = "半自动（按页表级别查表）" if pre["kinds"] else "需人工"
    elif eng == "EC":
        pre = {"needs": [d["key"] for d in devs[:3]],
               "note": "按偏离的输入组合构造页表项" + ("；偏离是截断：需要值超过偏离构建的编码位数" if any(d.get("truncation") for d in devs) else "")}
        auto["前置状态"] = "半自动（取偏离的输入组合）" if devs else "需人工"
    elif eng == "ORD":
        pre = {"needs": "页大小较大的配置，使阶数超过 MAX_PAGECACHE_ORDER",
               "combos": sorted({c for s in sig.split("|") for c in ord_hz.get(s, {}).get("M", [])})}
        auto["前置状态"] = "半自动"
    else:
        auto["前置状态"] = "需人工"
    # 观测点
    obs = []
    for n in srcn[:10]:
        obs += warns_in(G, n, "公共消费函数里")
    for c, d in callees(G, srcn[:10], 3):
        if any(not x[0].startswith("arch/") for x in G["defs"].get(c, [])):
            obs += warns_in(G, c, f"消费函数往下第 {d} 层", cap=4)
    for n in path_funcs:
        obs += warns_in(G, n, "到达路径上", cap=4)
    seen_o, obs2 = set(), []
    for o in obs:
        k2 = (o["file"], o["line"])
        if k2 not in seen_o:
            seen_o.add(k2)
            obs2.append(o)
    dbg = sorted({"DEBUG_VM" for o in obs2 if o["kind"].startswith("VM_")})
    auto["观测点"] = "半自动" if obs2 else "需人工"
    # 差分对照
    if eng == "EC":
        dbs = re.search(r"构建 ([\w,]+)", sig)
        dbs = dbs.group(1).split(",") if dbs else []
        diff = {"deviant": dbs, "normal": [b for b in ec["builds"] if b not in dbs], "source": "EC 实现对照组"}
        auto["差分对照"] = "自动"
    elif eng == "ORD":
        bad = sorted({c for s in sig.split("|") for c in ord_hz.get(s, {}).get("M", [])})
        allc = sorted({c for s in sig.split("|") for c in ord_hz.get(s, {}).get("avail", [])})
        same_arch_ok = sorted({c for c in allc if c not in bad and c.split("-")[0] in {b.split("-")[0] for b in bad}})
        diff = {"deviant": bad, "normal": same_arch_ok, "source": "ORD 违例组合；正常取同架构的不违例组合"}
        auto["差分对照"] = "自动" if bad else "需人工"
    else:
        diff = {"deviant": "需人工（引擎不判断哪个架构出错）",
                "bindings_differ": len({tuple(sorted(v)) for v in binds.values()}) > 1, "bindings": {b: sorted(v)[:1] for b, v in binds.items()}}
        auto["差分对照"] = "需人工"
    # 平台需求
    allcfg = set(comp_cfg) | set(path_cfg) | ({k["config"] for k in pre.get("kinds", [])} if isinstance(pre, dict) else set())
    if eng == "ORD" and any("arm64-64k" in c for c in pre.get("combos", [])):
        allcfg.add("ARM64_64K_PAGES")
    if eng == "EC" and any(b.startswith("arm_lpae") for b in diff.get("deviant", [])):
        allcfg.add("ARM_LPAE")
    plat = [{"config": c, "need": PLATFORM[c]} for c in sorted(allcfg) if c in PLATFORM]
    auto["平台需求"] = "半自动（按配置查表）" if plat else "需人工"
    return {"no": row["no"], "定位": loc, "资源与性质": res, "触发配置": trig,
            "到达路径": {"entries": ents, "n_entries": n_ent, "n_reached": n_reach},
            "运行时开关": sw2[:10] or "需人工", "前置状态": pre or "需人工", "观测点": {"points": obs2[:40], "n": len(obs2), "debug_configs": dbg},
            "差分对照": diff, "平台需求": plat or "需人工", "自动程度": auto}


# ------------------------------------------------------------------ gold (criteria 三)
GOLD = [
    {"id": "A", "exp": "p1dyn S1", "engine": "P1", "file": "fs/proc/task_mmu.c", "line": 1129, "func": "smaps_pmd_entry", "sig": "pmd_young",
     "entry": "show_smap", "cfg": {"PROC_FS", "MMU", "PROC_PAGE_MONITOR", "TRANSPARENT_HUGEPAGE"}, "diff": None, "obs": [],
     "pre": ["迁移项"], "switch": [], "plat": ["NUMA"]},
    {"id": "B", "exp": "p1dyn S2", "engine": "XV", "file": "mm/rmap.c", "line": 986, "func": "folio_referenced_one", "sig": None,
     "entry": "memory_reclaim", "cfg": {"MMU"}, "diff": None, "obs": [("get_swap_device", None)],
     "pre": ["device-exclusive"], "switch": [], "plat": ["DEVICE_PRIVATE", "MEMCG", "SWAP"]},
    {"id": "C", "exp": "s4dyn", "engine": "XV", "file": "mm/vmscan.c", "line": 4279, "func": "lru_gen_look_around", "sig": None,
     "entry": "memory_reclaim", "cfg": {"LRU_GEN"}, "diff": None, "obs": [("get_swap_device", None)],
     "pre": ["device-exclusive"], "switch": ["lru_gen"], "plat": ["DEVICE_PRIVATE", "MEMCG", "SWAP"]},
    {"id": "D", "exp": "s3dyn", "engine": "P1", "file": "mm/memory.c", "line": 2495, "func": "insert_page_into_pte_locked", "sig": None,
     "entry": "handle_mm_fault", "cfg": {"MMU"}, "diff": None, "obs": [("insert_page_into_pte_locked", None)],
     "pre": ["uffd-wp"], "switch": [], "plat": ["FS_DAX", "LIBNVDIMM"]},
    {"id": "E", "exp": "s6dyn", "engine": "ORD", "file": "mm/shmem.c", "line": 1942, "func": "shmem_alloc_and_add_folio", "sig": None,
     "entry": "shmem_fault", "cfg": {"SHMEM"}, "diff": ({"arm64-64k"}, {"arm64-4k"}), "obs": [("xas_split_alloc", "lib/xarray.c:1051")],
     "pre": ["arm64-64k"], "switch": ["shmem_huge"], "plat": ["ARM64_64K_PAGES"]},
    {"id": "F", "exp": "lpaeqemu", "engine": "EC", "file": "arch/arm/include/asm/pgtable.h", "line": 289, "func": "__swp_entry", "sig": "arm_lpae",
     "entry": "split_huge_pages_write", "cfg": {"MMU"}, "diff": ({"arm_lpae"}, None),
     "obs": [(None, "include/linux/leafops.h:400"), ("softleaf_entry_wait_on_locked", None)],
     "pre": ["截断"], "switch": ["transparent_hugepage"], "plat": ["ARM_LPAE"]},
    {"id": "G", "exp": "rvpud", "engine": "EC", "file": "arch/riscv/include/asm/pgtable-64.h", "line": 192, "func": "pud_leaf", "sig": "riscv64_thp",
     "entry": "sys_mprotect", "cfg": set(), "diff": ({"riscv64_thp"}, None), "obs": [("pud_clear_bad", None)],
     "pre": ["PAGE_NONE"], "switch": [], "plat": ["VFIO_PCI", "ARCH_SUPPORTS_PUD_PFNMAP"]},
]


def pick(rows, g):
    c = [r for r in rows if r["engine"] == g["engine"] and r["file"] == g["file"] and r["line"] == g["line"] and r["func"] == g["func"]
         and (g["sig"] is None or g["sig"] in r["sig"])]
    return c[0] if c else None


def check_gold(cards, rows):
    res = []
    for g in GOLD:
        r = pick(rows, g)
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
        ents = [e["entry"] for e in c["到达路径"]["entries"]]
        t3 = g["entry"] in ents or any(g["entry"] in e["path"] for e in c["到达路径"]["entries"])
        pts = c["观测点"]["points"]
        omatch = []
        for fnm, fl in g["obs"]:
            ok = any((fnm and p["func"] == fnm) or (fl and f'{p["file"]}:{p["line"]}' == fl) for p in pts)
            omatch.append({"gold": fnm or fl, "ok": ok})
        txt = json.dumps(c["前置状态"], ensure_ascii=False) + json.dumps(c["运行时开关"], ensure_ascii=False)
        plat = {p["config"] for p in c["平台需求"]} if isinstance(c["平台需求"], list) else set()
        res.append({"id": g["id"], "exp": g["exp"], "row": r["no"], "T1": t1, "T1_detail": {"gold": sorted(g["cfg"]), "got": c["触发配置"]["compile_configs"]},
                    "T2": t2, "T2_detail": d if not isinstance(d.get("deviant"), str) else d["deviant"],
                    "T3": t3, "T3_entries": ents[:20], "T3_path": next((e["path"] for e in c["到达路径"]["entries"] if g["entry"] in e["path"]), None),
                    "T4": omatch, "T5_pre": {k: k in txt for k in g["pre"]}, "T5_switch": {k: k in txt for k in g["switch"]},
                    "T5_plat": {k: k in plat for k in g["plat"]}})
    return res


def run():
    G = build_graph()
    rows = json.load(open(CT / "task4_20261125" / "out" / "table.json", encoding="utf-8"))["rows"]
    recs_by_iface = defaultdict(list)
    for b in BUILDS:
        for r in json.load(gzip.open(W / f"rec_{b}.json.gz", "rt")):
            if r["kind"] in ("调用", "宏"):
                recs_by_iface[r["iface"]].append(r)
    ecd = json.load(open("/root/work/ec_cache/r10/df/df.json"))
    ec = {"devs": json.load(open("/root/work/ec_cache/r10/df/df2908090cda/deviations.json")),
          "builds": sorted(ecd.get("builds") or {d["build"] for d in json.load(open("/root/work/ec_cache/r10/df/df2908090cda/deviations.json"))})}
    sys.path.insert(0, str(CT / "orddom_20261116"))
    import orddom as O
    # ORD row sources -> base sources by ORD's own macro closure, then the violating combos of those bases
    _, sets = O.analyze(O.blobs_of(REV))
    ord_hz = {}
    for s, bases in sets["S"].items():
        hz = [O.HZ[b] for b in bases if b in O.HZ]
        ord_hz[s] = {"M": sorted({c for h in hz for c in h["M"]}), "avail": sorted({c for h in hz for c in h["avail"]}), "bases": bases}
    cards = {}
    (HERE / "cards").mkdir(exist_ok=True)
    for r in rows:
        c = card(G, r, recs_by_iface, ec, ord_hz)
        cards[r["no"]] = c
        json.dump(c, open(HERE / "cards" / f"{r['no']:03d}.json", "w"), ensure_ascii=False, indent=1)
    gold = check_gold(cards, rows)
    json.dump({g["id"]: cards.get(g["row"]) for g in gold if g.get("row")}, open(HERE / "cards_gold.json", "w"), ensure_ascii=False, indent=1)
    t4 = [o for g in gold for o in g.get("T4", [])]
    auto = defaultdict(Counter)
    for c in cards.values():
        for k, v in c["自动程度"].items():
            auto[k][v.split("（")[0]] += 1
    res = {"T1": all(g.get("T1") for g in gold), "T2": all(g.get("T2") for g in gold), "T3": all(g.get("T3") for g in gold),
           "T4": {"matched": sum(o["ok"] for o in t4), "n": len(t4), "pass": sum(o["ok"] for o in t4) >= 4},
           "gold": gold, "T6_automation": {k: dict(v) for k, v in auto.items()}, "cards": len(cards)}
    json.dump(res, open(HERE / "result.json", "w"), ensure_ascii=False, indent=1)
    for g in gold:
        print("GOLD", g["id"], g.get("exp"), "row", g.get("row"), "T1", g.get("T1"), "T2", g.get("T2"), "T3", g.get("T3"),
              "T4", [(o["gold"], o["ok"]) for o in g.get("T4", [])], "T5", g.get("T5_pre"), g.get("T5_switch"), g.get("T5_plat"), flush=True)
    print("T1", res["T1"], "T2", res["T2"], "T3", res["T3"], "T4", res["T4"])
    print("T6", json.dumps(res["T6_automation"], ensure_ascii=False))


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    {"run": run}[sys.argv[1]]()
