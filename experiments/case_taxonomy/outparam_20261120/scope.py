"""outparam criteria 二 (day 1): preprocess mm/ and kernel/ translation units per build, bind every direct call, classify units.
WSL. Large outputs go to /root/work/outparam/.

    python3 scope.py run      -> /root/work/outparam/{pass1_<build>.pkl.gz, extidx.pkl.gz, scope.csv.gz}, scope_summary.json
"""
import csv
import gzip
import hashlib
import io
import json
import os
import pickle
import re
import shlex
import subprocess
import sys
import time
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "p1check_20261115"))
import p1check as C  # noqa: E402

SRC = "/root/repos/linux/"
REV = "df2908090cda"
BUILDS = {a: f"/root/work/boundary_build/{a}_defconfig" for a in ("riscv", "arm64", "x86_64")}
WORK = Path("/root/work/outparam")
MARK = re.compile(r'^# (\d+) "([^"]*)"')
IDENT = re.compile(r"^[A-Za-z_]\w*$")
NOT_CALLS = {"__attribute__", "__attribute", "asm", "__asm__", "__asm", "__typeof__", "__typeof", "typeof", "_Static_assert",
             "static_assert", "__alignof__", "_Alignof", "alignof", "__volatile__", "volatile", "__extension__", "_Generic",
             "__label__", "__auto_type", "offsetof", "__builtin_offsetof"}


def load_db(b):
    cc = json.load(open(BUILDS[b] + "/compile_commands.json"))
    return {e["file"][len(SRC):]: e for e in cc if e["file"].startswith(SRC) and e["file"].endswith(".c")}


def pp_command(e):
    args = shlex.split(e["command"]) if "command" in e else list(e["arguments"])
    out, skip = [], False
    for a in args:
        if skip:
            skip = False
            continue
        if a in ("-c",):
            continue
        if a in ("-o", "-MF", "-MT", "-MQ"):
            skip = True
            continue
        if a.startswith("-Wp,-MMD") or a.startswith("-Wp,-MD") or a in ("-MD", "-MMD"):
            continue
        out.append(a)
    return out + ["-E", "-o", "-"]


def preprocess(e):
    r = subprocess.run(pp_command(e), cwd=e["directory"], capture_output=True, text=True, errors="replace")
    return r.stdout if r.returncode == 0 else None


def origin_map(text):
    """returns (clean text with marker lines blanked, list origin[(file, line)] per output line (1-based index))"""
    lines = text.split("\n")
    org = [None] * (len(lines) + 1)
    cur_f, cur_l = "?", 0
    for i, ln in enumerate(lines, 1):
        m = MARK.match(ln)
        if m:
            cur_l, cur_f = int(m.group(1)) - 1, m.group(2)
            if cur_f.startswith(SRC):
                cur_f = cur_f[len(SRC):]
            lines[i - 1] = ""
            org[i] = (cur_f, cur_l)
            continue
        if ln.startswith("#"):
            lines[i - 1] = ""
        cur_l += 1
        org[i] = (cur_f, cur_l)
    return "\n".join(lines), org


def head_info(t, lo, name):
    j = lo - 1
    d = 0
    while j >= 0:
        x = t[j][0]
        if x == ")":
            d += 1
        elif x == "(":
            d -= 1
        elif x in (";", "}") and d == 0:
            break
        j -= 1
    head = [x[0] for x in t[j + 1:lo]]
    pre = head[:head.index(name)] if name in head else head
    rk = "ptr" if "*" in pre else ("void" if "void" in pre else ("bool" if "bool" in pre else "other"))
    return {"static": "static" in pre, "weak": "__weak" in head or "weak" in " ".join(head), "rk": rk}


