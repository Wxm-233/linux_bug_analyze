"""widthtrunc3 criteria 一/二: third version of the width-truncation check.
Read-only import of widthtrunc2_20261117/widthtrunc2.py (which imports v1 and p1check); runtime replacement only. WSL, no build.

    python3 widthtrunc3.py selftest
    python3 widthtrunc3.py head      -> head.json, compare_v2.json, rules.json, review.txt, review.json, review_key.json
    python3 widthtrunc3.py recall    -> recall.json
"""
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "widthtrunc2_20261117"))
import widthtrunc2 as V2  # noqa: E402  (read-only import)

W, C = V2.W, V2.C
IDENT = W.IDENT
STATE = {"B": None, "td": True, "mode": "find", "writes": defaultdict(list), "bounded": set(), "td_changed": {}}


# ---------------------------------------------------------------- 一.2 / 一.3: Kconfig select, per-arch closure, Makefile blocks
def _conj(expr):
    return V2.Build64._conjuncts(expr)


def parse_kconfig(src):
    """records: {sym, deps:set, prompt:bool, defaults:[(value, condset)], selects:[(target, condset)]}"""
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
            cur = {"sym": m.group(2), "deps": set(c for e in ifs for c in _conj(e)), "prompt": False, "defaults": [], "selects": []}
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
            cur["deps"].update(_conj(m.group(1)))
            continue
        if re.match(r'^(bool|tristate|int|hex|string)\s+"', s) or re.match(r"^prompt\b", s):
            cur["prompt"] = True
            continue
        m = re.match(r"^(def_bool|def_tristate|default)\s+(\S+)(?:\s+if\s+(.*))?$", s)
        if m:
            cur["defaults"].append((m.group(2), set(_conj(m.group(3))) if m.group(3) else set()))
            continue
        m = re.match(r"^select\s+([A-Za-z0-9_]+)(?:\s+if\s+(.*))?$", s)
        if m:
            cur["selects"].append((m.group(1), set(_conj(m.group(2))) if m.group(2) else set()))
    return recs


def closure(recs):
    defs, prompt, defaults, sel = defaultdict(list), defaultdict(bool), defaultdict(list), defaultdict(list)
    for r in recs:
        defs[r["sym"]].append(r["deps"])
        prompt[r["sym"]] |= r["prompt"]
        defaults[r["sym"]] += r["defaults"]
        for tgt, cond in r["selects"]:
            sel[tgt].append((r["sym"], cond))
    k64 = set(V2.INIT64)
    changed = True
    while changed:
        changed = False
        for sym, ds in defs.items():
            if sym in k64:
                continue
            if ds and all(d & k64 for d in ds):                       # depends on (second version)
                k64.add(sym)
                changed = True
                continue
            on = any(v not in ("n", "0", '""') and not (c & k64) for v, c in defaults[sym])
            if not prompt[sym] and not on and sel.get(sym) and all(s in k64 or (c & k64) for s, c in sel[sym]):   # criteria 一.2
                k64.add(sym)
                changed = True
    return k64


