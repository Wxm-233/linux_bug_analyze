"""widthtrunc2 criteria 一/二: second version of the width-truncation check.
Read-only import of widthtrunc_20261116/widthtrunc.py; runtime replacement of its rule class and scope. WSL, no build.

    python3 widthtrunc2.py selftest
    python3 widthtrunc2.py head      -> head.json, compare_v1.json
    python3 widthtrunc2.py recall    -> recall.json
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "widthtrunc_20261116"))
import widthtrunc as W  # noqa: E402  (read-only import)

C = W.C
INIT64 = {"64BIT", "X86_64", "PPC64", "SPARC64"}


# ---------------------------------------------------------------- 1. where is code compiled only on 64-bit
class Build64:
    def __init__(self, files):
        """files: {path: text} containing Kconfig* and Makefile/Kbuild files"""
        self.k64 = self._kconfig({p: s for p, s in files.items() if re.search(r"(^|/)Kconfig[^/]*$", p)})
        self.arch = self._arch_bits({p: s for p, s in files.items() if re.match(r"arch/[^/]+/Kconfig", p)})
        self.fcond, self.dcond = self._makefiles({p: s for p, s in files.items() if re.search(r"(^|/)(Makefile|Kbuild)$", p)})
        self.lines = {}

    @staticmethod
    def _conjuncts(expr):
        expr = expr.split("#")[0].strip()
        if "||" in expr:
            return []
        out = []
        for term in expr.split("&&"):
            term = term.strip().strip("()").strip()
            if re.fullmatch(r"[A-Z0-9_]+", term):
                out.append(term)
        return out

    def _kconfig(self, kfiles):
        defs = defaultdict(list)                     # sym -> [set(conjunct syms)] per definition
        for src in kfiles.values():
            ifs, cur = [], None
            for raw in src.replace("\\\n", " ").split("\n"):
                line = raw.rstrip()
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                m = re.match(r"^(menuconfig|config)\s+([A-Za-z0-9_]+)", s)
                if m and not raw.startswith(("\t", " ")) or (m and raw.startswith(("\t", " ")) and cur is None):
                    cur = set(c for e in ifs for c in self._conjuncts(e))
                    defs[m.group(2)].append(cur)
                    continue
                if re.match(r"^if\s+", s) and not raw.startswith(("\t", " ")):
                    ifs.append(s[3:])
                    cur = None
                    continue
                if s == "endif" and not raw.startswith(("\t", " ")):
                    if ifs:
                        ifs.pop()
                    cur = None
                    continue
                if re.match(r"^(menu|endmenu|choice|endchoice|comment|source|mainmenu)\b", s) and not raw.startswith(("\t", " ")):
                    cur = None
                    continue
                if cur is not None:
                    m = re.match(r"^depends\s+on\s+(.*)$", s)
                    if m:
                        cur.update(self._conjuncts(m.group(1)))
        k64 = set(INIT64)
        changed = True
        while changed:
            changed = False
            for sym, ds in defs.items():
                if sym in k64 or not ds:
                    continue
                if all(d & k64 for d in ds):
                    k64.add(sym)
                    changed = True
        return k64

    @staticmethod
    def _arch_bits(afiles):
        by = defaultdict(str)
        for p, s in afiles.items():
            by[p.split("/")[1]] += "\n" + s
        out = {}
        for a, s in by.items():
            m = re.search(r"^config 64BIT\s*\n((?:[ \t]+.*\n|\s*\n)*)", s, re.M)
            if not m:
                out[a] = "32"
                continue
            body = m.group(1)
            if re.search(r"^\s*def_bool\s+y\s*$", body, re.M) and "depends" not in body and not re.search(r"\bbool\b(?!\s*y)", body.replace("def_bool", "")):
                out[a] = "64"
            else:
                out[a] = "both"
        return out

    @staticmethod
    def _makefiles(mfiles):
        fcond, dcond = defaultdict(set), defaultdict(set)
        for p, s in mfiles.items():
            d = p.rsplit("/", 1)[0] if "/" in p else ""
            s = s.replace("\\\n", " ")
            for m in re.finditer(r"^\s*[\w.-]+-\$\(CONFIG_([A-Za-z0-9_]+)\)\s*[:+]?=\s*(.*)$", s, re.M):
                sym = m.group(1)
                for item in m.group(2).split():
                    if item.endswith(".o"):
                        fcond[f"{d}/{item[:-2]}.c" if d else f"{item[:-2]}.c"].add(sym)
                    elif item.endswith("/"):
                        dcond[f"{d}/{item[:-1]}" if d else item[:-1]].add(sym)
        return fcond, dcond

    def file_reason(self, path):
        parts = path.split("/")
        if parts[0] == "arch" and len(parts) > 1 and self.arch.get(parts[1]) == "64":
            return f"arch:{parts[1]}"
        if path.endswith("_64.c"):
            return "file:_64.c"
        conds = set(self.fcond.get(path, ()))
        for i in range(1, len(parts)):
            conds |= self.dcond.get("/".join(parts[:i]), set())
        hit = sorted(conds & self.k64)
        return f"make:CONFIG_{hit[0]}" if hit else None

    def _cond64(self, kind, expr):
        """(positive_only64, negative_only64) for one directive"""
        expr = expr.split("/*")[0].strip()
        syms = re.findall(r"CONFIG_([A-Za-z0-9_]+)", expr)
        if kind == "ifdef":
            return (bool(syms) and syms[0] in self.k64), False
        if kind == "ifndef":
            return False, (bool(syms) and syms[0] in self.k64)
        if "||" in expr:
            return False, False
        e = expr.replace(" ", "")
        if re.search(r"BITS_PER_LONG==64", e):
            return True, False
        if re.search(r"BITS_PER_LONG(==32|!=64)", e):
            return False, True
        pos = any(s in self.k64 and not re.search(rf"!\s*(defined\s*\(\s*)?(IS_ENABLED\s*\(\s*)?CONFIG_{s}\b", expr) for s in syms)
        neg = len(syms) == 1 and syms[0] in self.k64 and bool(re.search(rf"!\s*(defined\s*\(\s*)?(IS_ENABLED\s*\(\s*)?CONFIG_{syms[0]}\b", expr)) \
            and "&&" not in expr
        return pos, neg

    def line_only64(self, path, src):
        if path in self.lines:
            return self.lines[path]
        res, stack = set(), []      # frames: [pos, neg, in_else]
        lines = src.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]
            full = line
            while full.endswith("\\") and i + 1 < len(lines):
                i += 1
                full = full[:-1] + " " + lines[i]
            m = re.match(r"^\s*#\s*(if|ifdef|ifndef|elif|else|endif)\b(.*)$", full)
            if m:
                k, rest = m.group(1), m.group(2)
                if k in ("if", "ifdef", "ifndef"):
                    pos, neg = self._cond64(k, rest)
                    stack.append([pos, neg, False])
                elif k == "elif" and stack:
                    pos, neg = self._cond64("if", rest)
                    stack[-1] = [pos, False, False]
                elif k == "else" and stack:
                    stack[-1][2] = True
                elif k == "endif" and stack:
                    stack.pop()
            elif any((not f[2] and f[0]) or (f[2] and f[1]) for f in stack):
                res.add(i + 1)
            i += 1
        self.lines[path] = res
        return res


# ---------------------------------------------------------------- 2-4. rule changes
class Fn2(W.Fn):
    def _mask_class(self, j):
        t = self.t
        if re.match(r"^[A-Za-z_]\w*$", t[j][0]) and "mask" in t[j][0].lower() and j + 1 < len(t) and t[j + 1][0] == "(":
            return None                                   # criteria 一.2
        return super()._mask_class(j)

    def _left_wide(self, j):
        t = self.t
        k = j - 1
        if t[k][0] == ")":
            o = self._match_back(k)
            if o is not None and o - 1 > self.b0 and re.match(r"^[A-Za-z_]\w*$", t[o - 1][0]) and t[o - 1][0] not in C.KEYW:
                return self.prim_class(o - 1, k + 1) == "W"   # criteria 一.3: a call is judged by its return type
        return super()._left_wide(j)

    def target_type(self, kind, desc):
        if kind == "return":
            r = self.T.ret.get(self.name)
            return r[0] if r else None
        if kind == "arg":
            f, idx = desc.split("#")
            ps = self.T.params.get(f, [])
            return ps[int(idx)][1] if int(idx) < len(ps) else None
        if desc in self.env:
            return self.env[desc][0]
        return None

    def reduced(self, lo, hi, ttype):
        """criteria 一.4"""
        t = self.t
        toks = [x[0] for x in t[lo:hi]]
        if any(x in W.REDUCE_TOK - {">>"} for x in toks) or any(x in W.REDUCE_FN for x in toks):
            return True
        for m in range(lo, hi):
            if t[m][0] != ">>":
                continue
            if m + 1 < hi and t[m + 1][0] == "(":
                e = C.match_fwd(t, m + 1)
                amt = [x[0] for x in t[m + 2:e]]
            else:
                amt = [t[m + 1][0]] if m + 1 < hi else []
            if len(amt) == 1 and re.fullmatch(r"\d+[uUlL]*", amt[0]) and int(re.sub(r"[uUlL]+$", "", amt[0])) >= 32:
                return True
            if "PAGE_SHIFT" in amt and ttype == "pgoff_t":
                return True
        return False

    def wide_source2(self, lo, hi, ttype):
        lo, hi = self.strip(lo, hi)
        if self.reduced(lo, hi, ttype):
            return False
        return any(self.prim_class(a, b) == "W" for a, b in self.primaries(lo, hi))

    def findings(self):
        out = []
        guarded = bool(self.ids & W.GUARD)
        t = self.t
        for kind, tcls, desc, lo, hi, line in self.events:
            if tcls == "N" and self.wide_source2(lo, hi, self.target_type(kind, desc)):
                out.append(("A", line, f"{kind}:{desc}", C.norm(t, lo, hi)[:120]))
            if tcls == "W":
                for j in range(lo, hi):
                    if t[j][0] == "<<" and self._left_operand_class(lo, j) == "N":
                        out.append(("B", t[j][1], f"{kind}:{desc}", C.norm(t, lo, hi)[:120]))
                        break
        for j in range(self.b0 + 1, self.b1 - 1):
            if t[j][0] == "&" and t[j + 1][0] == "~" and self._mask_class(j + 2) == "N" and self._left_wide(j):
                out.append(("C", t[j][1], "mask", C.norm(t, max(self.b0, j - 6), min(self.b1, j + 8))[:120]))
        return out, guarded


W.Fn = Fn2   # runtime replacement inside the imported module; files unchanged


def in_scope2(p):
    return W_in_scope(p) or (p.endswith(".h") and p.startswith("fs/"))   # criteria 一.5


W_in_scope = W.in_scope
W.in_scope = in_scope2


# ---------------------------------------------------------------- driver
def build_files(rev):
    names = [p for p in C.git("ls-tree", "-r", "--name-only", rev).split("\n")
             if re.search(r"(^|/)Kconfig[^/]*$", p) or (re.search(r"(^|/)(Makefile|Kbuild)$", p)
                                                         and (p.count("/") == 0 or p.startswith(("mm/", "kernel/", "lib/", "fs/", "arch/"))))]
    return C.cat_files(rev, names)


def analyze(rev=None, blobs=None, bfiles=None):
    blobs = blobs if blobs is not None else W.blobs_of(rev)
    B = Build64(bfiles if bfiles is not None else build_files(rev))
    rows, ranges = W.analyze(blobs)
    for r in rows:
        why = B.file_reason(r["file"])
        if not why and r["line"] in B.line_only64(r["file"], blobs.get(r["file"], "")):
            why = "ifdef64"
        r["only64"] = why
    return rows, ranges, B


def candidates(rows):
    return W.candidates([r for r in rows if not r["only64"]])


def head():
    rows, _, B = analyze(W.HEAD)
    cands = candidates(rows)
    by = defaultdict(int)
    for r in cands:
        by[r["form"]] += 1
    v1 = json.loads((CT / "widthtrunc_20261116/head.json").read_text())
    adj = json.loads((CT / "widthtrunc_20261116/adjudication.json").read_text(encoding="utf-8"))["rows"]
    keyset = {(r["file"], r["line"], r["form"]) for r in cands}
    v1rank = {(r["file"], r["line"], r["form"]): i for i, r in enumerate(v1["ranked"], 1)}
    v1top = v1["ranked"][:30]
    cmp_rows = []
    for a, r in zip(adj, v1top):
        k = (r["file"], r["line"], r["form"])
        why = next((x["only64"] for x in rows if (x["file"], x["line"], x["form"]) == k), "rule")
        cmp_rows.append({"k": a["k"], "loc": a["loc"], "final_v1": a["final"], "kept_v2": k in keyset, "removed_by": None if k in keyset else why})
    comp = {"v1_possible_kept": sum(1 for c in cmp_rows if c["final_v1"] == "可能" and c["kept_v2"]),
            "v1_possible_total": sum(1 for c in cmp_rows if c["final_v1"] == "可能"),
            "v1_impossible_removed": sum(1 for c in cmp_rows if c["final_v1"] == "不可能" and not c["kept_v2"]),
            "v1_impossible_total": sum(1 for c in cmp_rows if c["final_v1"] == "不可能"), "rows": cmp_rows}
    (HERE / "compare_v1.json").write_text(json.dumps(comp, indent=1, ensure_ascii=False), encoding="utf-8")
    only = defaultdict(int)
    for r in rows:
        if r["only64"] and not r["guarded"]:
            only[r["only64"].split(":")[0]] += 1
    res = {"candidates": len(cands), "by_form": dict(by), "v1": {"candidates": v1["candidates"], "by_form": v1["by_form"]},
           "removed_only64_by_reason": dict(only), "k64_size": len(B.k64), "arch_bits": B.arch,
           "ranked": [dict(r, v1_rank=v1rank.get((r["file"], r["line"], r["form"]))) for r in cands]}
    (HERE / "head.json").write_text(json.dumps(res, indent=1))
    print("candidates", len(cands), dict(by), "| v1", v1["candidates"], v1["by_form"])
    print("removed (only64) by reason", dict(only), "| K64 symbols", len(B.k64))
    print("arch bits", B.arch)
    print("v1 top30: possible kept", comp["v1_possible_kept"], "/", comp["v1_possible_total"], "| impossible removed",
          comp["v1_impossible_removed"], "/", comp["v1_impossible_total"])
    for i, r in enumerate(cands[:45], 1):
        print(f"{i:3} {r['form']} {r['file']}:{r['line']} {r['func']} [{r['where']}] v1={res['ranked'][i-1]['v1_rank']} {r['text'][:70]}")


def recall():
    out = []
    for c in W.SAMPLES:
        rev = f"{c}^"
        rows, ranges, _ = analyze(rev)
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
    ok_v1 = W.selftest()
    bfiles = {
        "arch/a64/Kconfig": "config A64\n\tdef_bool y\n\nconfig 64BIT\n\tdef_bool y\n",
        "arch/b32/Kconfig": "config B32\n\tdef_bool y\n",
        "arch/cboth/Kconfig": "config 64BIT\n\tbool \"64-bit kernel\"\n",
        "mm/Kconfig": "menuconfig MEMORY_HOTPLUG\n\tbool \"hp\"\n\tdepends on 64BIT\n\nif MEMORY_HOTPLUG\nconfig MEMORY_HOTREMOVE\n\tbool \"hr\"\nendif\n"
                      "config ZONE_DEVICE\n\tbool \"zd\"\n\tdepends on MEMORY_HOTREMOVE\n",
        "fs/Kconfig": "config FS_DAX\n\tbool \"dax\"\n\tdepends on MMU\n\tdepends on ZONE_DEVICE\n",
        "fs/fuse/Makefile": "fuse-y := inode.o\nfuse-$(CONFIG_FS_DAX) += dax.o\n",
    }
    blobs = {
        "include/linux/t.h": "typedef unsigned long pgoff_t;\nstruct args { u64 flags; };\n",
        "arch/a64/kernel/p.c": "int p1(const struct args *args) { unsigned long cf = args->flags; return cf; }\n",
        "arch/cboth/kernel/p.c": "int p2(const struct args *args) { unsigned long cf = args->flags; return cf; }\n",
        "kernel/x_64.c": "int p3(const struct args *args) { unsigned long cf = args->flags; return cf; }\n",
        "kernel/y.c": "#ifdef CONFIG_64BIT\nint p4(const struct args *args) { unsigned long cf = args->flags; return cf; }\n#endif\n"
                      "#ifndef CONFIG_64BIT\nint p5a(void) { return 0; }\n#else\nint p5(const struct args *args) { unsigned long cf = args->flags; return cf; }\n#endif\n",
        "fs/fuse/dax.c": "int p6(const struct args *args) { unsigned long cf = args->flags; return cf; }\n",
        "fs/fuse/inode.c": "int p7(const struct args *args) { unsigned long cf = args->flags; return cf; }\n",
        "mm/m.c": "\n".join([
            "loff_t q1(loff_t off, struct hstate *h) { return off & ~huge_page_mask(h); }",
            "loff_t q2(struct folio *folio, loff_t start, size_t bsz) { return offset_in_folio(folio, start) & ~(bsz - 1); }",
            "unsigned long q3(u64 ofs, int bits) { unsigned long lcn = ofs >> bits; return lcn; }",
            "pgoff_t q4(loff_t pos) { pgoff_t idx = pos >> PAGE_SHIFT; return idx; }",
        ]),
    }
    rows, _, B = analyze(blobs=blobs, bfiles=bfiles)
    got = {(r["func"], r["form"]) for r in candidates(rows)}
    checks = [("arch 64-only -> not", ("p1", "A") not in got), ("arch both -> reported", ("p2", "A") in got),
              ("_64.c -> not", ("p3", "A") not in got), ("#ifdef CONFIG_64BIT -> not", ("p4", "A") not in got),
              ("#ifndef CONFIG_64BIT #else -> not", ("p5", "A") not in got), ("obj-$(CONFIG_FS_DAX) -> not", ("p6", "A") not in got),
              ("same dir, unconditional -> reported", ("p7", "A") in got), ("~huge_page_mask() -> not", ("q1", "C") not in got),
              ("call on the left of & -> not", ("q2", "C") not in got), ("u64 >> var into unsigned long -> reported", ("q3", "A") in got),
              ("loff_t >> PAGE_SHIFT into pgoff_t -> not", ("q4", "A") not in got),
              ("K64 closure has FS_DAX", "FS_DAX" in B.k64), ("arch bits", B.arch == {"a64": "64", "b32": "32", "cboth": "both"})]
    bad = 0
    for name, ok in checks:
        bad += not ok
        print("ok " if ok else "BAD", name)
    print("selftest(widthtrunc2)", "PASS" if not bad and ok_v1 else f"FAIL {bad} v1={ok_v1}")
    return bad == 0 and ok_v1


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    cmd = sys.argv[1]
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    if not selftest():
        sys.exit(1)
    {"head": head, "recall": recall}[cmd]()
