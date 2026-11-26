"""layerbound criteria 三.2-三.4 + 四: layer labels, boundary edges, gates G1 (functions) / G2 / G3. WSL.

    python3 layer.py            -> /root/work/layerbound/{funcs,edges}.json.gz ; here: result.json, g1_funcs.json, g2.json, g3.json
"""
import gzip
import json
import os
import pickle
import re
import sys
import zlib
from collections import Counter, defaultdict
from pathlib import Path

SRC = Path("/root/repos/linux")
W = Path("/root/work/layerbound")
HERE = Path(__file__).resolve().parent
BUILDS = ("riscv", "arm64", "x86_64")
KEYWORDS = set("""if for while switch return sizeof typeof __typeof__ __typeof do else case goto break continue defined
__attribute__ __attribute asm __asm__ __asm volatile __volatile__ _Static_assert static_assert __builtin_expect
__builtin_constant_p __builtin_choose_expr __builtin_types_compatible_p _Generic alignof __alignof__ offsetof""".split())
PREDEF = {"__riscv", "__riscv_xlen", "__aarch64__", "__arm__", "__x86_64__", "__i386__", "__powerpc__", "__powerpc64__", "__mips__",
          "__s390__", "__s390x__", "__loongarch__", "__sparc__", "__hexagon__", "__LP64__", "__ILP32__", "__BIG_ENDIAN__",
          "__LITTLE_ENDIAN__", "__CHECKER__"}
IDENT = re.compile(r"[A-Za-z_]\w*")
SEP = re.compile(r"^arch/[^/]+/boot/|^arch/[^/]+/purgatory/|^arch/x86/realmode/|^drivers/firmware/efi/libstub/|/vdso")   # amendment 3.2
DIRECTIVE = re.compile(r"^\s*#\s*(if|ifdef|ifndef|elif|else|endif|define)\b(.*)$")


# ---------------------------------------------------------------- raw source parsing
def strip_code(text):
    """blank out comments, string and char literals (keep newlines), so line numbers stay"""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append(re.sub(r"[^\n]", " ", text[i:j]))
            i = j
        elif c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
        elif c in "\"'":
            j = i + 1
            while j < n and text[j] != c and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            j = min(j + 1, n)
            out.append(c + re.sub(r"[^\n]", " ", text[i + 1:j - 1]) + (c if j <= n else ""))
            i = j
        else:
            out.append(c)
            i += 1
    return "".join(out)


def logical_lines(lines):
    """yield (first_line_no, last_line_no, joined) for backslash-continued lines"""
    i = 0
    while i < len(lines):
        j, buf = i, lines[i]
        while buf.endswith("\\") and j + 1 < len(lines):
            j += 1
            buf = buf[:-1] + " " + lines[j]
        yield i + 1, j + 1, buf
        i = j + 1


def parse_file(path):
    text = strip_code(Path(path).read_text(errors="replace"))
    lines = text.split("\n")
    groups, stack, defines, pp_lines = [], [], [], set()
    for a, b, s in logical_lines(lines):
        m = DIRECTIVE.match(s)
        if not m:
            continue
        pp_lines.update(range(a, b + 1))
        kind, rest = m.group(1), m.group(2)
        if kind == "define":
            mm = re.match(r"\s*([A-Za-z_]\w*)(\()?", rest)
            if mm:
                defines.append({"name": mm.group(1), "fn": bool(mm.group(2)), "start": a, "end": b})
            continue
        if kind in ("if", "ifdef", "ifndef"):
            g = {"start": a, "cond": rest.strip(), "kind": kind, "ids": set(IDENT.findall(rest)), "chain": []}
            stack.append([g])
            groups.append(g)
        elif kind in ("elif", "else"):
            if not stack:
                continue
            prev = stack[-1][-1]
            prev["end"] = a - 1
            ids = set().union(*[x["ids"] for x in stack[-1]]) | set(IDENT.findall(rest))
            g = {"start": a, "cond": rest.strip(), "kind": kind, "ids": ids}
            stack[-1].append(g)
            groups.append(g)
        elif kind == "endif":
            if not stack:
                continue
            stack[-1][-1]["end"] = a - 1
            stack.pop()
    for g in groups:
        g.setdefault("end", len(lines))
        g.pop("chain", None)
    funcs = find_funcs(lines, pp_lines)
    return groups, funcs, defines, lines


TOK = re.compile(r"[A-Za-z_]\w*|\S")


