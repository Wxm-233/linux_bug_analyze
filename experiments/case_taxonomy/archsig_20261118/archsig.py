"""archsig criteria 一-五: commit-level mode with affected-architecture sets (config feasibility) and Fixes-based alignment.
WSL, no build. Engine candidates come from the existing caches; nothing is written into earlier rounds.

    python3 archsig.py selftest
    python3 archsig.py info <rev>       -> /root/work/commitmode_cache/ARCH/<rev>.json (feasibility per candidate file, WT/TLB arch sets)
    python3 archsig.py fixes            -> fixes_map.json (Fixes: tag -> fixing commits, history up to df2908090cda)
    python3 archsig.py runall [N]       -> missing TLB caches for Kconfig/Makefile-touching commits, then all ARCH infos, N parallel
    python3 archsig.py score            -> results.json, score.log, report/<commit>.json
"""
import json
import re
import subprocess
import sys
import time
import traceback
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
for d in ("commitmode_20261117", "commitmode_tlb_20261117", "tlbhook2_20261117", "widthtrunc3_20261117"):
    sys.path.insert(0, str(CT / d))
import commitmode as M  # noqa: E402
import dataset as DSET  # noqa: E402
import engines as E  # noqa: E402
import cmtlb as TL  # noqa: E402
import tlbhook2 as T2  # noqa: E402
import widthtrunc3 as W3  # noqa: E402

C = T2.C
HEADREV = "df2908090cda"
CACHE = Path("/root/work/commitmode_cache")
ACACHE = CACHE / "ARCH"
ENGS = ("P1", "XV", "ORD", "WT", "TLB")
XT = json.loads((CT / "xvdom_20261116" / "table2.json").read_text())["table"]
OLD = {"pte_mkuffd_wp": "pte_mkuffd", "pte_clear_uffd_wp": "pte_clear_uffd", "pmd_mkuffd_wp": "pmd_mkuffd",      # = xvdom.OLD
       "pmd_clear_uffd_wp": "pmd_clear_uffd", "pte_swp_uffd_wp": "pte_swp_uffd", "pmd_swp_uffd_wp": "pmd_swp_uffd",
       "pte_swp_mkuffd_wp": "pte_swp_mkuffd", "pte_swp_clear_uffd_wp": "pte_swp_clear_uffd",
       "pmd_swp_mkuffd_wp": "pmd_swp_mkuffd", "pmd_swp_clear_uffd_wp": "pmd_swp_clear_uffd"}
CONSTS = json.loads((CT / "orddom_20261116" / "consts.json").read_text())


def arch_dir(a):
    return {"x86_64": "x86", "i386": "x86"}.get(a, a)


# ---------------------------------------------------------------- 一 config feasibility
def parse_kconfig(src):
    """copy of widthtrunc3.parse_kconfig; amendment 1 changes only the default / def_bool parsing"""
    conj = W3._conj
    recs, ifs, cur, in_help = [], [], None, False
    for raw in src.replace("\\\n", " ").split("\n"):
        s = raw.strip()
        indented = raw.startswith(("\t", " "))
        if in_help:
            if not s or indented:
                continue
            in_help = False
        if not s or s.startswith("#"):
            continue
        m = re.match(r"^(menuconfig|config)\s+([A-Za-z0-9_]+)\s*$", s)
        if m:
            cur = {"sym": m.group(2), "deps": set(c for e in ifs for c in conj(e)), "prompt": False, "defaults": [], "selects": []}
            recs.append(cur)
            continue
        if not indented:
            if re.match(r"^if\s+", s):
                ifs.append(s[3:])
                cur = None
                continue
            if s == "endif":
                if ifs:
                    ifs.pop()
                cur = None
                continue
            if re.match(r"^(menu|endmenu|choice|endchoice|comment|source|mainmenu)\b", s):
                cur = None
                continue
        if cur is None:
            continue
        if re.match(r"^(help|---help---)\s*$", s):
            in_help = True
            continue
        m = re.match(r"^depends\s+on\s+(.*)$", s)
        if m:
            cur["deps"].update(conj(m.group(1)))
            continue
        if re.match(r'^(bool|tristate|int|hex|string)\s+"', s) or re.match(r"^prompt\b", s):
            cur["prompt"] = True
            continue
        m = re.match(r"^(def_bool|def_tristate|default)\s+(.+?)(?:\s+if\s+(.*))?$", s)
        if m:                                                             # amendment 1
            val, cond = m.group(2).strip(), set(conj(m.group(3))) if m.group(3) else set()
            if val in ("n", "0", '""'):
                cur["defaults"].append(("n", cond))
            elif val in ("y", "m") or val.startswith("$("):
                cur["defaults"].append(("y", cond))
            else:
                cur["defaults"].append(("y", cond | set(conj(val))))
            continue
        m = re.match(r"^select\s+([A-Za-z0-9_]+)(?:\s+if\s+(.*))?$", s)
        if m:
            cur["selects"].append((m.group(1), set(conj(m.group(2))) if m.group(2) else set()))
    return recs


