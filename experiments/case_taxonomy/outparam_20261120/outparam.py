"""outparam criteria 三/四/五 (day 2): output-parameter comparison on units whose bindings differ across builds. WSL.

    python3 outparam.py selftest          -> micro controls (criteria 五)
    python3 outparam.py run               -> /root/work/outparam/pairs.csv, reports.jsonl; ranked_coarse.json, ranked_evidence.json,
                                             pairs_summary.json
"""
import csv
import gzip
import hashlib
import json
import pickle
import re
import sys
import time
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "p1check_20261115"))
sys.path.insert(0, str(HERE))
import p1check as C  # noqa: E402
import scope as S  # noqa: E402

WORK = S.WORK
IDENT = re.compile(r"^[A-Za-z_]\w*$")
WRITE_ALL = {"memset", "memcpy", "memmove", "memzero_explicit", "copy_from_user", "__copy_from_user", "strscpy", "strcpy",
             "strncpy", "strlcpy", "memcpy_fromio", "copy_from_kernel_nofault"}
ARGFORM = re.compile(r"^& ([A-Za-z_]\w*)((?: (?:\.|->) [A-Za-z_]\w*)*)$")
SEED = "20261120"
CAP = 512


class Overflow(Exception):
    pass


def path_from(t, i, hi):
    """access path starting at ident t[i]: ('v', ['f','g'], next)"""
    base = t[i][0]
    fs, j = [], i + 1
    while j + 1 < hi and t[j][0] in ("->", ".") and IDENT.match(t[j + 1][0]):
        fs.append(t[j + 1][0])
        j += 2
    return base, fs, j