class Build64v3(V2.Build64):
    def __init__(self, files):
        kfiles = {p: s for p, s in files.items() if re.search(r"(^|/)Kconfig[^/]*$", p)}
        recs = {p: parse_kconfig(s) for p, s in kfiles.items()}
        self.k64 = closure([r for rs in recs.values() for r in rs])
        common = [r for p, rs in recs.items() if not re.match(r"arch/[^/]+/", p) for r in rs]
        archs = sorted({p.split("/")[1] for p in recs if re.match(r"arch/[^/]+/", p)})
        self.k64_arch = {a: closure(common + [r for p, rs in recs.items() if p.startswith(f"arch/{a}/") for r in rs]) for a in archs}
        self.arch = self._arch_bits({p: s for p, s in files.items() if re.match(r"arch/[^/]+/Kconfig", p)})
        self.flist, self.dlist = self._makefiles3({p: s for p, s in files.items() if re.search(r"(^|/)(Makefile|Kbuild)$", p)})
        self.lines = {}

    def kset(self, path):
        m = re.match(r"arch/([^/]+)/", path)
        return self.k64_arch.get(m.group(1), self.k64) if m else self.k64

    @staticmethod
    def _makefiles3(mfiles):
        flist, dlist = defaultdict(list), defaultdict(list)
        for p, s in mfiles.items():
            d = p.rsplit("/", 1)[0] if "/" in p else ""
            stack = []
            for line in s.replace("\\\n", " ").split("\n"):
                st = line.split("#")[0].strip()
                if not st:
                    continue
                m = re.match(r"^ifeq\s*\(\s*((?:\$\(CONFIG_[A-Za-z0-9_]+\))+)\s*,\s*(y+)\s*\)$", st)
                if m:
                    syms = re.findall(r"CONFIG_([A-Za-z0-9_]+)", m.group(1))
                    stack.append(set(syms) if len(m.group(2)) == len(syms) else set())
                    continue
                m = re.match(r"^ifneq\s*\(\s*\$\(CONFIG_([A-Za-z0-9_]+)\)\s*,\s*\)$", st) or re.match(r"^ifdef\s+CONFIG_([A-Za-z0-9_]+)$", st)
                if m:
                    stack.append({m.group(1)})
                    continue
                if re.match(r"^(ifeq|ifneq|ifdef|ifndef)\b", st):
                    stack.append(set())
                    continue
                if st == "else" or st.startswith("else "):
                    if stack:
                        stack[-1] = set()
                    continue
                if st == "endif":
                    if stack:
                        stack.pop()
                    continue
                m = re.match(r"^[\w.-]+-(\$\(CONFIG_([A-Za-z0-9_]+)\)|y|objs)\s*[:+]?=\s*(.*)$", st)
                if not m:
                    continue
                conds = set().union(*stack) if stack else set()
                if m.group(2):
                    conds = conds | {m.group(2)}
                for item in m.group(3).split():
                    if item.endswith(".o"):
                        flist[f"{d}/{item[:-2]}.c" if d else f"{item[:-2]}.c"].append(conds)
                    elif item.endswith("/"):
                        dlist[f"{d}/{item[:-1]}" if d else item[:-1]].append(conds)
        return flist, dlist

    def file_reason(self, path):
        parts = path.split("/")
        if parts[0] == "arch" and len(parts) > 1 and self.arch.get(parts[1]) == "64":
            return f"arch:{parts[1]}"
        if path.endswith("_64.c"):
            return "file:_64.c"
        ks = self.kset(path)
        L = self.flist.get(path)
        if L and all(c & ks for c in L):
            return "make:CONFIG_" + sorted(L[0] & ks)[0]
        for i in range(1, len(parts)):
            D = self.dlist.get("/".join(parts[:i]))
            if D and all(c & ks for c in D):
                return "make:CONFIG_" + sorted(D[0] & ks)[0]
        return None

    def line_only64(self, path, src):
        if path in self.lines:
            return self.lines[path]
        saved = self.k64
        self.k64 = self.kset(path)
        try:
            return super().line_only64(path, src)
        finally:
            self.k64 = saved


# ---------------------------------------------------------------- 一.1: conditional typedef
TD_RE = re.compile(r"\btypedef\s+([^;{}()]+?)\s+\**\s*([A-Za-z_]\w*)\s*;")


class Types3(W.Types):
    def __init__(self, blobs):
        super().__init__(blobs)
        B = STATE["B"]
        if not STATE["td"] or B is None:
            return
        defs = defaultdict(list)
        for p, src in blobs.items():
            if "typedef" not in src:
                continue
            s = C.strip(src)
            for m in TD_RE.finditer(s):
                if "*" in m.group(0):
                    continue
                defs[m.group(2)].append((W.norm_type(m.group(1).split()), p, s.count("\n", 0, m.start()) + 1))
        for name, ds in defs.items():
            if len({d[0] for d in ds}) < 2:
                continue
            keep = [d for d in ds if d[2] not in B.line_only64(d[1], blobs[d[1]])]
            if keep and len(keep) < len(ds) and self.typedef.get(name) != keep[0][0]:
                STATE["td_changed"][name] = (self.typedef.get(name), keep[0][0])
                self.typedef[name] = keep[0][0]


# ---------------------------------------------------------------- 一.4: field writers within a subsystem
NARROW_BASE = {"int", "unsigned int", "short", "unsigned short", "char", "unsigned char", "signed char", "short int", "signed int",
               "unsigned short int", "u8", "u16", "u32", "s8", "s16", "s32", "__u8", "__u16", "__u32", "__s8", "__s16", "__s32",
               "__le16", "__le32", "__be16", "__be32", "uint8_t", "uint16_t", "uint32_t", "int8_t", "int16_t", "int32_t", "bool", "_Bool"}