class Feas:
    def __init__(self, kfiles, mfiles):
        recs = {p: parse_kconfig(s) for p, s in kfiles.items()}
        def arch_of(p):                                    # arch/<a>/...; arch/Kconfig itself is common (defines HAVE_*)
            parts = p.split("/")
            return parts[1] if parts[0] == "arch" and len(parts) >= 3 else None
        self.common = [r for p, rs in recs.items() if arch_of(p) is None for r in rs]
        self.per_arch = defaultdict(list)
        for p, rs in recs.items():
            if arch_of(p):
                self.per_arch[arch_of(p)] += rs
        self.archs = sorted(self.per_arch)
        self.flist, self.dlist = W3.Build64v3._makefiles3(mfiles)
        self._imp = {}

    def impossible(self, a):
        """一.2: fixpoint of 'impossible on a'"""
        if a in self._imp:
            return self._imp[a]
        defs, prompt, defaults, sel = defaultdict(list), defaultdict(bool), defaultdict(list), defaultdict(list)
        for r in self.common + self.per_arch.get(a, []):
            defs[r["sym"]].append(r["deps"])
            prompt[r["sym"]] |= r["prompt"]
            defaults[r["sym"]] += r["defaults"]
            for tgt, cond in r["selects"]:
                sel[tgt].append((r["sym"], cond))
        I = set()

        def imp(x):
            return x in I or x not in defs

        changed = True
        while changed:
            changed = False
            for sym, ds in defs.items():
                if sym in I:
                    continue
                if all(any(imp(x) for x in d) for d in ds):
                    I.add(sym)
                    changed = True
                    continue
                if not prompt[sym]:
                    on = any(v not in ("n", "0", '""') and not any(imp(c) for c in cond) for v, cond in defaults[sym])
                    if not on and all(imp(s) or any(imp(c) for c in cond) for s, cond in sel.get(sym, [])):
                        I.add(sym)
                        changed = True
        self._imp[a] = (I, set(defs))
        return self._imp[a]

    def feasible(self, path, a):
        m = re.match(r"arch/([^/]+)/", path)
        if m:
            return m.group(1) == a
        I, defined = self.impossible(a)

        def dead(conds):
            return any(x in I or x not in defined for x in conds)

        L = self.flist.get(path)
        if L and all(dead(c) for c in L):
            return False
        parts = path.split("/")
        for i in range(1, len(parts)):
            D = self.dlist.get("/".join(parts[:i]))
            if D and all(dead(c) for c in D):
                return False
        return True


def feas_of(rev):
    names = [p for p in C.git("ls-tree", "-r", "--name-only", rev).split("\n") if p]
    kf = [p for p in names if re.search(r"(^|/)Kconfig[^/]*$", p)]
    mf = [p for p in names if re.search(r"(^|/)(Makefile|Kbuild)$", p)]
    blobs = C.cat_files(rev, kf + mf)
    return Feas({p: blobs[p] for p in kf if p in blobs}, {p: blobs[p] for p in mf if p in blobs})