# ------------------------------------------------------------------ callee side
class Callee:
    """walk success paths of a definition; record writes to the object behind parameter p"""

    def __init__(self, t, lo, hi, pname, rk, helpers=None):
        self.t, self.lo, self.hi, self.p, self.rk = t, lo, hi, pname, rk
        self.helpers = helpers or {}   # name -> function(argidx) -> {'all': set(fields always written) } or None

    def apply(self, st, lo, hi):
        written, unres = st
        written = set(written)
        t, p = self.t, self.p
        for i in range(lo, hi):
            x = t[i][0]
            if x != p:
                continue
            prev = t[i - 1][0] if i > lo else ""
            # *p = …
            if prev == "*" and i + 1 < hi and t[i + 1][0] == "=" and (i - 2 < lo or t[i - 2][0] in ("(", ";", "{", "}", ",") or i - 1 == lo):
                written.add("*")
                continue
            base, fs, j = path_from(t, i, hi)
            if j < hi and t[j][0] == "[":
                k = C.match_fwd(t, j, "[", "]")
                if k + 1 < hi and t[k + 1][0] == "=":
                    written.add("*")
                continue
            if fs and j < hi and t[j][0] == "=" and prev not in (".", "->"):
                if i + 1 < hi and t[i + 1][0] == "->":
                    written.add(fs[0])
                continue
            # p passed somewhere / aliased
            if prev in (".", "->"):
                continue
            if j < hi and t[j][0] in ("=",) and not fs:
                continue  # p = … (reassigning the pointer): treat below as alias
            # find enclosing call: walk back to '(' preceded by ident
            k, d = i - 1, 0
            while k >= lo:
                y = t[k][0]
                if y in (")", "]"):
                    d += 1
                elif y in ("(", "["):
                    if d == 0:
                        break
                    d -= 1
                elif y in (";", "{", "}") and d == 0:
                    k = lo - 1
                    break
                k -= 1
            if k >= lo and t[k][0] == "(" and k - 1 >= lo and IDENT.match(t[k - 1][0]) and t[k - 1][0] not in C.KEYW:
                fn = t[k - 1][0]
                args = C.args_of(t, k)[0]
                idx = next((n for n, (a, b) in enumerate(args) if a <= i < b), None)
                arg_toks = [z[0] for z in t[args[idx][0]:args[idx][1]]] if idx is not None else []
                # &p->f or p
                field = "*"
                if arg_toks[:2] == ["&", p] and len(arg_toks) >= 4 and arg_toks[2] == "->":
                    field = arg_toks[3]
                elif arg_toks[:1] == [p] and len(arg_toks) == 1:
                    field = "*"
                elif arg_toks[:1] == [p] and len(arg_toks) >= 3 and arg_toks[1] == "->":
                    continue  # passing p->f by value: a read
                else:
                    unres = True
                    continue
                if fn in WRITE_ALL and idx == 0:
                    written.add(field)
                    continue
                h = self.helpers.get(fn)
                res = h(idx) if h else None
                if res is None:
                    if fn in ("pr_debug", "pr_info", "pr_warn", "pr_err", "printk", "WARN_ON", "BUG_ON", "kfree", "IS_ERR"):
                        continue
                    unres = True
                elif field == "*":
                    written |= res
                elif "*" in res:
                    written.add(field)
            else:
                unres = True  # alias / return p / other use
        return (frozenset(written), unres)

    def stmt(self, s, st, cd):
        if s is None:
            return [(st, "fall", None, cd)]
        k = s[0]
        if k == "block":
            states, out = [(st, cd)], []
            for x in s[1]:
                new, seen = [], set()
                for y, c in states:
                    for z, kind, info, c2 in self.stmt(x, y, c):
                        if kind == "fall":
                            if z not in seen:
                                seen.add(z)
                                new.append((z, c2))
                        else:
                            out.append((z, kind, info, c2))
                states = new
                if len(states) + len(out) > CAP:
                    raise Overflow
            return out + [(y, "fall", None, c) for y, c in states]
        if k == "expr":
            return [(self.apply(st, *s[1]), "fall", None, cd)]
        if k == "if":
            st = self.apply(st, *s[1])
            txt = " ".join(x[0] for x in self.t[s[1][0]:s[1][1]])[:70]
            return self.stmt(s[2], st, (cd + (txt,))[-3:]) + self.stmt(s[3], st, (cd + ("!(" + txt + ")",))[-3:])
        if k == "loop":
            for r in s[3]:
                st = self.apply(st, *r)
            if s[1]:
                st = self.apply(st, *s[1])
            out = [(st, "fall", None, cd)]   # zero iterations
            for z, kind, info, c2 in self.stmt(s[2], st, cd):
                out.append((z, "fall" if kind in ("break", "continue", "fall") else kind, info, c2))
            return out
        if k == "switch":
            st = self.apply(st, *s[1])
            out = [(st, "fall", None, cd)]
            for z, kind, info, c2 in self.stmt(s[2], st, cd):
                out.append((z, "fall" if kind in ("break", "fall") else kind, info, c2))
            return out
        if k == "jump":
            st = self.apply(st, *s[2])
            return [(st, s[1], s[2], cd)]
        return [(st, "fall", None, cd)]

    def ret_class(self, kind, info):
        t = self.t
        if kind == "goto":
            return "unk"
        if kind == "fall":
            return "ok" if self.rk == "void" else "unk"
        lo, hi = C.strip_parens(t, *info)
        w = [x[0] for x in t[lo:hi]]
        if self.rk == "void":
            return "ok"
        if self.rk == "bool":
            return "ok" if w in (["true"], ["1"]) else ("fail" if w in (["false"], ["0"]) else "unk")
        if self.rk == "ptr":
            if w in (["NULL"], ["0"]) or (w and w[0] in ("ERR_PTR", "ERR_CAST")):
                return "fail"
            return "ok" if w else "unk"
        if w == ["0"] or (len(w) == 1 and w[0].isdigit()):
            return "ok"
        if w and w[0] == "-":
            return "fail"
        return "unk"

    def run(self):
        tree = C.P(self.t, self.lo, self.hi + 1).block()
        outs = self.stmt(tree, (frozenset(), False), ())
        paths = []
        for (written, unres), kind, info, cd in outs:
            rc = self.ret_class(kind, info)
            line = self.t[info[0]][1] if info and info[0] < len(self.t) else self.t[self.hi][1]
            paths.append({"rc": rc, "written": written, "unres": unres, "conds": cd, "oline": line})
        return paths