NARROW_FN = {"le16_to_cpu", "le32_to_cpu", "be16_to_cpu", "be32_to_cpu", "get_unaligned_le32", "get_unaligned_be32",
             "get_unaligned_le16", "get_unaligned_be16", "get_next_ino"}
SETTERS = {("iget_locked", 1): ("struct inode", "i_ino")}
ASSIGN_OPS = {"=", "+=", "-=", "|=", "&=", "^=", "<<=", ">>=", "*=", "/=", "%=", "++", "--"}


def scope(path):
    parts = path.split("/")
    if parts[0] in ("fs", "arch", "kernel") and len(parts) > 2:
        return "/".join(parts[:2])
    return parts[0]


class Fn3(V2.Fn2):
    def _narrow_type(self, ty, depth=0):
        if ty in W.N_BASE or ty in NARROW_BASE or ty.startswith("enum "):
            return True
        if ty in W.W_BASE:
            return False
        if depth < 8 and ty in self.T.typedef and self.T.typedef[ty] != ty:
            return self._narrow_type(self.T.typedef[ty], depth + 1)
        return False

    def _struct(self, ty):
        return ty if ty.startswith(("struct ", "union ")) else self.T.typedef.get(ty, ty)

    def prim_narrow(self, lo, hi):
        lo, hi = self.strip(lo, hi)
        t = self.t
        if hi - lo == 1 and re.fullmatch(r"[A-Z][A-Z0-9_]*", t[lo][0]):
            return True
        if hi - lo >= 3 and t[lo][0] == "(":
            end = C.match_fwd(t, lo)
            inner = [x[0] for x in t[lo + 1:end]]
            if inner and end + 1 < hi and all(self.T.is_type_word(x) or x == "*" for x in inner):
                return "*" not in inner and self._narrow_type(W.norm_type(inner))
        ct = self.chain_type(lo, hi)
        if ct:
            return not ct[1] and self._narrow_type(ct[0])
        if hi - lo >= 3 and IDENT.match(t[lo][0]) and t[lo + 1][0] == "(" and C.match_fwd(t, lo + 1) == hi - 1:
            if t[lo][0] in NARROW_FN:
                return True
            r = self.T.ret.get(t[lo][0])
            return bool(r) and not r[1] and self._narrow_type(r[0])
        return False

    def narrow_known(self, lo, hi):
        lo, hi = self.strip(lo, hi)
        if self.reduced(lo, hi, None):
            return True
        return all(self.prim_narrow(a, b) for a, b in self.primaries(lo, hi))

    def _collect(self):
        t, sc, wr = self.t, scope(self.path), STATE["writes"]
        known = set()
        for kind, tcls, desc, lo, hi, line in self.events:
            if kind == "assign" and ("->" in desc or "." in desc) and t[lo - 1][0] == "=":
                eq = lo - 1
                s = eq - 1
                while s - 2 > self.b0 and t[s - 1][0] in ("->", ".") and IDENT.match(t[s - 2][0]):
                    s -= 2
                if s >= eq - 1:
                    continue
                base, ft = self.chain_type(s, eq - 2), self.chain_type(s, eq)
                if not base or not ft or ft[1] or self.T.cls(ft[0]) != "W":
                    continue
                wr[(sc, self._struct(base[0]), t[eq - 1][0])].append(self.narrow_known(lo, hi))
                known.add(eq - 1)
            elif kind == "arg":
                f, idx = desc.split("#")
                key = SETTERS.get((f, int(idx)))
                if key:
                    wr[(sc,) + key].append(self.narrow_known(lo, hi))
        for j in range(self.b0 + 1, self.b1 - 2):
            y = t[j][0]
            if y in ("->", ".") and IDENT.match(t[j + 1][0]) and t[j + 2][0] in ASSIGN_OPS and j + 1 not in known:
                wr[(sc, "?", t[j + 1][0])].append(False)
            elif y == "&" and not (IDENT.match(t[j - 1][0]) and t[j - 1][0] not in C.KEYW) and t[j - 1][0] not in (")", "]") \
                    and not re.match(r"^\d", t[j - 1][0]) and IDENT.match(t[j + 1][0]):
                k = j + 1
                while k + 2 < self.b1 and t[k + 1][0] in ("->", ".") and IDENT.match(t[k + 2][0]):
                    k += 2
                if k > j + 1:
                    wr[(sc, "?", t[k][0])].append(False)

    def prim_class(self, lo, hi):
        if STATE["bounded"]:
            a, b = self.strip(lo, hi)
            t = self.t
            if b - a >= 3 and IDENT.match(t[a][0]) and t[b - 2][0] in ("->", ".") and IDENT.match(t[b - 1][0]):
                base = self.chain_type(a, b - 2)
                if base and (scope(self.path), self._struct(base[0]), t[b - 1][0]) in STATE["bounded"]:
                    return None                                        # criteria 一.4
        return super().prim_class(lo, hi)

    def findings(self):
        if STATE["mode"] == "collect":
            self._collect()
            return [], False
        return super().findings()


