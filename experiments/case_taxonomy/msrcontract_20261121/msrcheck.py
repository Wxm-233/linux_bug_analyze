"""msrcontract criteria 二/三: MSR -> X86_FEATURE contract table mined from KVM; host MSR accesses not guarded by a required feature. WSL.

    python3 msrcheck.py table <rev>             -> prints size; writes /root/work/msrcontract/table_<rev12>.json
    python3 msrcheck.py sample <rev>            -> table_sample.json (criteria 四.1, seed 20261121, 15 entries + msr-index.h line)
    python3 msrcheck.py run <rev> [out.json]    -> candidates
"""
import json
import random
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "capcheck_20261121"))
import capcheck as K  # noqa: E402  (frozen 39e02684…; imported read-only)
C = K.C

WORK = Path("/root/work/msrcontract")
FEATCALL = {"guest_cpu_cap_has", "guest_cpuid_has", "kvm_cpu_cap_has", "boot_cpu_has", "static_cpu_has", "cpu_feature_enabled"}
MSROPS = {"rdmsr", "rdmsrl", "rdmsrq", "wrmsr", "wrmsrl", "wrmsrq", "wrmsrns", "native_read_msr", "native_write_msr", "rdmsr_on_cpu",
          "wrmsr_on_cpu", "rdmsrl_on_cpu", "wrmsrl_on_cpu", "rdmsrq_on_cpu", "wrmsrq_on_cpu", "msr_set_bit", "msr_clear_bit"}
FEAT = re.compile(r"^X86_FEATURE_\w+$")


def feats_in(t, lo, hi):
    out, calls = set(), set()
    for i in range(lo, hi - 1):
        x = t[i][0]
        if t[i + 1][0] != "(" or not K.IDENT.match(x) or (i > 0 and t[i - 1][0] in ("->", ".")):
            continue
        if x in FEATCALL:
            args = C.split_top(t, i + 2, C.match_fwd(t, i + 1), ",")
            a, b = C.strip_parens(t, *args[-1])
            if b - a == 1 and FEAT.match(t[a][0]):
                out.add(t[a][0])
        else:
            calls.add(x)
    return out, calls


def table(rev):
    rev = K.full(rev)
    paths = [p for p in K.git("ls-tree", "-r", "--name-only", rev, "--", "arch/x86/kvm").split("\n") if p.endswith((".c", ".h"))]
    srcs = C.cat_files(rev, paths)
    toks = {p: C.tokenize(C.strip(s)) for p, s in srcs.items()}
    helper = {}
    for p, t in toks.items():
        for name, params, lo, hi in C.functions(t):
            f, _ = feats_in(t, lo, hi)
            if f:
                helper[name] = helper.get(name, set()) | f
    tab = defaultdict(set)
    where = defaultdict(set)
    for p, t in toks.items():
        depth = [0] * (len(t) + 1)
        d = 0
        for i, (x, _) in enumerate(t):
            depth[i] = d
            if x == "{":
                d += 1
            elif x == "}":
                d -= 1
        i = 0
        while i < len(t):
            if t[i][0] != "case":
                i += 1
                continue
            d0 = depth[i]
            labels, j = [], i
            while j < len(t) and t[j][0] == "case" and depth[j] == d0:
                k = j + 1
                while k < len(t) and t[k][0] != ":":
                    k += 1
                if t[j + 1][0].startswith("MSR_"):
                    labels.append(t[j + 1][0])
                j = k + 1
            e = j
            while e < len(t):
                x = t[e][0]
                if depth[e] < d0 or (depth[e] == d0 and x in ("case", "default")) or (x == "}" and depth[e] == d0):
                    break
                e += 1
            if labels:
                f, calls = feats_in(t, j, e)
                for c in calls:
                    f |= helper.get(c, set())
                for m in labels:
                    if f:
                        tab[m] |= f
                        where[m].add(p)
            i = j
    out = {m: sorted(f) for m, f in sorted(tab.items())}
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / f"table_{rev[:12]}.json").write_text(json.dumps({"rev": rev, "table": out, "where": {m: sorted(v) for m, v in where.items()}}, indent=1))
    return out


def sample(rev):
    rev = K.full(rev)
    tab = table(rev)
    idx = K.git("show", f"{rev}:arch/x86/include/asm/msr-index.h").split("\n")
    pick = random.Random(20261121).sample(sorted(tab), min(15, len(tab)))
    rows = []
    for m in pick:
        line = next((ln.strip() for ln in idx if re.search(r"#define\s+" + re.escape(m) + r"\b", ln)), None)
        rows.append({"msr": m, "features": tab[m], "msr_index_line": line})
    (HERE / "table_sample.json").write_text(json.dumps(rows, indent=1))
    for r in rows:
        print(r["msr"], r["features"], "|", r["msr_index_line"])


def effective_sites(files):
    """copy of capcheck.infer's effective-guard computation (criteria 三: same definition), restricted to MSR operations"""
    out = []
    for f in files:
        if f["path"].startswith("arch/x86/kvm/"):
            continue
        reg = {name for kind, name in f["regs"]}
        byname = {fn["name"]: fn for fn in f["funcs"]}
        modguard = set()
        for fn in f["funcs"]:
            if fn["name"] in reg:
                modguard |= set(fn["entry"])
        callers = defaultdict(list)
        for fn in f["funcs"]:
            for line, nm, keys, g in fn["sites"]:
                if nm in byname:
                    callers[nm].append(set(g) | modguard)
        for fn in f["funcs"]:
            cg = set()
            if fn["static"] and callers.get(fn["name"]):
                cg = set.intersection(*callers[fn["name"]])
            for line, nm, keys, g in fn["sites"]:
                if nm in MSROPS and len(keys) > 1 and keys[1].split("|", 1)[1].startswith("MSR_"):
                    out.append((f["path"], fn["name"], line, nm, keys[1].split("|", 1)[1], set(g) | modguard | cg))
    return out


def run(rev, outp=None):
    t0 = time.time()
    rev = K.full(rev)
    tab = table(rev)
    files = K.facts(rev)
    sites = effective_sites(files)
    guarded = Counter()
    for p, fn, line, op, msr, gs in sites:
        if msr in tab and gs & set(tab[msr]):
            guarded[msr] += 1
    cands = []
    for p, fn, line, op, msr, gs in sites:
        if msr in tab and not (gs & set(tab[msr])):
            cands.append({"file": p, "line": line, "func": fn, "op": op, "msr": msr, "needs": tab[msr], "guarded_elsewhere": guarded[msr],
                          "other_caps_here": sorted(gs)})
    cands.sort(key=lambda c: (-c["guarded_elsewhere"], c["file"], c["line"]))
    stats = {"table": len(tab), "msr_sites": len(sites), "sites_on_table_msrs": sum(1 for s in sites if s[4] in tab),
             "guarded": sum(guarded.values()), "cands": len(cands), "cand_msrs": len({c["msr"] for c in cands}), "secs": round(time.time() - t0)}
    res = {"rev": rev, "stats": stats, "cands": cands}
    if outp:
        Path(outp).write_text(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    cmd = sys.argv[1]
    if cmd == "table":
        t = table(sys.argv[2])
        print("table entries", len(t))
    elif cmd == "sample":
        sample(sys.argv[2])
    elif cmd == "run":
        r = run(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
        print(json.dumps(r["stats"]))