# ---------------------------------------------------------------- 二 property-broken archs per engine
def ord_archs(sources):
    out = set()
    for combo, v in CONSTS.items():
        lim = v.get("MAX_PAGECACHE_ORDER")
        for s in sources:
            x = v.get(s)
            if isinstance(x, int) and isinstance(lim, int) and x > lim:
                out.add(arch_dir(combo.split("-")[0]))
    return out


def iface_of(engine, sig):
    parts = sig.split("|")
    if engine == "P1":
        return parts[0]
    if engine == "XV":
        return parts[1] if parts[0] == "dom" else parts[2]
    return None


def prop_archs(engine, cand, info):
    sig = cand["sig"]
    if engine in ("P1", "XV"):
        A = iface_of(engine, sig)
        t = XT.get(A) or XT.get(OLD.get(A, ""))
        return {arch_dir(a) for a in t["M"]} if t else set()
    if engine == "ORD":
        return ord_archs(sig.split("|"))
    if engine == "WT":
        return set(info["wt32"])
    if engine == "TLB":
        r, rest = sig.split("|", 1)
        if r in ("T1a", "T1c", "R1"):
            return {rest.split("|")[0]}
        return set(info["tlb"].get(r, []))
    return set()


def cache_files(rev):
    out = []
    for e in ("P1", "XV", "ORD", "WT"):
        out += sorted((CACHE / e).glob(f"{rev}*.json"))
    p = CACHE / "TLB" / f"{rev}.json"
    if p.exists():
        out.append(p)
    return out


def info(rev):
    """per-rev: feasibility of every candidate file x arch, WT 32-bit archs, TLB affected archs"""
    p = ACACHE / f"{rev}.json"
    if p.exists():
        return json.loads(p.read_text())
    t0 = time.time()
    try:
        if M.full(rev) != rev:
            raise ValueError(f"not a full commit id: {rev}")
        files = set()
        for cp in cache_files(rev):
            files |= {c["file"] for c in json.loads(cp.read_text()).get("cands", [])}
        F = feas_of(rev)
        feas = {f: [a for a in F.archs if F.feasible(f, a)] for f in sorted(files)}
        afiles = C.cat_files(rev, [f"arch/{a}/Kconfig" for a in F.archs])
        bits = W3.V2.Build64._arch_bits(afiles)
        wt32 = sorted(a for a, b in bits.items() if b in ("32", "both"))
        tf = T2.files_of(rev)
        T = T2.V1.Table({q: s for q, s in tf.items() if (q.startswith("arch/") and not q.endswith("Kconfig")) or q in T2.V1.GENERIC})
        tlb = {r: T2.V1.affected(T, r) for r in ("T2", "T3", "T4")}
        res = {"rev": rev, "ok": True, "archs": F.archs, "feas": feas, "wt32": wt32, "tlb": tlb, "secs": round(time.time() - t0, 1)}
    except Exception:
        res = {"rev": rev, "ok": False, "error": traceback.format_exc()[-2000:], "secs": round(time.time() - t0, 1)}
    ACACHE.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(res))
    return res


# ---------------------------------------------------------------- 三 new = multiset (old) + arch expansion
def S_of(engine, cand, inf):
    return prop_archs(engine, cand, inf) & set(inf["feas"].get(cand["file"], inf["archs"]))


def expansions(engine, pres, cres, pinf, cinf, ren):
    pk, ck = defaultdict(set), defaultdict(list)
    for r in pres["cands"]:
        pk[(ren.get(r["file"], r["file"]), r["func"], r["sig"])] |= S_of(engine, r, pinf)
    for r in cres["cands"]:
        ck[(r["file"], r["func"], r["sig"])].append(r)
    out = []
    for k, rows in ck.items():
        if k not in pk:
            continue
        sc = set().union(*(S_of(engine, r, cinf) for r in rows))
        grow = sc - pk[k]
        if grow:
            out.append(dict(rows[0], engine=engine, expand=sorted(grow)))
    return out