def find_funcs(lines, pp_lines):
    toks = []
    for no, l in enumerate(lines, 1):
        if no in pp_lines:
            continue
        for m in TOK.finditer(l):
            toks.append((m.group(0), no))
    out, depth, i, n = [], 0, 0, len(toks)
    start_tok = None
    while i < n:
        t = toks[i][0]
        if t == "{":
            if depth == 0:
                name = func_name(toks, i)
                start_tok = (name, toks[i][1], i) if name else None
            depth += 1
        elif t == "}":
            depth = max(0, depth - 1)
            if depth == 0 and start_tok:
                name, _, k = start_tok
                hdr = name[1]
                out.append({"name": name[0], "start": hdr, "end": toks[i][1], "static": name[2]})
                start_tok = None
        i += 1
    return out


ANNOT = re.compile(r"^__\w+$|^(?:noinline|notrace|asmlinkage|visible)$")


def func_name(toks, i):
    """toks[i] is a '{' at depth 0: return ((name, line)) if it opens a function body"""
    j = i - 1
    while j >= 0:
        t = toks[j][0]
        if t == ")":
            d, k = 0, j
            while k >= 0:
                if toks[k][0] == ")":
                    d += 1
                elif toks[k][0] == "(":
                    d -= 1
                    if d == 0:
                        break
                k -= 1
            if k <= 0:
                return None
            nm = toks[k - 1][0]
            if not IDENT.fullmatch(nm) or nm in KEYWORDS:
                return None
            if ANNOT.match(nm) and k - 2 >= 0 and toks[k - 2][0] == ")":
                j = k - 2                                     # trailing annotation like __acquires(x): keep walking back
                continue
            # reject initializers / declarations: '=' right before the declarator start is an initializer
            m = k - 2                                       # amendment 3: storage class of the definition
            while m >= 0 and toks[m][0] not in (";", "}", "{"):
                m -= 1
            st = any(toks[q][0] == "static" for q in range(m + 1, k - 1))
            return (nm, toks[k - 1][1], st)
        if IDENT.fullmatch(t) and (ANNOT.match(t) or t in ("const",)):
            j -= 1
            continue
        return None
    return None


# ---------------------------------------------------------------- build data
def load_lines(b):
    with gzip.open(W / f"lines_{b}.pkl.gz", "rb") as fh:
        d = pickle.load(fh)
    return {p: zlib.decompress(x) for p, x in d["files"].items() if not p.startswith("gen:")}, d


def active(bm, ln):
    return bm is not None and ln < len(bm) and bm[ln] == 1


def any_active(bm, a, b):
    if bm is None:
        return False
    return 1 in bm[a:min(b + 1, len(bm))]


def arch_macros():
    names = set()
    for root, _, fs in os.walk(SRC / "arch"):
        for f in fs:
            if f.endswith((".h", ".c")):
                try:
                    for l in open(os.path.join(root, f), errors="replace"):
                        m = re.match(r"\s*#\s*define\s+([A-Za-z_]\w*)", l)
                        if m:
                            names.add(m.group(1))
                except OSError:
                    pass
    return names


def makefile_cond(path):
    """common .c file: CONFIG symbols on the obj-$(CONFIG_X) line naming it in its directory's Makefile/Kbuild"""
    d, base = os.path.dirname(path), os.path.basename(path)[:-2] + ".o"
    out = set()
    for mk in ("Makefile", "Kbuild"):
        p = SRC / d / mk
        if p.exists():
            txt = p.read_text(errors="replace").replace("\\\n", " ")
            for l in txt.split("\n"):
                if re.search(r"(^|\s)" + re.escape(base) + r"(\s|$)", l):
                    out |= set(re.findall(r"CONFIG_(\w+)", l))
    return out


def classify_ids(ids, cfg_arch, cfg_common, amac):
    kinds = set()
    for x in ids:
        if x.startswith("CONFIG_"):
            s = x[7:]
            if s.endswith("_MODULE"):
                s = s[:-7]
            if s in cfg_arch:
                kinds.add("arch")
            elif s in cfg_common:
                kinds.add("config")
        elif x in PREDEF or x in amac:
            kinds.add("arch")
    return kinds