def compute_bounded(writes):
    out = set()
    for (sc, st, f), vals in writes.items():
        if st == "?" or not vals or not all(vals):
            continue
        if writes.get((sc, "?", f)):
            continue
        out.add((sc, st, f))
    return out


W.Fn = Fn3          # runtime replacement inside the imported modules; files unchanged
W.Types = Types3


# ---------------------------------------------------------------- driver
def analyze3(rev=None, blobs=None, bfiles=None, td=True, field=True):
    blobs = blobs if blobs is not None else W.blobs_of(rev)
    B = Build64v3(bfiles if bfiles is not None else V2.build_files(rev))
    STATE.update(B=B, td=td, td_changed={}, writes=defaultdict(list), bounded=set())
    if field:
        STATE["mode"] = "collect"
        W.analyze(blobs)
        STATE["bounded"] = compute_bounded(STATE["writes"])
    STATE["mode"] = "find"
    rows, ranges = W.analyze(blobs)
    for r in rows:
        why = B.file_reason(r["file"])
        if not why and r["line"] in B.line_only64(r["file"], blobs.get(r["file"], "")):
            why = "ifdef64"
        r["only64"] = why
    info = {"bounded": sorted("|".join(k) for k in STATE["bounded"]), "td_changed": dict(STATE["td_changed"]), "k64": len(B.k64)}
    return rows, ranges, B, info


def candidates(rows):
    return V2.candidates(rows)


def key(r):
    return (r["file"], r["line"], r["form"])


def reviewed_locs():
    """locations judged in v1 / v2 -> final verdict"""
    out = {}
    for d in ("widthtrunc_20261116", "widthtrunc2_20261117"):
        for x in json.loads((CT / d / "adjudication.json").read_text(encoding="utf-8"))["rows"]:
            out[x["loc"]] = x["final"]
    return out


