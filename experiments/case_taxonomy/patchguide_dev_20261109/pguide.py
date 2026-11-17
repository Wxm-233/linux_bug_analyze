"""Patch-guided detection: counterpart fix elements missing from riscv (criteria sections 3.3-3.5).

    (library) run(riscv_facts, riscv_repo, riscv_rev, counter_facts{arch: facts}, candidates, patches, cutoff) -> flags
"""
import re
import subprocess
from collections import defaultdict

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "checks2_xarch_20261109"))
import xcmp  # noqa: E402

DEPTH = 3
ASSIGN_AFTER = r"\s*(?:[|&^+\-]?=)(?!=)"


class Source:
    """function bodies of one tree revision, read through git (no checkout needed)"""

    def __init__(self, repo, rev):
        self.repo, self.rev, self.files = repo, rev, {}

    def file(self, path):
        if path not in self.files:
            r = subprocess.run(["git", "-C", self.repo, "show", f"{self.rev}:{path}"], capture_output=True, text=True,
                               errors="replace")
            self.files[path] = r.stdout.splitlines() if r.returncode == 0 else []
        return self.files[path]

    def body(self, path, line):
        """text from the definition line to the brace that closes the function body"""
        lines = self.file(path)
        if not lines or line < 1 or line > len(lines):
            return ""
        out, depth, opened = [], 0, False
        for text in lines[line - 1:line - 1 + 3000]:
            out.append(text)
            for ch in re.sub(r'"(?:\\.|[^"\\])*"', '""', text):
                if ch == "{":
                    depth, opened = depth + 1, True
                elif ch == "}":
                    depth -= 1
            if opened and depth <= 0:
                break
            if not opened and text.rstrip().endswith(";"):
                break  # a prototype, not a definition
        return "\n".join(out)


def closure_defs(build, defs, depth=DEPTH):
    """the definitions themselves plus those reachable through direct calls within depth hops"""
    seen = {(d["file"], d["line"]) for d in defs}
    out, frontier, names = list(defs), list(defs), set()
    for _ in range(depth):
        nxt = []
        for c in build.calls_of(frontier):
            names.add(c["callee"])
            for cd in build.by_name.get(c["callee"], []):
                k = (cd["file"], cd["line"])
                if k not in seen:
                    seen.add(k)
                    nxt.append(cd)
                    out.append(cd)
        frontier = nxt
    return out, names


def counter_reach(cb, arch, candidates, depth=DEPTH):
    """criteria 3.3 (2): h -> {candidate g : h in ReachX(g)}, ReachX = g's defs + arch/<X> functions within depth hops
    (depth is an iteration option; iteration 0 uses DEPTH)"""
    rev = defaultdict(set)
    for g in candidates:
        defs = cb.impls(g)
        if not defs:
            continue
        rev[g].add(g)
        allds, _ = closure_defs(cb, defs, depth)
        for d in allds:
            if d["file"].startswith(f"arch/{arch}/"):
                rev[d["name"]].add(g)
    return rev


class Target:
    def __init__(self, name, defs, rb, src):
        allds, calls = closure_defs(rb, defs)
        self.name = name
        self.calls = calls | {d["name"] for d in allds}
        self.writes = {k for d in allds for k in d["writes"]}
        self.text = "\n".join(src.body(d["file"], d["line"]) for d in allds)
        self.words = set(re.findall(r"[A-Za-z_]\w*", self.text))
        self.locs = sorted({f"{d['file']}:{d['line']}" for d in defs})

    def has(self, kind, e):
        if kind == "call":
            return e in self.calls or e in self.words
        if kind == "field":
            return (any(k.endswith("." + e) or k.endswith("->" + e) for k in self.writes)
                    or re.search(r"(?:\.|->)\s*" + re.escape(e) + ASSIGN_AFTER, self.text) is not None)
        return e in self.words  # errno


# iteration options (iteration 0 = all off); see iterations.md
DIAG_EXT = re.compile(r"WARN|BUG")
KEYWORDS_EXT = {"volatile", "__volatile__"}


def available_on_riscv(rb, kind, e, cache):
    """iteration 1: an element riscv could have at all -- a function defined or called somewhere in the riscv facts,
    a field written somewhere in the riscv facts; error codes always count"""
    if "names" not in cache:
        cache["names"] = set(rb.by_name) | {c["callee"] for cs in rb.callees.values() for c in cs}
        cache["fields"] = {re.split(r"\.|->", k)[-1] for ds in rb.by_name.values() for d in ds for k in d["writes"]}
    if kind == "call":
        return e in cache["names"]
    if kind == "field":
        return e in cache["fields"]
    return True


def run(riscv_facts, repo, rev, counter_facts, candidates, patches, cutoff=None, revmaps=None, opts=None):
    opts = opts or {}
    rb = xcmp.Build(riscv_facts)
    src = Source(repo, rev)
    avail_cache = {}
    if revmaps is None:  # (optional precomputed counter_reach, identical result; speed only)
        revmaps = {a: counter_reach(xcmp.Build(f), a, candidates) for a, f in counter_facts.items()}
    targets = {}

    def target(kind, name):
        key = (kind, name)
        if key not in targets:
            defs = rb.by_name.get(name, []) if kind == "name" else rb.impls(name)
            targets[key] = Target(name, defs, rb, src) if defs else None
        return targets[key]

    flags = defaultdict(lambda: {"evidence": [], "locs": None})
    used = 0
    for p in patches:
        if cutoff is not None and p["cdate"] >= cutoff:
            continue
        used += 1
        for h in p["hunks"]:
            if h["arch"] not in revmaps:
                continue
            ts = [target("name", h["func"])] + [target("iface", g) for g in sorted(revmaps[h["arch"]].get(h["func"], ()))]
            for t in {id(t): t for t in ts if t}.values():
                for kind, es in h["added"].items():
                    for e in es:
                        if opts.get("diag_ext") and (DIAG_EXT.search(e) or e in KEYWORDS_EXT):
                            continue
                        if opts.get("riscv_available") and not available_on_riscv(rb, kind, e, avail_cache):
                            continue
                        if not t.has(kind, e):
                            fl = flags[(t.name, kind, e)]
                            fl["locs"] = t.locs
                            ev = {"commit": p["commit"][:12], "arch": h["arch"], "func": h["func"], "subject": p["subject"]}
                            if ev not in fl["evidence"]:
                                fl["evidence"].append(ev)
    out = [{"target": n, "kind": k, "element": e, "riscv": v["locs"], "evidence": v["evidence"]}
           for (n, k, e), v in sorted(flags.items())]
    return out, {"patches_used": used, "targets_built": sum(1 for t in targets.values() if t), "distinct_flags": len(out)}


def reaches(rb, src_name, dst_names):
    """src_name == one of dst_names, or src's definitions reach one within DEPTH hops (riscv facts)"""
    if src_name in dst_names:
        return True
    _, names = closure_defs(rb, rb.by_name.get(src_name, []))
    return bool(names & set(dst_names))