def field_status(paths, field):
    ok = [p for p in paths if p["rc"] == "ok"]
    if not ok:
        return "未知", None
    hit = [("*" in p["written"]) or (field in p["written"]) for p in ok]
    if all(hit):
        return "必写", None
    miss = [p for p, h in zip(ok, hit) if not h and not p["unres"]]
    if miss:
        return "明确未写", miss[0]
    return "未知", None


# ------------------------------------------------------------------ caller side
def caller_facts(t, lo, hi, call_i, argpath, rk):
    """walk the caller; returns {'reads': {relfield: {'ok_read': bool, 'refill': bool}}, 'preinit': set, 'checked': bool}"""
    base, afs = argpath
    tree = C.P(t, lo, hi + 1).block()
    res = {"reads": defaultdict(lambda: {"ok_read": False, "clean_read": False}), "preinit": set(), "checked": False,
           "resvar": None}
    # state: (called, outcome('ok'|'fail'|'?'), preinit(frozenset), refill(frozenset))

    def rel(fs):
        if fs[:len(afs)] != afs:
            return None
        r = fs[len(afs):]
        return r[0] if r else "*"

    def apply(st, a, b):
        called, outc, pre, ref = st
        pre, ref = set(pre), set(ref)
        for i in range(a, b):
            if i == call_i:
                called = True
                # result variable: x = callee(...)
                if i - 2 >= a and t[i - 1][0] == "=" and IDENT.match(t[i - 2][0]):
                    res["resvar"] = t[i - 2][0]
                continue
            if t[i][0] != base or (i > a and t[i - 1][0] in (".", "->")):
                continue
            bb, fs, j = path_from(t, i, b)
            r = rel(fs)
            is_lhs = j < b and t[j][0] == "="
            addr = i > a and t[i - 1][0] == "&"
            if not called:
                if is_lhs:
                    pre.add(r if r is not None else "*")
                elif addr and not (i + 0 <= call_i <= i + 3):
                    k = i - 2
                    if k >= a and t[k][0] == "(" and k - 1 >= a and t[k - 1][0] in ("memset", "memzero_explicit"):
                        pre.add("*")
                continue
            if is_lhs:
                ref.add(r if r is not None else "*")
                continue
            if addr or r is None:
                continue
            if outc != "fail":
                e = res["reads"][r]
                e["ok_read"] = True
                if r not in pre and "*" not in pre and r not in ref and "*" not in ref:
                    e["clean_read"] = True
        return (called, outc, frozenset(pre), frozenset(ref))

    def cond_outcome(a, b):
        """which branch is failure for a condition on the call result: returns ('then'|'else', ) or None"""
        w = [x[0] for x in t[a:b]]
        rv = res["resvar"]
        has_call = a <= call_i < b
        if not has_call and (rv is None or rv not in w):
            return None
        res["checked"] = True
        s = " ".join(w)
        neg = w[:1] == ["!"] or "== 0" in s or ">= 0" in s
        if rk == "bool" and has_call:
            return "else" if not neg else "then"
        if "IS_ERR" in s or "< 0" in s or "!= 0" in s:
            return "then"
        if neg:
            return "else"
        return "then"

    def stmt(s, st):
        if s is None:
            return [st]
        k = s[0]
        if k == "block":
            states = [st]
            for x in s[1]:
                new = []
                for y in states:
                    new.extend(z for z in stmt(x, y) if z is not None)
                states = list(dict.fromkeys(new))
                if len(states) > CAP:
                    raise Overflow
            return states
        if k == "expr":
            return [apply(st, *s[1])]
        if k == "if":
            st = apply(st, *s[1])
            fo = cond_outcome(*s[1]) if st[0] else None
            a_st, b_st = st, st
            if fo == "then":
                a_st = (st[0], "fail", st[2], st[3])
                b_st = (st[0], "ok", st[2], st[3])
            elif fo == "else":
                a_st = (st[0], "ok", st[2], st[3])
                b_st = (st[0], "fail", st[2], st[3])
            return stmt(s[2], a_st) + stmt(s[3], b_st)
        if k == "loop":
            for r in s[3]:
                st = apply(st, *r)
            if s[1]:
                st = apply(st, *s[1])
            return [st] + stmt(s[2], st)
        if k == "switch":
            st = apply(st, *s[1])
            return [st] + stmt(s[2], st)
        if k == "jump":
            apply(st, *s[2])
            return []   # path ends
        return [st]
    stmt(tree, (False, "?", frozenset(), frozenset()))
    res["reads"] = dict(res["reads"])
    return res