def main():
    cfg = json.load(open(W / "config_symbols.json"))
    cfg_arch, cfg_common = set(cfg["arch_related"]), set(cfg["common"])
    amac = arch_macros() - {"defined"}
    L = {}
    INCL = {}
    mk_cache = {}

    def unit_kind(u):                                   # amendment 1.2: attribution of one including unit
        if u.startswith("arch/"):
            return "arch"
        if u not in mk_cache:
            k = classify_ids({"CONFIG_" + x for x in makefile_cond(u)}, cfg_arch, cfg_common, amac)
            mk_cache[u] = "arch" if "arch" in k else ("config" if "config" in k else "unattr")
        return mk_cache[u]
    for b in BUILDS:
        L[b], meta = load_lines(b)
        INCL[b] = meta.get("includers", {})
        print("loaded", b, "files", len(L[b]), "units", meta["units"], "failed", len(meta["failed"]), flush=True)
    files = sorted(set().union(*[set(L[b]) for b in BUILDS]))
    files = [f for f in files if f.endswith((".c", ".h")) and (SRC / f).exists() and not SEP.search(f)]   # amendment 3.2
    print("source files", len(files), flush=True)

    entries = []          # functions and function-like macros
    reasons = Counter()
    for fi, f in enumerate(files):
        try:
            groups, funcs, defines, lines = parse_file(SRC / f)
        except Exception as ex:                       # noqa: BLE001
            reasons["parse-error"] += 1
            continue
        in_arch = f.startswith("arch/")
        P = [b for b in BUILDS if f in L[b]]
        taken = []
        for g in groups:
            st = {b: any_active(L[b][f], g["start"] + 1, g["end"]) for b in P}
            known = any(st.values())
            taken.append(st if known else None)
        mk = makefile_cond(f) if (f.endswith(".c") and not in_arch and len(P) < len(BUILDS)) else set()
        items = [dict(x, kind="func") for x in funcs] + [dict(x, kind="macro") for x in defines if x["fn"]]
        for it in items:
            hdr = it["start"]
            comp = {b: active(L[b][f], hdr) for b in P}
            cb = [b for b in P if comp[b]]
            diffs = []
            if len(P) < len(BUILDS) and cb:
                if in_arch:
                    diffs.append(("file", "arch"))
                elif f.endswith(".c"):
                    k = classify_ids({"CONFIG_" + s for s in mk}, cfg_arch, cfg_common, amac)
                    diffs.append(("file", "arch" if "arch" in k else ("config" if "config" in k else "unattr")))
                else:                                       # amendment 1.2: header, by its including units
                    ks = {unit_kind(u) for b2 in P for u in INCL[b2].get(f, ())}
                    hk = "arch" if ks == {"arch"} else ("config" if "config" in ks and "arch" not in ks else "unattr")
                    diffs.append(("file", hk))
            for g, st in zip(groups, taken):
                if st is None:
                    continue
                if g["start"] <= hdr <= g["end"]:            # encloses the definition: compiled status
                    vals = {st[b] for b in P}
                elif g["start"] <= it["end"] and g["end"] >= hdr and cb:   # inside the body
                    vals = {st[b] for b in cb}
                else:
                    continue
                if len(vals) > 1:
                    k = classify_ids(g["ids"], cfg_arch, cfg_common, amac)
                    diffs.append(("cond:" + g["cond"][:80], "arch" if "arch" in k else ("config" if "config" in k else "unattr")))
            if not cb:
                label = "未编入"
            elif in_arch:
                label = "架构层A0"
            elif any(d[1] == "arch" for d in diffs):
                label = "架构层A1"
            elif not diffs:
                label = "公共层"
            elif all(d[1] == "config" for d in diffs):
                label = "公共层-配置差异"
            else:
                label = "未归因"
            if it["kind"] == "macro" and label in ("公共层", "公共层-配置差异", "未归因"):
                label = "公共宏"                              # criteria 三.2: only arch-side function-like macros count as functions
            entries.append({"file": f, "name": it["name"], "kind": it["kind"], "start": hdr, "end": it["end"], "label": label,
                            "static": it.get("static", False),
                            "builds": cb, "diffs": diffs[:6]})
        if fi % 2000 == 0:
            print("parsed", fi, "/", len(files), "entries", len(entries), flush=True)

    # ---------------------------------------------------------------- boundary edges
    ARCH = ("架构层A0", "架构层A1")
    COMMON = ("公共层", "公共层-配置差异")
    idx = {b: defaultdict(list) for b in BUILDS}
    for k, e in enumerate(entries):
        for b in e["builds"]:
            idx[b][e["name"]].append(k)
    src_cache = {}
    mbody = {}
    INCS = {b: {h: set(us) for h, us in INCL[b].items()} for b in BUILDS}

    def units_of(f, b):                                  # amendment 3.1
        return {f} if f.endswith(".c") else INCS[b].get(f, set())

    def visible(c, f, b, U):
        e = entries[c]
        g = e["file"]
        if g == f:
            return True
        if g.endswith(".h"):
            return not U.isdisjoint(INCS[b].get(g, ()))
        return e["kind"] == "func" and not e["static"]

    def macro_calls(c):                                  # amendment 1.3: names called inside a function-like macro body
        if c not in mbody:
            e = entries[c]
            txt = strip_code((SRC / e["file"]).read_text(errors="replace")).split("\n")[e["start"] - 1:e["end"]]
            body = " ".join(x.rstrip("\\") for x in txt)
            body = re.sub(r"^\s*#\s*define\s+\w+\s*\([^)]*\)", " ", body)
            tk = TOK.findall(body)
            mbody[c] = {tk[i] for i in range(len(tk) - 1) if tk[i + 1] == "(" and IDENT.fullmatch(tk[i]) and tk[i] not in KEYWORDS}
        return mbody[c]

    def via_macros(t, b, f, U, depth=3, seen=None):
        seen = seen if seen is not None else set()
        out = set()
        for c in idx[b].get(t, []):
            if not visible(c, f, b, U):
                continue
            e = entries[c]
            if e["kind"] != "macro" or e["label"] != "公共宏" or c in seen:
                continue
            seen.add(c)
            for t2 in macro_calls(c):
                for c2 in idx[b].get(t2, []):
                    if entries[c2]["label"] in ARCH and visible(c2, f, b, U):
                        out.add(c2)
                if depth > 1:
                    out |= via_macros(t2, b, f, U, depth - 1, seen)
        return out
    medges = set()
    edges = set()
    calls_of = defaultdict(set)                                 # entry -> called names (any layer), for the one-hop measure
    collide = Counter()
    for k, e in enumerate(entries):
        if e["kind"] != "func" or e["label"] not in COMMON:
            continue
        f = e["file"]
        if f not in src_cache:
            src_cache.clear()
            src_cache[f] = strip_code((SRC / f).read_text(errors="replace")).split("\n")
        lines = src_cache[f]
        for b in e["builds"]:
            bm = L[b][f]
            U = units_of(f, b)
            body = " \n".join(lines[ln - 1] if active(bm, ln) else "" for ln in range(e["start"], e["end"] + 1))
            toks = TOK.findall(body)
            for i in range(len(toks) - 1):
                t = toks[i]
                if toks[i + 1] != "(" or not IDENT.fullmatch(t) or t in KEYWORDS or t == e["name"]:
                    continue
                calls_of[k].add(t)
                cand = [c for c in idx[b].get(t, []) if visible(c, f, b, U)]
                archc = [c for c in cand if entries[c]["label"] in ARCH]
                if archc:
                    if len(archc) < len(cand):
                        collide[b] += 1
                    for c in archc:
                        edges.add((k, c, b))
                else:
                    for c in via_macros(t, b, f, U):
                        medges.add((k, c, b))
    d_type1 = {k for k, _, _ in edges}
    d_type2 = {c for _, c, _ in edges}
    alle = edges | medges
    type1 = {k for k, _, _ in alle}
    type2 = {c for _, c, _ in alle}
    print("direct edges", len(edges), "type1", len(d_type1), "type2", len(d_type2), "| with macro", len(alle), "type1", len(type1),
          "type2", len(type2), flush=True)

    with gzip.open(W / "funcs.json.gz", "wt") as fh:
        json.dump(entries, fh)
    with gzip.open(W / "edges.json.gz", "wt") as fh:
        json.dump({"direct": sorted(edges), "macro": sorted(medges - edges)}, fh)

    # ---------------------------------------------------------------- G3
    lab = Counter(e["label"] for e in entries)
    perb = {}
    for b in BUILDS:
        eb = [(k, c) for k, c, bb in edges if bb == b]
        perb[b] = {"edges": len(eb), "type1": len({k for k, _ in eb}), "type2": len({c for _, c in eb}),
                   "common_funcs": sum(1 for e in entries if e["kind"] == "func" and e["label"] in COMMON and b in e["builds"]),
                   "arch_entries": sum(1 for e in entries if e["label"] in ARCH and b in e["builds"]),
                   "name_collisions": collide[b]}
    why = Counter(d[1] for e in entries for d in e["diffs"])
    g3 = {"labels": dict(lab), "per_build": perb, "union_direct": {"edges": len(edges), "type1": len(d_type1), "type2": len(d_type2)},
          "union_with_macro": {"edges": len(alle), "type1": len(type1), "type2": len(type2)},
          "diff_attribution": dict(why), "parse_errors": reasons["parse-error"], "files": len(files)}
    json.dump(g3, open(HERE / "g3.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(g3, ensure_ascii=False, indent=1))

    # ---------------------------------------------------------------- G1 functions
    def find(f, name, kind=None):
        return [k for k, e in enumerate(entries) if e["file"] == f and e["name"] == name and (kind is None or e["kind"] == kind)]
    g1 = [("arch/riscv/mm/pgtable.c", "pudp_invalidate", {"架构层A0"}),
          ("arch/x86/kernel/amd_nb.c", "amd_get_mmconfig_range", {"架构层A0"}),
          ("include/linux/pgtable.h", "ptep_get", {"架构层A1"}),
          ("mm/huge_memory.c", "change_huge_pud", {"架构层A1"}),
          ("mm/mprotect.c", "change_pud_range", {"公共层"}),
          ("mm/memory.c", "zap_pud_range", {"公共层"}),
          ("mm/memory.c", "insert_page_into_pte_locked", {"公共层"}),
          ("fs/proc/task_mmu.c", "smaps_pmd_entry", {"公共层", "公共层-配置差异"})]
    res1, ok1 = [], 0
    for f, n, want in g1:
        ks = find(f, n, "func")
        got = [entries[k]["label"] for k in ks]
        good = bool(got) and all(x in want for x in got)
        ok1 += good
        res1.append({"file": f, "name": n, "want": sorted(want), "got": got, "ok": good, "diffs": [entries[k]["diffs"] for k in ks]})
        print("G1", "OK " if good else "BAD", f, n, got, [entries[k]["diffs"] for k in ks][:1])
    print("G1 functions", ok1, "/", len(g1))
    json.dump(res1, open(HERE / "g1_funcs.json", "w"), ensure_ascii=False, indent=1)

    # ---------------------------------------------------------------- G2
    bnd_names = {entries[k]["name"] for k in type1 | type2}
    g2 = [("K1", "fs/proc/task_mmu.c", "smaps_pmd_entry"), ("K2", "mm/rmap.c", "folio_referenced_one"),
          ("K3", "mm/memory.c", "insert_page_into_pte_locked"), ("K4", "mm/vmscan.c", "lru_gen_look_around"),
          ("K5", "mm/shmem.c", "shmem_allowable_huge_orders"), ("K6", "arch/x86/kernel/amd_nb.c", "amd_get_mmconfig_range"),
          ("K7", "arch/riscv/include/asm/pgtable-64.h", "pud_leaf"), ("D1", "arch/x86/include/asm/pgtable.h", "pud_leaf"),
          ("D2", "arch/riscv/include/asm/pgtable.h", "pte_leaf_size"), ("D3", "arch/arm64/include/asm/pgtable.h", "pmd_leaf|pud_leaf"),
          ("D4", "arch/riscv/include/asm/pgtable.h", "PAGE_PROT_NONE"), ("D5", "arch/arm64/include/asm/pgtable.h", "pte_wrprotect")]
    res2, strict, hop, evaluable = [], 0, 0, 0
    for tag, f, names in g2:
        ks = [k for n in names.split("|") for k in find(f, n)]
        comp = [k for k in ks if entries[k]["builds"]]
        ev = bool(comp) or tag == "D4"                # D4 is an object-like macro: evaluable, cannot be a boundary function
        s = any(k in type1 or k in type2 for k in comp)
        sd = any(k in d_type1 or k in d_type2 for k in comp)
        h = s or any(any(nm in bnd_names for nm in calls_of.get(k, ())) for k in comp)
        evaluable += ev
        strict += s and ev
        hop += h and ev
        res2.append({"id": tag, "file": f, "name": names, "found": len(ks), "compiled": len(comp), "evaluable": ev,
                     "labels": [entries[k]["label"] for k in ks], "type1": any(k in type1 for k in comp),
                     "type2": any(k in type2 for k in comp), "strict": s, "strict_direct_only": sd, "one_hop": h})
        print("G2", tag, f, names, "evaluable" if ev else "NOT evaluable", "strict" if s else "-", "hop" if h else "-",
              [entries[k]["label"] for k in ks])
    print(f"G2 strict {strict}/{evaluable}  one-hop {hop}/{evaluable}")
    json.dump({"items": res2, "strict": strict, "one_hop": hop, "evaluable": evaluable}, open(HERE / "g2.json", "w"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