# ---------------------------------------------------------------- 四 Fixes map
def build_fixes():
    out = subprocess.run(["git", "-C", M.KSRC, "log", "-i", "--grep=^ *fixes:", "--format=%H%x01%B%x02", HEADREV],
                         capture_output=True, text=True, errors="replace").stdout
    m = defaultdict(list)
    for chunk in out.split("\x02"):
        if "\x01" not in chunk:
            continue
        h, body = chunk.split("\x01", 1)
        for tag in re.findall(r"^\s*fixes:\s*([0-9a-f]{8,40})\b", body, re.I | re.M):
            m[tag.lower()[:8]].append([tag.lower(), h.strip()])
    (HERE / "fixes_map.json").write_text(json.dumps(m))
    print("fixes map", len(m), "prefixes,", sum(len(v) for v in m.values()), "Fixes lines")


_FM = None


def fixes_for(commit):
    global _FM
    if _FM is None:
        _FM = json.loads((HERE / "fixes_map.json").read_text())
    c = commit.lower()
    return sorted({h for tag, h in _FM.get(c[:8], []) if c.startswith(tag)})


# ---------------------------------------------------------------- driver
def datasets():
    dev = json.loads((CT / "commitmode_20261117" / "dataset.json").read_text())
    ho = json.loads((CT / "heldout_commit_20261117" / "heldout_set.json").read_text())
    return {"dev": dev, "heldout": ho}


def extra_for(name, c):
    ex = M.extra_of(c)
    return [] if name == "heldout" and len(ex) > 30 else ex


def touches_build(c):
    return any(re.search(r"(^|/)(Kconfig[^/]*|Makefile|Kbuild)$", f) for f in M.git("diff", "--name-only", f"{c}^", c).split("\n") if f)


def runall(n=5):
    revs, tlb_need = [], []
    for name, ds in datasets().items():
        for it in ds["positives"] + ds["negatives"]:
            c = M.full(it["commit"])
            for rev in (M.full(c + "^"), c):
                if rev not in revs:
                    revs.append(rev)
                if (TL.touches(c) or touches_build(c)) and not (CACHE / "TLB" / f"{rev}.json").exists() and rev not in tlb_need:
                    tlb_need.append(rev)
    log = open(HERE / "runall.log", "a")
    for label, todo, cmd in (("TLB", tlb_need, [str(CT / "commitmode_tlb_20261117" / "cmtlb.py"), "engine"]),
                             ("ARCH", [r for r in revs if not (ACACHE / f"{r}.json").exists()], [str(HERE / "archsig.py"), "info"])):
        print(f"start {len(todo)} {label} jobs", file=log, flush=True)
        running, t0 = [], time.time()
        while todo or running:
            running = [pr for pr in running if pr.poll() is None]
            while todo and len(running) < n:
                running.append(subprocess.Popen([sys.executable, *cmd, todo.pop(0)], stdout=log, stderr=subprocess.STDOUT))
            print(f"{label} {round(time.time() - t0)}s todo={len(todo)} running={len(running)}", file=log, flush=True)
            time.sleep(15)
        print(f"{label} done", round(time.time() - t0), file=log, flush=True)


def load(path):
    return json.loads(path.read_text()) if path.exists() else None