def analyse_tu(task):
    b, path, e = task
    t0 = time.time()
    text = preprocess(e)
    if text is None:
        return b, path, {"err": "preprocess failed"}
    clean, org = origin_map(text)
    s = C.strip(clean)
    t = C.tokenize(s)
    defs, calls = {}, []
    try:
        fns = list(C.functions(t))
    except Exception as ex:  # noqa: BLE001
        return b, path, {"err": "functions: " + repr(ex)[:100]}
    for name, params, lo, hi in fns:
        of, ol = org[t[lo][1]] if t[lo][1] < len(org) and org[t[lo][1]] else ("?", 0)
        hi_ = head_info(t, lo, name)
        body = " ".join(x[0] for x in t[lo:hi + 1])
        defs[name] = {"file": of, "line": ol, "hash": hashlib.sha1(body.encode()).hexdigest()[:16], **hi_,
                      "nparams": len(params)}
        if of != path:
            continue
        for i in range(lo, hi):
            if t[i + 1][0] != "(" or not IDENT.match(t[i][0]) or t[i][0] in C.KEYW:
                continue
            nm = t[i][0]
            if nm.startswith("__builtin_") or nm in NOT_CALLS:  # devlog 1
                continue
            member = i > 0 and t[i - 1][0] in ("->", ".")
            if i > 0 and t[i - 1][0] == ")":  # (*fp)(...) style handled below
                pass
            cl = org[t[i][1]][1] if org[t[i][1]] else 0
            try:
                args = C.args_of(t, i + 1)[0]
                aforms = [" ".join(x[0] for x in t[a:bb])[:60] for a, bb in args][:8]
            except Exception:
                aforms = []
            calls.append({"caller": name, "line": cl, "callee": nm, "member": member, "args": aforms})
        # (*fp)(…) indirect
        for i in range(lo, hi - 3):
            if t[i][0] == "(" and t[i + 1][0] == "*" and IDENT.match(t[i + 2][0]) and t[i + 3][0] == ")" and i + 4 < hi and t[i + 4][0] == "(":
                calls.append({"caller": name, "line": org[t[i][1]][1] if org[t[i][1]] else 0, "callee": t[i + 2][0],
                              "member": True, "args": []})
    return b, path, {"defs": defs, "calls": calls, "secs": round(time.time() - t0, 2), "size": len(text)}


def ext_scan(path):
    try:
        src = open(SRC + path, encoding="utf-8", errors="replace").read()
        t = C.tokenize(C.strip(src))
        out = []
        for name, params, lo, hi in C.functions(t):
            h = head_info(t, lo, name)
            if not h["static"]:
                body = " ".join(x[0] for x in t[lo:hi + 1])
                out.append((name, t[lo][1], h["weak"], hashlib.sha1(body.encode()).hexdigest()[:16]))
        return path, out
    except Exception as ex:  # noqa: BLE001
        return path, None