def head():
    blobs = W.blobs_of(W.HEAD)
    bfiles = V2.build_files(W.HEAD)
    rows, _, B, info = analyze3(blobs=blobs, bfiles=bfiles)
    cands = candidates(rows)
    rows_ntd, _, _, _ = analyze3(blobs=blobs, bfiles=bfiles, td=False)
    rows_nf, _, _, _ = analyze3(blobs=blobs, bfiles=bfiles, field=False)
    c_ntd, c_nf = {key(r) for r in candidates(rows_ntd)}, {key(r) for r in candidates(rows_nf)}
    ks = {key(r) for r in cands}
    raw = {key(r): r for r in rows}
    v2 = json.loads((CT / "widthtrunc2_20261117/head.json").read_text())
    v2rank = {key(r): i for i, r in enumerate(v2["ranked"], 1)}

    def why_removed(k):
        if k in c_ntd:
            return "typedef"
        if k in c_nf:
            return "field"
        r = raw.get(k)
        if r and r["only64"]:
            return "build:" + r["only64"].split(":")[0]
        return "other"

    removed = defaultdict(lambda: defaultdict(int))
    for r in v2["ranked"]:
        if key(r) not in ks:
            removed[why_removed(key(r))][r["form"]] += 1
    added = [r for r in cands if key(r) not in v2rank]
    by = defaultdict(int)
    for r in cands:
        by[r["form"]] += 1
    # regression on the 41 reviewed v2 rows
    rev = reviewed_locs()
    cmp_rows = []
    for i, r in enumerate(v2["ranked"][:41], 1):
        loc = f"{r['file']}:{r['line']}"
        kept = key(r) in ks
        cmp_rows.append({"v2_rank": i, "loc": loc, "form": r["form"], "final": rev.get(loc), "kept_v3": kept,
                         "removed_by": None if kept else why_removed(key(r))})
    comp = {"possible_kept": sum(c["final"] == "可能" and c["kept_v3"] for c in cmp_rows),
            "possible_total": sum(c["final"] == "可能" for c in cmp_rows),
            "impossible_removed": sum(c["final"] == "不可能" and not c["kept_v3"] for c in cmp_rows),
            "impossible_total": sum(c["final"] == "不可能" for c in cmp_rows), "rows": cmp_rows}
    (HERE / "compare_v2.json").write_text(json.dumps(comp, indent=1, ensure_ascii=False), encoding="utf-8")
    res = {"candidates": len(cands), "by_form": dict(by), "v2": {"candidates": v2["candidates"], "by_form": v2["by_form"]},
           "removed_from_v2": {k: dict(v) for k, v in removed.items()}, "added_vs_v2": len(added),
           "added_examples": [f"{r['form']} {r['file']}:{r['line']} {r['func']}" for r in added[:20]],
           "k64": info["k64"], "k64_arch_sizes": {a: len(s) for a, s in B.k64_arch.items()},
           "td_changed": info["td_changed"], "bounded_n": len(info["bounded"]),
           "ranked": [dict(r, v2_rank=v2rank.get(key(r))) for r in cands]}
    (HERE / "head.json").write_text(json.dumps(res, indent=1))
    (HERE / "rules.json").write_text(json.dumps({"bounded": info["bounded"], "td_changed": info["td_changed"],
                                                 "k64_minus_v2": sorted(B.k64 - V2.Build64({p: s for p, s in bfiles.items()}).k64)},
                                                indent=1, ensure_ascii=False), encoding="utf-8")
    print("candidates", len(cands), dict(by), "| v2", v2["candidates"], v2["by_form"])
    print("removed from v2 by rule", {k: dict(v) for k, v in removed.items()}, "| added", len(added))
    print("typedef changed", info["td_changed"])
    print("bounded fields", len(info["bounded"]), "| K64", info["k64"])
    print("regression: possible kept", comp["possible_kept"], "/", comp["possible_total"], "| impossible removed",
          comp["impossible_removed"], "/", comp["impossible_total"])
    for c in cmp_rows:
        if not c["kept_v3"]:
            print("   removed", c["v2_rank"], c["loc"], c["form"], c["final"], c["removed_by"])
    # ---- review set (criteria 二.5)
    rng = random.Random(20261117)
    cb = [r for r in cands if r["form"] in "CB" and f"{r['file']}:{r['line']}" not in rev]
    pool_a = [r for r in cands if r["form"] == "A" and f"{r['file']}:{r['line']}" not in rev]
    ga = cb + rng.sample(pool_a, max(0, 30 - len(cb)))
    field_removed = [r for r in candidates(rows_nf) if key(r) not in ks]
    gb = rng.sample(field_removed, min(10, len(field_removed)))
    items = [("甲", r) for r in ga] + [("乙", r) for r in gb]
    rng.shuffle(items)
    review, keyrows = [], []
    for k, (g, r) in enumerate(items, 1):
        review.append({"k": k, "file": r["file"], "func": r["func"], "line": r["line"], "form": r["form"], "where": r["where"]})
        keyrows.append({"k": k, "group": g, "loc": f"{r['file']}:{r['line']}", "form": r["form"]})
    (HERE / "review.json").write_text(json.dumps(review, indent=1, ensure_ascii=False), encoding="utf-8")
    (HERE / "review_key.json").write_text(json.dumps({"甲_cb": len(cb), "甲_a_sample": len(ga) - len(cb), "a_pool": len(pool_a),
                                                      "field_removed_pool": len(field_removed), "rows": keyrows},
                                                     indent=1, ensure_ascii=False), encoding="utf-8")
    form = {"A": "A 窄化：恒 64 位的值交给在 32 位架构上只有 32 位的类型", "B": "B 移位溢出：32/64 位可变的值先左移，再当 64 位用",
            "C": "C 掩码截断：64 位的值 & ~(32/64 位可变的值 …)，32 位架构上会清掉高 32 位"}
    src = C.cat_files(W.HEAD, sorted({d["file"] for d in review}))
    out = []
    for d in review:
        lines = src[d["file"]].split("\n")
        a, b = max(1, d["line"] - 25), min(len(lines), d["line"] + 6)
        out += ["=" * 90, f"[{d['k']}] {d['file']}:{d['line']}  函数 {d['func']}  形态 {form[d['form']]}  位置 {d['where']}",
                "    32 位组合：arm32, i386, riscv32, mips32"]
        out += [f"{'>>' if i == d['line'] else '  '}{i:5d} {lines[i - 1]}" for i in range(a, b + 1)]
    (HERE / "review.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("review: 甲 CB", len(cb), "A sample", len(ga) - len(cb), "of", len(pool_a), "| 乙", len(gb), "of", len(field_removed))


def recall():
    out = []
    for c in W.SAMPLES:
        rows, ranges, _, _ = analyze3(f"{c}^")
        cands = candidates(rows)
        tch = W.touched(c, ranges)
        tnames = {n for _, n in tch}
        h1 = [(i, r) for i, r in enumerate(cands, 1) if (r["file"], r["func"]) in tch]
        h2 = h1 + [(i, r) for i, r in enumerate(cands, 1) if r["form"] == "A" and r["where"].startswith("arg:")
                   and r["where"][4:].split("#")[0] in tnames and (i, r) not in h1]
        out.append({"commit": c, "hit1": bool(h1), "hit2": bool(h2), "n_candidates": len(cands),
                    "hits": [{"rank": i, "file": r["file"], "func": r["func"], "form": r["form"], "where": r["where"]} for i, r in h2[:8]]})
        print(c, "hit1" if h1 else "-", "hit2" if h2 else "-", [(x["rank"], x["form"], x["func"]) for x in out[-1]["hits"][:4]], flush=True)
    n1, n2 = sum(o["hit1"] for o in out), sum(o["hit2"] for o in out)
    (HERE / "recall.json").write_text(json.dumps({"n": len(out), "hit1": n1, "hit2": n2, "rows": out}, indent=1))
    print("recall 口径一", n1, "/", len(out), "口径二", n2, "/", len(out))


def selftest():
    STATE.update(B=None, bounded=set(), mode="find")
    ok_v2 = V2.selftest()          # runs v1 + v2 cases through the replaced classes (bounded empty, td without B)
    bfiles = {
        "arch/la/Kconfig": "config LA\n\tdef_bool y\n\tselect SUPH if 64BIT\n\nconfig 64BIT\n\tbool \"64-bit\"\n",
        "arch/arm32/Kconfig": "config ARM32\n\tdef_bool y\n\tselect SUPH\n",
        "arch/mp/Kconfig": "config MP\n\tdef_bool y\n\nconfig 64BIT\n\tbool \"64-bit\"\n\nconfig HID\n\tbool\n\nconfig HID2\n\tbool\n\n"
                           "config O32\n\tbool \"o32\"\n\tdepends on 64BIT\n\tselect HID\n\tselect HID2\n\thelp\n\t  config FAKE in help\n\n"
                           "config X\n\tbool \"x\"\n\tselect HID2\n",
        "mm/Kconfig": "config SUPH\n\tbool\n\nconfig NTC\n\tbool \"ntc\"\n\tdepends on 64BIT\n",
        "arch/la/mm/Makefile": "obj-$(CONFIG_SUPH) += hp.o\n",
        "mm/Makefile": "obj-$(CONFIG_SUPH) += hcommon.o\nobj-$(CONFIG_64BIT) += m.o\nobj-$(CONFIG_FOO) += m.o\n",
        "arch/mp/kernel/Makefile": "obj-$(CONFIG_HID) += c32.o\nobj-$(CONFIG_HID2) += d32.o\n",
        "kernel/bpf/Makefile": "ifeq ($(CONFIG_MMU)$(CONFIG_64BIT),yy)\nobj-$(CONFIG_BPF) += ar.o\nendif\nobj-y += core.o\n"
                               "ifeq ($(CONFIG_64BIT),y)\nobj-y += a64.o\nelse\nobj-y += a32.o\nendif\n",
    }
    fnA = "int {n}(const struct args *args) {{ unsigned long cf = args->flags; return cf; }}\n"
    blobs = {
        "include/linux/t.h": "typedef unsigned long pgoff_t;\nstruct args { u64 flags; };\nstruct inode { u64 i_ino; };\nstruct raw { __le32 ino; };\n"
                             "struct inode *iget_locked(struct super_block *sb, u64 ino);\n",
        "fs/zz/ntc.h": "#ifdef CONFIG_NTC\ntypedef u64 CL;\n#else\ntypedef u32 CL;\n#endif\n",
        "fs/zz/t.c": "loff_t t1(pgoff_t idx) { CL c = idx << PAGE_SHIFT; return c; }\n",
        "arch/la/mm/hp.c": fnA.format(n="s1"), "mm/hcommon.c": fnA.format(n="s2"), "mm/m.c": fnA.format(n="s3"),
        "arch/mp/kernel/c32.c": fnA.format(n="s4"), "arch/mp/kernel/d32.c": fnA.format(n="s5"),
        "kernel/bpf/ar.c": fnA.format(n="m1"), "kernel/bpf/core.c": fnA.format(n="m2"),
        "kernel/bpf/a64.c": fnA.format(n="m3"), "kernel/bpf/a32.c": fnA.format(n="m4"),
        "include/linux/zz.h": "int zz_lookup(unsigned long ino);\n",
        "fs/zz/a.c": "void z1(struct inode *inode, unsigned long ino) { inode->i_ino = ino; }\n"
                     "int z2(struct inode *inode) { return zz_lookup(inode->i_ino); }\n",
        "fs/yy/a.c": "void y1(struct inode *inode, u64 v) { inode->i_ino = v; }\nint y2(struct inode *inode) { return zz_lookup(inode->i_ino); }\n",
        "fs/xx/a.c": "struct inode *x1(struct super_block *sb, u32 n) { return iget_locked(sb, n); }\n"
                     "int x2(struct inode *inode) { return zz_lookup(inode->i_ino); }\n",
        "fs/ww/a.c": "void w1(struct inode *inode, unsigned long ino) { inode->i_ino = ino; get_it(&inode->i_ino); }\n"
                     "int w2(struct inode *inode) { return zz_lookup(inode->i_ino); }\n",
        "fs/vv/a.c": "void v1(struct inode *inode, struct raw *raw) { inode->i_ino = le32_to_cpu(raw->ino); }\n"
                     "int v2(struct inode *inode) { return zz_lookup(inode->i_ino); }\n",
        "fs/uu/a.c": "void u1(struct inode *inode, struct raw *raw) { inode->i_ino = MAGIC_INO; }\n"
                     "int u2(struct inode *inode) { return zz_lookup(inode->i_ino); }\n",
    }
    rows, _, B, info = analyze3(blobs=blobs, bfiles=bfiles)
    got = {(r["func"], r["form"]) for r in candidates(rows)}
    rows0, _, _, _ = analyze3(blobs=blobs, bfiles=bfiles, td=False, field=False)
    got0 = {(r["func"], r["form"]) for r in candidates(rows0)}
    checks = [("typedef off: CL=u64 -> B reported", ("t1", "B") in got0), ("typedef on: CL=u32 -> not", ("t1", "B") not in got),
              ("select if 64BIT, arch file -> not", ("s1", "A") not in got), ("select by 32-bit arch, common file -> reported", ("s2", "A") in got),
              ("listed twice, one unconditional -> reported", ("s3", "A") in got),
              ("hidden, selected only by 64-bit option -> not", ("s4", "A") not in got),
              ("hidden, also selected by prompt option -> reported", ("s5", "A") in got),
              ("ifeq yy block -> not", ("m1", "A") not in got), ("plain obj-y -> reported", ("m2", "A") in got),
              ("ifeq y block -> not", ("m3", "A") not in got), ("else branch -> reported", ("m4", "A") in got),
              ("help text 'config FAKE' ignored", "FAKE" not in B.k64_arch.get("mp", set())),
              ("field: narrow writer -> not", ("z2", "A") not in got), ("field off -> reported", ("z2", "A") in got0),
              ("field: u64 writer -> reported", ("y2", "A") in got),
              ("field: iget_locked(u32) -> not", ("x2", "A") not in got),
              ("field: address taken -> reported", ("w2", "A") in got),
              ("field: le32_to_cpu writer -> not", ("v2", "A") not in got),
              ("field: macro constant writer -> not", ("u2", "A") not in got)]
    bad = 0
    for name, ok in checks:
        bad += not ok
        print("ok " if ok else "BAD", name)
    print("selftest(widthtrunc3)", "PASS" if not bad and ok_v2 else f"FAIL {bad} v2={ok_v2}")
    return bad == 0 and ok_v2


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    cmd = sys.argv[1]
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    if not selftest():
        sys.exit(1)
    {"head": head, "recall": recall}[cmd]()