def commit_eval(name, it):
    c = M.full(it["commit"])
    p = M.full(c + "^")
    ex = tuple(extra_for(name, c))
    ren = M.renames(c)
    pinf, cinf = load(ACACHE / f"{p}.json"), load(ACACHE / f"{c}.json")
    out = {"commit": c[:12], "info": M.git("log", "-1", "--format=%h|%cs|%s", c).strip(), "engines": {}, "old_new": [], "expand": []}
    for e in ENGS:
        if e == "TLB":
            pr, cr = load(CACHE / "TLB" / f"{p}.json"), load(CACHE / "TLB" / f"{c}.json")
            if pr is None and cr is None and not (TL.touches(c) or touches_build(c)):
                out["engines"][e] = "skip"
                continue
        else:
            x = ex if e in M.HEAVY else ()
            pr, cr = load(E.cache_path(e, p, x)), load(E.cache_path(e, c, x))
        if pr is None or cr is None or not pr["ok"] or not cr["ok"]:
            out["engines"][e] = "error"
            continue
        out["engines"][e] = "ok"
        out["old_new"] += [dict(r, engine=e) for r in M.compare(pr, cr, ren)]
        if pinf and cinf and pinf["ok"] and cinf["ok"]:
            out["expand"] += expansions(e, pr, cr, pinf, cinf, ren)
        else:
            out["engines"][e] = "ok-noarch"
    return out


def is_A(r):
    return r["engine"] == "WT" and r["sig"].startswith("A|")


