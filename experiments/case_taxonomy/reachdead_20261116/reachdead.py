"""F7: dead branches guarded by a parameter that is constant on every live call path (reachdead criteria 二～三).
Read-only import of reachgoto.py (-> reachsum -> reachf1 -> reachf4 -> reach -> contract). WSL, no build.

    python3 reachdead.py selftest
    python3 reachdead.py head      -> head.json, changes.json
    python3 reachdead.py recall    -> recall.json
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "reachgoto_20261116"))
import reachgoto as RG  # noqa: E402  (read-only import; installs the label-aware analyzer)

S, G, F, R, K, C = RG.S, RG.G, RG.F, RG.R, RG.K, RG.C
INT = re.compile(r"^-?(0x[0-9a-fA-F]+|\d+)[uUlL]*$")
CALLWORDS = {"return", "else", "case", "do", "sizeof"}


def lit_truth(a):
    a = (a or "").strip()
    while a.startswith("(") and a.endswith(")") and a.count("(") == 1:
        a = a[1:-1].strip()
    if a in ("false", "NULL"):
        return False
    if a == "true":
        return True
    if INT.match(a):
        return int(re.sub(r"[uUlL]+$", "", a), 0) != 0
    return None


def is_proto_line(line, g):
    m = re.search(rf"\b{re.escape(g)}\b", line)
    if not m or not line[m.end():].lstrip().startswith("("):
        return False
    prefix = line[:m.start()].strip()
    return bool(prefix) and re.fullmatch(r"[A-Za-z_][\w\s\*]*", prefix) is not None and \
        not re.search(r"\b(return|if|while|else|case|do|goto|sizeof)\b", prefix)


class Dead:
    def __init__(self, fns, blobs, rev, local_only=False):
        self.blobs, self.rev, self.local = blobs, rev, local_only
        self.defs = defaultdict(list)
        for f in fns:
            self.defs[f.func].append(f)
        self.calls = defaultdict(list)
        for f in fns:
            for s in f.sites:
                if s["name"] in self.defs:
                    self.calls[s["name"]].append((f, s))
        self.memo, self.icache, self.scache = {}, {}, {}
        self.reasons = {}

    def stripped(self, p):
        if p not in self.scache:
            self.scache[p] = C.strip(self.blobs[p])
        return self.scache[p]

    def is_static_c(self, g):
        f = self.defs[g][0]
        return f.fname.endswith(".c") and re.search(rf"(^|\n)[ \t]*static\b[^;{{}}()]*\b{re.escape(g)}\s*\(",
                                                     self.stripped(f.fname)) is not None

    def info(self, g):
        """criteria 二.3: (unknown, exported, number of call occurrences in scanned files)"""
        if g in self.icache:
            return self.icache[g]
        unknown, exported, ncalls = False, False, 0
        if self.local:
            files = list(self.blobs)
        elif self.is_static_c(g):
            files = [self.defs[g][0].fname]
        else:
            files = set()
            for ln in C.git("grep", "-n", "-w", g, self.rev).splitlines():
                parts = ln.split(":", 3)
                if len(parts) < 4:
                    continue
                path, text = parts[1], parts[3]
                if path in self.blobs:
                    files.add(path)
                elif "EXPORT_SYMBOL" in text:
                    exported = True
                elif not is_proto_line(text, g):
                    unknown = True          # used outside the scanned files
            files = sorted(files)
        pat = re.compile(rf"\b{re.escape(g)}\b")
        for p in files:
            src = self.stripped(p)
            for m in pat.finditer(src):
                ls = src.rfind("\n", 0, m.start()) + 1
                line = src[ls:src.find("\n", m.end()) if src.find("\n", m.end()) >= 0 else len(src)]
                prevline = src[src.rfind("\n", 0, max(ls - 1, 0)) + 1:max(ls - 1, 0)]
                if line.lstrip().startswith("#") or prevline.rstrip().endswith("\\"):
                    unknown = True          # inside a macro
                    continue
                before = src[ls:m.start()].rstrip()
                after = src[m.end():].lstrip()
                if re.search(r"EXPORT_SYMBOL\w*\s*\($", before):
                    exported = True
                    continue
                if not after.startswith("("):
                    unknown = True          # address taken
                    continue
                pw = re.search(r"([A-Za-z_]\w*|\*)\s*$", before)
                if pw and pw.group(1) not in CALLWORDS and (pw.group(1) == "*" or re.match(r"[A-Za-z_]", pw.group(1))):
                    continue                # definition / prototype (type word right before the name)
                ncalls += 1
        self.icache[g] = (unknown, exported, ncalls)
        return self.icache[g]

    def dead_fn(self, h):
        """criteria 二.4: no use at all in the whole tree"""
        if len(self.defs.get(h, ())) != 1:
            return False
        unknown, exported, ncalls = self.info(h)
        return not unknown and not exported and ncalls == 0

    def values(self, g, i, stack=()):
        """criteria 二.2: set of truth values of parameter i of g, or None if unknown"""
        key = (g, i)
        if key in self.memo:
            return self.memo[key]
        if key in stack or len(self.defs.get(g, ())) != 1:
            return None
        unknown, exported, ncalls = self.info(g)
        sites = self.calls.get(g, [])
        res = set()
        if unknown or exported or len(sites) < ncalls:
            res = None
        else:
            for cf, s in sites:
                if self.dead_fn(cf.func):
                    continue
                a = s["args"][i] if i < len(s["args"]) else None
                v = lit_truth(a)
                if v is not None:
                    res.add(v)
                    continue
                if a in cf.params:
                    r = self.values(cf.func, cf.params.index(a), stack + (key,))
                    if r is None:
                        res = None
                        break
                    res |= r
                    continue
                res = None
                break
        self.memo[key] = res
        return res

    def dead_branch(self, f, s):
        for (P, pol, c) in s["facts"]:
            if P == K.NONNULL and c in f.params:
                v = self.values(f.func, f.params.index(c))
                if v and all(x != pol for x in v):
                    self.reasons[(f.fname, s["line"], s["name"])] = {"param": c, "needs": pol, "values": sorted(v)}
                    return True
        return False


def candidates(fns, names, dead):
    rows = []
    for f in fns:
        for s in f.sites:
            if s["name"] not in names or not s["canons"] or not s["canons"][0]:
                continue
            origin, old = S.classify(f, s)
            flt = "F7" if old is None and dead.dead_branch(f, s) else old
            rows.append({"file": f.fname, "func": f.func, "line": s["line"], "A": s["name"], "origin": origin,
                         "canon": s["canons"][0], "filtered": flt, "old": old,
                         "why_F7": dead.reasons.get((f.fname, s["line"], s["name"]))})
    return rows


def head():
    blobs = R.blobs_of(R.HEAD)
    fns = S.analyze_all(blobs)
    rows = candidates(fns, R.RESTR, Dead(fns, blobs, R.HEAD))
    kept = R.rank(rows)
    old_kept = R.rank([dict(r, filtered=r["old"]) for r in rows])
    key = lambda r: (r["file"], r["line"], r["A"])  # noqa: E731
    old_pos = {key(r): i for i, r in enumerate(old_kept, 1)}
    pos = {b: next((i for i, r in enumerate(kept, 1) if (r["file"], r["line"]) == fl), None)
           for b, fl in (("B-1", ("fs/proc/task_mmu.c", 1129)), ("B-2", ("include/linux/pgtable.h", 534)),
                         ("B-2026-11-16-1", ("mm/memory.c", 2494)))}
    changes = [dict(r, old_rank=old_pos.get(key(r))) for r in rows if r["old"] != r["filtered"]]
    res = {"sites": len(rows), "filtered": dict(Counter(r["filtered"] for r in rows)), "kept": len(kept), "kept_old": len(old_kept),
           "ranks": pos, "ranked": [dict(r, old_rank=old_pos.get(key(r))) for r in kept]}
    (HERE / "head.json").write_text(json.dumps(res, indent=1))
    (HERE / "changes.json").write_text(json.dumps(changes, indent=1))
    print("sites", len(rows), "filtered", res["filtered"], "kept", len(kept), "(old", len(old_kept), ") ranks", pos)
    print("F7", len(changes))
    for c in changes:
        print("  ", c["old_rank"], c["file"], c["line"], c["func"], c["A"], c["why_F7"])


def recall():
    ho = json.loads((CT / "p1check_20261115/heldout_score.json").read_text())
    dev = json.loads((CT / "p1check_20261115/dev.json").read_text())
    ex = json.loads((CT / "p1check_20261115/extra_p1_codex.json").read_text())
    samples = []
    for r in ho["rows"]:
        if r["hit"]:
            samples.append((r["commit"], [(h["file"], h["funcs_parent"], h["accessors"]) for h in r["hunks"] if h["hit"]]))
    for c, rows in dev.items():
        samples.append((c, [(h["file"], h["funcs_parent"], h["accessors"]) for h in rows if h["hit"]]))
    for c, rows in ex.items():
        if any(h["hit"] for h in rows):
            samples.append((c, [(h["file"], h["funcs"], h["accessors"]) for h in rows if h["hit"]]))
    out = []
    for c, hs in samples:
        extra = tuple(sorted({f.rsplit("/", 1)[0] + "/" for f, _, _ in hs if f.endswith(".c") and not K.in_scope(f)}))
        rev = f"{c}^"
        blobs = R.blobs_of(rev, extra)
        fns = S.analyze_all(blobs)
        rows = candidates(fns, R.RESTR | R.OLD_NAMES, Dead(fns, blobs, rev))
        match = [r for r in rows if any(r["file"] == f and r["func"] in funcs and r["A"] in accs for f, funcs, accs in hs)]
        kept = [r for r in match if r["filtered"] is None]
        out.append({"commit": c, "kept": bool(kept), "kept_old": any(r["old"] is None for r in match), "matched": len(match),
                    "reasons": sorted({r["filtered"] for r in match if r["filtered"]}),
                    "sites": [(r["func"], r["line"], r["A"], r["filtered"], r["old"]) for r in match][:8]})
        print(c, "kept" if kept else "LOST", len(match), out[-1]["reasons"], flush=True)
    n = sum(o["kept"] for o in out)
    (HERE / "recall.json").write_text(json.dumps({"n": len(out), "kept": n, "kept_old": sum(o["kept_old"] for o in out),
                                                  "rows": out}, indent=1))
    print("recall", n, "/", len(out))


def selftest():
    ok_prev = RG.selftest()   # 32 cases
    names = {"pte_pfn"}
    src = {"mm/e.c": "\n".join([
        "static void ip(pte_t *p, bool mk){ pte_t e = ptep_get(p); if (!pte_none(e)) { if (mk) { x = pte_pfn(e); } } }",
        "void a1(pte_t *p){ ip(p, false); }",
        "static void mid(pte_t *p, bool mk){ ip(p, mk); }",
        "void a2(pte_t *p){ mid(p, false); a1(p); }",
        "static void deadcaller(pte_t *p){ mid(p, true); }",
        "static void ip2(pte_t *p, bool mk){ pte_t e = ptep_get(p); if (mk) x = pte_pfn(e); }",
        "void b1(pte_t *p){ ip2(p, false); }",
        "void b2(pte_t *p){ ip2(p, true); b1(p); }",
        "static void ip3(pte_t *p, bool mk){ pte_t e = ptep_get(p); if (mk) x = pte_pfn(e); }",
        "void c1(pte_t *p, int k){ ip3(p, k > 2); }",
        "static void ip4(pte_t *p, bool mk){ pte_t e = ptep_get(p); if (!mk) return; x = pte_pfn(e); }",
        "void d1(pte_t *p){ ip4(p, false); }",
        "static void ip5(pte_t *p, bool mk){ pte_t e = ptep_get(p); if (mk) x = pte_pfn(e); }",
        "void e1(pte_t *p){ ip5(p, false); }",
        "static void (*fp)(pte_t *, bool) = ip5;",
        "void user(pte_t *p){ a2(p); b2(p); c1(p, 3); d1(p); e1(p); }"])}
    fns = S.analyze_all(src)
    rows = candidates(fns, names, Dead(fns, src, None, local_only=True))
    got = {(r["func"], r["A"]): r["filtered"] for r in rows}
    want = {("ip", "pte_pfn"): "F7", ("ip2", "pte_pfn"): None, ("ip3", "pte_pfn"): None, ("ip4", "pte_pfn"): "F7",
            ("ip5", "pte_pfn"): None}
    bad = 0
    for k, w in want.items():
        ok = got.get(k, "missing") == w
        bad += not ok
        print("ok " if ok else "BAD", k, got.get(k, "missing"), "want", w)
    S.SUMS.clear()
    print("selftest(dead)", "PASS" if not bad and ok_prev else f"FAIL {bad} prev={ok_prev}")
    return bad == 0 and ok_prev


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    cmd = sys.argv[1]
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    if not selftest():
        sys.exit(1)
    {"head": head, "recall": recall}[cmd]()