def main():
    t0 = time.time()
    WORK.mkdir(parents=True, exist_ok=True)
    st = subprocess.run(["git", "-C", SRC, "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
    head = subprocess.run(["git", "-C", SRC, "rev-parse", "--short=12", "HEAD"], capture_output=True, text=True).stdout.strip()
    if st or head != REV:
        raise SystemExit(f"worktree not clean or not at {REV}")
    dbs = {b: load_db(b) for b in BUILDS}
    callers = sorted({p for b in dbs for p in dbs[b] if p.startswith(("mm/", "kernel/"))})
    callers = [p for p in callers if sum(p in dbs[b] for b in dbs) >= 2]
    print("caller TUs (in >=2 builds):", len(callers), flush=True)
    # external index (lexical, raw files), union of compiled .c files
    allc = sorted({p for b in dbs for p in dbs[b]})
    ext = {}
    with Pool(16) as pool:
        for k, (p, out) in enumerate(pool.imap_unordered(ext_scan, allc, chunksize=32)):
            ext[p] = out
    print("ext index files:", len(ext), "failed:", sum(v is None for v in ext.values()), round(time.time() - t0), "s", flush=True)
    extidx = {}
    for b in dbs:
        idx = defaultdict(list)
        for p in dbs[b]:
            for name, line, weak, h in (ext.get(p) or []):
                idx[name].append((p, line, weak, h))
        extidx[b] = idx
    pickle.dump(extidx, gzip.open(WORK / "extidx.pkl.gz", "wb"))
    # pass 1: preprocess callers
    tasks = [(b, p, dbs[b][p]) for p in callers for b in dbs if p in dbs[b]]
    res = {b: {} for b in dbs}
    with Pool(16) as pool:
        for k, (b, p, r) in enumerate(pool.imap_unordered(analyse_tu, tasks, chunksize=2)):
            res[b][p] = r
            if k % 100 == 0:
                print(f"  pass1 {k}/{len(tasks)} {round(time.time() - t0)}s", flush=True)
    for b in dbs:
        pickle.dump(res[b], gzip.open(WORK / f"pass1_{b}.pkl.gz", "wb"))
    errs = Counter(r.get("err", "ok")[:20] for b in res for r in res[b].values())
    print("pass1 status:", dict(errs), round(time.time() - t0), "s", flush=True)

    def bind(b, p, callee):
        r = res[b].get(p)
        if r is None:
            return ("caller-absent",)
        if "err" in r:
            return ("unknown", r["err"])
        d = r["defs"].get(callee)
        if d:
            return ("bound", d["file"], d["line"], d["hash"], "tu")
        lst = extidx[b].get(callee, [])
        strong = [x for x in lst if not x[2]]
        cand = strong or lst
        if len(cand) == 1:
            p2, line, weak, h = cand[0]
            return ("bound", p2, line, "raw:" + h, "ext")
        if not cand:
            return ("absent",)
        return ("unknown", f"{len(cand)} definitions")
    # units
    units = {}
    for p in callers:
        for b in dbs:
            r = res[b].get(p)
            if not r or "err" in r:
                continue
            for c in r["calls"]:
                k = (p, c["caller"], c["line"], c["callee"])
                u = units.setdefault(k, {"member": c["member"], "args": c["args"], "builds": {}})
                u["builds"][b] = None
    status = Counter()
    rows = []
    for k, u in units.items():
        p, fn, line, callee = k
        if u["member"]:
            stt = "间接调用"
            binds = {}
        else:
            binds = {b: bind(b, p, callee) for b in u["builds"]}  # amendment 1: only builds where the call site exists
            bound = {b: v for b, v in binds.items() if v[0] == "bound"}
            if len(bound) >= 2:
                keys = {(v[1], v[2], v[3]) for v in bound.values()}
                stt = "双侧可绑定且不同" if len(keys) > 1 else "双侧同实现"
            elif any(v[0] == "unknown" for v in binds.values()):
                stt = "解析未知"
            else:
                stt = "一侧缺席"
        status[stt] += 1
        rows.append([p, fn, line, callee, stt, json.dumps(binds, ensure_ascii=False), json.dumps(u["args"], ensure_ascii=False)])
    with gzip.open(WORK / "scope.csv.gz", "wt", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["caller_file", "caller_func", "line", "callee", "status", "bindings", "args"])
        w.writerows(rows)
    ifaces = Counter(r[3] for r in rows if r[4] == "双侧可绑定且不同")
    summ = {"caller_tus": len(callers), "pp_tasks": len(tasks), "pass1_status": dict(errs), "units": len(rows),
            "status": dict(status), "interfaces_diff": len(ifaces), "top_diff_interfaces": ifaces.most_common(25),
            "secs": round(time.time() - t0),
            "pp_size_mb_median": sorted(r.get("size", 0) for b in res for r in res[b].values())[len(tasks) // 2] / 1e6}
    (HERE / "scope_summary.json").write_text(json.dumps(summ, indent=1, ensure_ascii=False))
    print(json.dumps(summ, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    if sys.argv[1] == "run":
        main()
    elif sys.argv[1] == "one":  # quick probe on one TU: python3 scope.py one <build> <path>
        dbs = {sys.argv[2]: load_db(sys.argv[2])}
        b, p, r = analyse_tu((sys.argv[2], sys.argv[3], dbs[sys.argv[2]][sys.argv[3]]))
        print(r.get("err"), len(r.get("defs", {})), len(r.get("calls", [])), r.get("secs"), r.get("size"))