# ------------------------------------------------------------------ micro controls (criteria 五)
MICRO = {
    "c1_success_miss": ("int impl_a(struct o *p) { p->len = 4; return 0; }",
                        "int impl_b(struct o *p, int x) { if (x) { p->len = 8; return 0; } return 0; }",
                        "int caller(void) { struct o v; int ret; ret = g(&v); if (ret) return ret; use(v.len); return 0; }",
                        (1, 1, 1)),
    "c2_fail_only": ("int impl_a(struct o *p) { p->len = 4; return 0; }",
                     "int impl_b(struct o *p, int x) { if (x) return -22; p->len = 8; return 0; }",
                     "int caller(void) { struct o v; int ret; ret = g(&v); if (ret) return ret; use(v.len); return 0; }",
                     (1, 0, 1)),
    "c3_preinit": ("int impl_a(struct o *p) { p->len = 4; return 0; }",
                   "int impl_b(struct o *p, int x) { if (x) { p->len = 8; return 0; } return 0; }",
                   "int caller(void) { struct o v; int ret; v.len = 0; ret = g(&v); if (ret) return ret; use(v.len); return 0; }",
                   (1, 1, 0)),
    "c4_unresolved": ("int impl_a(struct o *p) { p->len = 4; return 0; }",
                      "int impl_b(struct o *p, int x) { if (x) { p->len = 8; return 0; } fill_unknown(p); return 0; }",
                      "int caller(void) { struct o v; int ret; ret = g(&v); if (ret) return ret; use(v.len); return 0; }",
                      (1, 0, 1)),
}


def fn_tokens(src, name):
    t = C.tokenize(C.strip(src))
    for n, params, lo, hi in C.functions(t):
        if n == name:
            return t, lo, hi, [p[1] for p in params]
    raise KeyError(name)


def evidence(sa, sb, cf, field, comparable):
    e1 = 1 if comparable else 0
    e2 = 1 if ({sa, sb} == {"必写", "明确未写"}) else 0
    r = cf["reads"].get(field)
    e3 = 1 if (r and r["clean_read"]) else 0
    return (e1, e2, e3)


def selftest():
    ok = True
    for name, (a, b, c, want) in MICRO.items():
        ta = fn_tokens(a, "impl_a")
        tb = fn_tokens(b, "impl_b")
        pa = Callee(ta[0], ta[1], ta[2], "p", "other").run()
        pb = Callee(tb[0], tb[1], tb[2], "p", "other").run()
        sa, _ = field_status(pa, "len")
        sb, _ = field_status(pb, "len")
        tc, lo, hi, _ = fn_tokens(c, "caller")
        call_i = next(i for i in range(lo, hi) if tc[i][0] == "g" and tc[i + 1][0] == "(")
        cf = caller_facts(tc, lo, hi, call_i, ("v", []), "other")
        got = evidence(sa, sb, cf, "len", True)
        good = got == want
        ok &= good
        print(f"{name}: a={sa} b={sb} evidence={got} want={want} {'OK' if good else 'FAIL'}")
    print("SELFTEST", "OK" if ok else "FAIL")
    return ok