def score():
    rows_all = {}
    for name, ds in datasets().items():
        rows = []
        for kind, items in (("pos", ds["positives"]), ("neg", ds["negatives"])):
            for it in items:
                r = commit_eval(name, it)
                r["kind"] = kind
                r["tainted"] = r["commit"] in TL.TAINTED and name == "heldout"
                old_names = {fn for _, fn in it.get("fix_funcs", [])}
                fx = fixes_for(M.full(it["commit"]))
                r["fixes_pointing"] = [f[:12] for f in fx]
                new_names = set(old_names)
                if kind == "pos":
                    for f in fx[:12]:
                        new_names |= {fn for _, fn in DSET.touched_funcs(f)}
                A, B = r["old_new"], r["old_new"] + r["expand"]
                r["flagA"], r["flagB"] = bool(A), bool(B)
                r["flagA_noA"], r["flagB_noA"] = any(not is_A(x) for x in A), any(not is_A(x) for x in B)

                def al(cands, names):
                    return any(x["func"] in names or (is_A(x) and x["sig"].split("|")[1][4:].split("#")[0] in names
                                                      and x["sig"].split("|")[1].startswith("arg:")) for x in cands)
                if kind == "pos":
                    r["alA"], r["alB"], r["alC"] = al(A, old_names), al(B, old_names), al(B, new_names)
                    r["n_fix_funcs_old"], r["n_fix_funcs_new"] = len(old_names), len(new_names)
                r["expand_show"] = [f"{x['engine']} +{','.join(x['expand'])} {x['file']}:{x['line']} {x['func']} {x['sig'][:70]}" for x in r["expand"]]
                rows.append(r)
                (HERE / "report").mkdir(exist_ok=True)
                (HERE / "report" / f"{name}_{r['commit']}.json").write_text(json.dumps(r, indent=1, ensure_ascii=False))
        rows_all[name] = rows

    def summ(P, N):
        s = {"n_pos": len(P), "n_neg": len(N)}
        for g in "AB":
            s[f"recall{g}"] = sum(r[f"flag{g}"] for r in P)
            s[f"recall{g}_noA"] = sum(r[f"flag{g}_noA"] for r in P)
            s[f"fp{g}"] = sum(r[f"flag{g}"] for r in N)
            s[f"fp{g}_noA"] = sum(r[f"flag{g}_noA"] for r in N)
        s["recallC"], s["fpC"] = s["recallB"], s["fpB"]
        for g in "ABC":
            s[f"aligned{g}"] = sum(r[f"al{g}"] for r in P)
        s["errors"] = sum(1 for r in P + N for v in r["engines"].values() if v in ("error", "ok-noarch"))
        return s
    res = {}
    for name, rows in rows_all.items():
        P = [r for r in rows if r["kind"] == "pos"]
        N = [r for r in rows if r["kind"] == "neg"]
        res[name] = {"all": summ(P, N)}
        if name == "heldout":
            res[name]["clean"] = summ([r for r in P if not r["tainted"]], N)
            res[name]["tainted"] = summ([r for r in P if r["tainted"]], [])
        res[name]["neg_with_fixes"] = [(r["commit"], r["fixes_pointing"]) for r in N if r["fixes_pointing"]]
        res[name]["rows"] = rows
    (HERE / "results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    lines = []
    for name, r in res.items():
        for part in [k for k in ("all", "clean", "tainted") if k in r]:
            s = r[part]
            lines.append(f"{name}/{part}: pos {s['n_pos']} recall A {s['recallA']} B {s['recallB']} (noA {s['recallA_noA']}/{s['recallB_noA']}) | "
                         f"aligned A {s['alignedA']} B {s['alignedB']} C {s['alignedC']} | neg {s['n_neg']} fp A {s['fpA']} B {s['fpB']} "
                         f"(noA {s['fpA_noA']}/{s['fpB_noA']}) | errors {s['errors']}")
        lines.append(f"  {name} negatives pointed to by Fixes: {r['neg_with_fixes']}")
        for row in r["rows"]:
            tag = []
            if row["flagB"] and not row["flagA"]:
                tag.append("NEWFLAG")
            if row["kind"] == "pos" and row["alC"] and not row["alA"]:
                tag.append("NEWALIGN(" + ("B" if row["alB"] else "C") + ")")
            if tag or row["expand"]:
                lines.append(f"  {name} {row['kind']} {'T' if row['tainted'] else ' '} {' '.join(tag) or '-'} {row['info'][:60]} fixes={row['fixes_pointing'][:4]}")
                lines += ["      " + x for x in row["expand_show"][:8]]
    (HERE / "score.log").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


# ---------------------------------------------------------------- selftest
def selftest():
    kf = {"arch/aa/Kconfig": "config AA\n\tdef_bool y\n\tselect HAVE_X\n\tselect SPARSE_OK\n",
          "arch/bb/Kconfig": "config BB\n\tdef_bool y\n\nconfig 64BIT\n\tbool \"64-bit\"\n",
          "mm/Kconfig": "config HAVE_X\n\tbool\n\nconfig SPARSE_OK\n\tbool\n\n"
                        "config FEAT\n\tbool \"feat\"\n\tdepends on HAVE_X\n\n"
                        "config ONLYX86\n\tbool \"x\"\n\tdepends on X86\n\n"
                        "config HID\n\tbool\n\tselect FOO\n\nconfig PLAIN\n\tbool \"plain\"\n\n"
                        "config SPARSEMEM_VMEMMAP\n\tbool \"v\"\n\tdepends on SPARSE_OK\n\n"
                        "config CC_OK\n\tdef_bool $(cc-option, -fsanitize=kernel-address)\n\n"
                        "config USES_CC\n\tbool \"u\"\n\tdepends on CC_OK\n\n"
                        "config EXPR_DEF\n\tdef_bool HAVE_X && PLAIN\n\n"
                        "config NDEF\n\tdef_bool n\n"}
    mf = {"mm/Makefile": "obj-y += a.o\nobj-$(CONFIG_FEAT) += feat.o\nobj-$(CONFIG_ONLYX86) += x86only.o\nobj-$(CONFIG_PLAIN) += plain.o\n"
                         "obj-$(CONFIG_SPARSEMEM_VMEMMAP) += sparse-vmemmap.o\nobj-$(CONFIG_FEAT) += sub/\n"
                         "obj-$(CONFIG_USES_CC) += cc.o\nobj-$(CONFIG_EXPR_DEF) += ex.o\nobj-$(CONFIG_NDEF) += nd.o\n"}
    F = Feas(kf, mf)
    ck = [("feat on aa", F.feasible("mm/feat.c", "aa")), ("feat not on bb", not F.feasible("mm/feat.c", "bb")),
          ("x86only nowhere", not F.feasible("mm/x86only.c", "aa") and not F.feasible("mm/x86only.c", "bb")),
          ("plain everywhere", F.feasible("mm/plain.c", "aa") and F.feasible("mm/plain.c", "bb")),
          ("obj-y everywhere", F.feasible("mm/a.c", "bb")), ("header everywhere", F.feasible("include/linux/x.h", "bb")),
          ("dir cond", not F.feasible("mm/sub/z.c", "bb") and F.feasible("mm/sub/z.c", "aa")),
          ("arch file only own arch", F.feasible("arch/aa/mm/i.c", "aa") and not F.feasible("arch/aa/mm/i.c", "bb")),
          ("vmemmap via select", F.feasible("mm/sparse-vmemmap.c", "aa") and not F.feasible("mm/sparse-vmemmap.c", "bb")),
          ("amd1: $(cc-option) default on", F.feasible("mm/cc.c", "bb")),
          ("amd1: def_bool expr", F.feasible("mm/ex.c", "aa") and not F.feasible("mm/ex.c", "bb")),
          ("amd1: def_bool n", not F.feasible("mm/nd.c", "aa"))]
    # expansion: same sig, child gains arch
    pinf = {"archs": ["aa", "bb", "riscv"], "feas": {"mm/sparse-vmemmap.c": ["aa"]}, "wt32": [], "tlb": {"T2": ["riscv", "aa"]}}
    cinf = {"archs": ["aa", "bb", "riscv"], "feas": {"mm/sparse-vmemmap.c": ["aa", "riscv"]}, "wt32": [], "tlb": {"T2": ["riscv", "aa"]}}
    cand = {"file": "mm/sparse-vmemmap.c", "func": "vmemmap_pte_populate", "line": 1, "sig": "T2|set_pte_at(&init_mm)"}
    ex = expansions("TLB", {"cands": [cand]}, {"cands": [dict(cand, line=5)]}, pinf, cinf, {})
    ex2 = expansions("TLB", {"cands": [cand]}, {"cands": [cand]}, cinf, cinf, {})
    ck += [("expansion riscv", len(ex) == 1 and ex[0]["expand"] == ["riscv"]), ("no expansion when same", ex2 == [])]
    # property archs
    ck += [("P1 table archs", "x86" in prop_archs("P1", {"sig": "pte_clear_soft_dirty|x"}, pinf)),
           ("P1 unknown iface -> empty", prop_archs("P1", {"sig": "nosuch|x"}, pinf) == set()),
           ("ORD HPAGE_PMD_ORDER -> arm64", "arm64" in ord_archs(["HPAGE_PMD_ORDER"])),
           ("ORD not x86", "x86" not in ord_archs(["HPAGE_PMD_ORDER"])),
           ("TLB R1 arch", prop_archs("TLB", {"sig": "R1|riscv|kasan|x"}, pinf) == {"riscv"})]
    global _FM
    _FM = {"abcdef12": [["abcdef123456", "f1"], ["abcdef12ffff", "f2"]]}
    ck += [("fixes prefix", fixes_for("abcdef1234567890") == ["f1"])]
    _FM = None
    bad = 0
    for nm, ok in ck:
        bad += not ok
        print("ok " if ok else "BAD", nm)
    print("selftest(archsig)", "PASS" if not bad else f"FAIL {bad}")
    return not bad


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    cmd = sys.argv[1]
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    if cmd == "info":
        r = info(sys.argv[2])
        print("ARCH", sys.argv[2][:12], "ok" if r["ok"] else "ERROR", len(r.get("feas", {})), "files", r["secs"], "s", (r.get("error") or "")[-300:], flush=True)
    elif cmd == "fixes":
        build_fixes()
    elif cmd == "runall":
        runall(int(sys.argv[2]) if len(sys.argv) > 2 else 5)
    elif cmd == "score":
        score()