# ------------------------------------------------------------------ day-2 driver
_DBS = None
_PP = {}


def tu_tokens(b, path):
    """preprocessed tokens + origin map + function index of (build, file); cached per worker"""
    key = (b, path)
    if key in _PP:
        return _PP[key]
    e = _DBS[b].get(path)
    if e is None:
        _PP[key] = None
        return None
    text = S.preprocess(e)
    if text is None:
        _PP[key] = None
        return None
    clean, org = S.origin_map(text)
    t = C.tokenize(C.strip(clean))
    fns = {}
    for name, params, lo, hi in C.functions(t):
        fns[name] = (lo, hi, [p[1] for p in params])
    if len(_PP) > 24:
        _PP.pop(next(iter(_PP)))
    _PP[key] = (t, org, fns)
    return _PP[key]


def rk_of(t, lo, name):
    return S.head_info(t, lo, name)["rk"]


def is_local(t, lo, hi, v, params):
    if v in params:
        return False
    for j in range(lo + 1, hi - 1):
        if t[j][0] == v and t[j + 1][0] in (";", "=", "[", ",") and (IDENT.match(t[j - 1][0]) or t[j - 1][0] in ("*", "}")) \
                and t[j - 1][0] not in C.KEYW | {"return"}:
            return True
    return False


def analyse_group(task):
    """task: (caller_tu, [unit dict]) -> list of report dicts and per-unit status"""
    path, units = task
    out, stat = [], Counter()
    for u in units:
        try:
            r = analyse_unit(path, u)
        except (Overflow, RecursionError, IndexError, ValueError, KeyError) as ex:
            stat["error:" + type(ex).__name__] += 1
            continue
        stat[r[0]] += 1
        out.extend(r[1])
    return out, stat


def callee_paths(b, binding, name, k, cache):
    """paths of the definition bound in build b, for parameter index k"""
    kind = binding[4]
    src_file = None if kind == "tu" else binding[1]
    key = (b, binding[1], binding[2], name, k)
    if key in cache:
        return cache[key]
    tt = tu_tokens(b, cache["__caller__"] if kind == "tu" else src_file)
    if tt is None or name not in tt[2]:
        cache[key] = None
        return None
    t, org, fns = tt
    lo, hi, params = fns[name]
    if k >= len(params):
        cache[key] = None
        return None
    rk = rk_of(t, lo, name)

    def helper(hname):
        if hname not in fns:
            return None

        def f(idx):
            hlo, hhi, hp = fns[hname]
            if idx >= len(hp):
                return None
            try:
                ps = Callee(t, hlo, hhi, hp[idx], rk_of(t, hlo, hname)).run()
            except (Overflow, RecursionError, IndexError, ValueError):
                return None
            fin = [p for p in ps if p["rc"] != "fail"]
            if not fin or any(p["unres"] for p in fin):
                return None
            common = set.intersection(*[set(p["written"]) for p in fin])
            return common
        return f
    helpers = {h: helper(h) for h in set(x[0] for x in t[lo:hi]) if h in fns and h != name}
    helpers = {h: f for h, f in helpers.items() if f}
    paths = Callee(t, lo, hi, params[k], rk, helpers).run()
    for p in paths:  # devlog 2: report source lines, not preprocessed-output lines
        ol = p["oline"]
        p["oline"] = list(org[ol]) if isinstance(ol, int) and ol < len(org) and org[ol] else ["?", 0]
    loc = org[t[lo][1]] if t[lo][1] < len(org) and org[t[lo][1]] else ("?", 0)
    cache[key] = (paths, rk, loc, params[k])
    return cache[key]


_CACHE = {}


def analyse_unit(path, u):
    binds = {b: v for b, v in u["bindings"].items() if v[0] == "bound"}
    order = [b for b in ("riscv", "arm64", "x86_64") if b in binds]
    cb = order[0]
    tt = tu_tokens(cb, path)
    if tt is None or u["caller_func"] not in tt[2]:
        return ("caller-parse", [])
    t, org, fns = tt
    lo, hi, cparams = fns[u["caller_func"]]
    reports = []
    found_any = False
    for k, form in enumerate(u["args"]):
        m = ARGFORM.match(form)
        if not m:
            continue
        v = m.group(1)
        afs = [x for x in m.group(2).replace("->", ".").split(" ") if x and x != "."]
        if not is_local(t, lo, hi, v, cparams):
            continue
        # locate the call token: callee name at origin line with this arg form
        call_i = None
        for i in range(lo, hi):
            if t[i][0] == u["callee"] and i + 1 < hi and t[i + 1][0] == "(" and org[t[i][1]] and org[t[i][1]][1] == u["line"]:
                args = C.args_of(t, i + 1)[0]
                if k < len(args) and " ".join(x[0] for x in t[args[k][0]:args[k][1]])[:60] == form:
                    call_i = i
                    break
        if call_i is None:
            continue
        found_any = True
        _CACHE["__caller__"] = path
        cps = {}
        for b in order:
            cps[b] = callee_paths(b, binds[b], u["callee"], k, _CACHE)
        if sum(1 for x in cps.values() if x) < 2:
            continue
        rk0 = next(x[1] for x in cps.values() if x)
        cf = caller_facts(t, lo, hi, call_i, (v, afs), rk0)
        for field, rd in cf["reads"].items():
            if not rd["ok_read"]:
                continue
            st = {b: (field_status(x[0], field) if x else ("未知", None)) for b, x in cps.items()}
            bs = [b for b in order if cps[b]]
            for i1 in range(len(bs)):
                for i2 in range(i1 + 1, len(bs)):
                    ba, bb = bs[i1], bs[i2]
                    if (binds[ba][1], binds[ba][2], binds[ba][3]) == (binds[bb][1], binds[bb][2], binds[bb][3]):
                        continue
                    sa, sb = st[ba][0], st[bb][0]
                    if sa == sb:
                        continue
                    comparable = cps[ba][1] == cps[bb][1] and (cps[ba][1] == "void" or cf["checked"])
                    ev = evidence(sa, sb, cf, field, comparable)
                    miss_b = ba if sa == "明确未写" else (bb if sb == "明确未写" else None)
                    miss_p = st[miss_b][1] if miss_b else None
                    reports.append({
                        "callee": u["callee"], "argidx": k, "argform": form, "field": field,
                        "caller": [path, u["caller_func"], u["line"]],
                        "builds": {ba: {"loc": cps[ba][2], "status": sa, "rk": cps[ba][1]},
                                   bb: {"loc": cps[bb][2], "status": sb, "rk": cps[bb][1]}},
                        "missing_build": miss_b,
                        "missing_path": ({"conds": list(miss_p["conds"]), "line": miss_p["oline"]} if miss_p else None),
                        "caller_checked": cf["checked"], "preinit": sorted(cf["preinit"]), "clean_read": rd["clean_read"],
                        "evidence": ev, "score": sum(ev)})
    return ("analysed" if found_any else "no-local-addr-arg", reports)


def init_worker():
    global _DBS
    _DBS = {b: S.load_db(b) for b in S.BUILDS}


def run():
    t0 = time.time()
    rows = []
    with gzip.open(WORK / "scope.csv.gz", "rt", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["status"] != "双侧可绑定且不同":
                continue
            args = json.loads(r["args"])
            if not any(ARGFORM.match(a) for a in args):
                continue
            rows.append({"caller_file": r["caller_file"], "caller_func": r["caller_func"], "line": int(r["line"]),
                         "callee": r["callee"], "bindings": json.loads(r["bindings"]), "args": args})
    groups = defaultdict(list)
    for r in rows:
        groups[r["caller_file"]].append(r)
    print("candidate units (diff + &local-form arg):", len(rows), "in", len(groups), "TUs", flush=True)
    reports, stat = [], Counter()
    with Pool(12, initializer=init_worker) as pool:
        for k, (rs, st) in enumerate(pool.imap_unordered(analyse_group, sorted(groups.items()), chunksize=1)):
            reports.extend(rs)
            stat.update(st)
            if k % 20 == 0:
                print(f"  groups {k}/{len(groups)} reports {len(reports)} {round(time.time() - t0)}s", flush=True)
    # pairs.csv / reports.jsonl
    with open(WORK / "reports.jsonl", "w") as f:
        for r in reports:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(WORK / "pairs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["callee", "argidx", "field", "caller_file", "caller_func", "line", "build_a", "loc_a", "status_a", "build_b",
                    "loc_b", "status_b", "missing_build", "missing_line", "checked", "preinit", "clean_read", "e1", "e2", "e3"])
        for r in reports:
            (ba, A), (bb, B) = list(r["builds"].items())
            w.writerow([r["callee"], r["argidx"], r["field"], *r["caller"], ba, f"{A['loc'][0]}:{A['loc'][1]}", A["status"], bb,
                        f"{B['loc'][0]}:{B['loc'][1]}", B["status"], r["missing_build"],
                        (r["missing_path"] or {}).get("line"), r["caller_checked"], "|".join(r["preinit"]), r["clean_read"], *r["evidence"]])
    # merge (criteria 四): interface, arg index, field, missing implementation
    merged = {}
    for r in reports:
        mb = r["missing_build"]
        miss_loc = tuple(r["builds"][mb]["loc"]) if mb else None
        other = tuple(sorted(tuple(x["loc"]) for x in r["builds"].values()))
        key = (r["callee"], r["argidx"], r["field"], miss_loc or other)
        m = merged.setdefault(key, {"key": [r["callee"], r["argidx"], r["field"], list(miss_loc or other)], "witnesses": [],
                                    "score": -1, "evidence": None, "best": None})
        m["witnesses"].append({"caller": r["caller"], "builds": r["builds"], "evidence": r["evidence"],
                               "missing_path": r["missing_path"], "preinit": r["preinit"], "checked": r["caller_checked"]})
        if r["score"] > m["score"]:
            m["score"], m["evidence"], m["best"] = r["score"], r["evidence"], r

    def h(m):
        return hashlib.sha256((SEED + "|" + json.dumps(m["key"])).encode()).hexdigest()
    lst = list(merged.values())
    coarse = sorted(lst, key=h)
    evid = sorted(lst, key=lambda m: (-m["score"], h(m)))
    (HERE / "ranked_coarse.json").write_text(json.dumps(coarse[:60], indent=1, ensure_ascii=False))
    (HERE / "ranked_evidence.json").write_text(json.dumps(evid[:60], indent=1, ensure_ascii=False))
    summ = {"candidate_units": len(rows), "tus": len(groups), "unit_status": dict(stat), "reports": len(reports),
            "merged": len(lst), "interfaces_in_reports": len({m["key"][0] for m in lst}),
            "score_hist": dict(Counter(m["score"] for m in lst)),
            "evidence_e2_e3_both": sum(1 for m in lst if m["evidence"][1] and m["evidence"][2]),
            "secs": round(time.time() - t0)}
    (HERE / "pairs_summary.json").write_text(json.dumps(summ, indent=1, ensure_ascii=False))
    print(json.dumps(summ, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    if sys.argv[1] == "selftest":
        sys.exit(0 if selftest() else 1)
    elif sys.argv[1] == "run":
        run()
