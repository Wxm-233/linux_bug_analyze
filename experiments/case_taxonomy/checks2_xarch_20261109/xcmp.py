"""Cross-architecture implementation comparison, check 2 first version (criteria.md section 3).

    python3 xcmp.py reduce <facts.json> <out.json.gz>
        keep only the fields the comparison needs; refuse if any unit failed to parse (criteria section 2)
    python3 xcmp.py compare --target R.json.gz --counter x86=X.json.gz --counter arm64=A.json.gz \
                            --pool P1.json --pool P2.json ... --out flags.json

Target = riscv. Flags are only raised where the counterpart has the behaviour and the target lacks it.
"""
import argparse
import gzip
import json
import re
import sys
from collections import defaultdict, deque

DEPTH = 3
FLAG_TYPES = ("stub", "write-missing", "call-missing", "arg-diff", "errno-diff", "param-check")


# ------------------------------------------------------------------ reduce
def reduce_facts(src, dst):
    with open(src, encoding="utf-8") as fh:
        f = json.load(fh)
    bad = [u for u in f.get("units", []) if u["status"] != 0]
    if not f.get("units"):
        raise SystemExit(f"{src}: no unit status recorded")
    if bad:  # criteria section 2: any unit that failed to parse stops the analysis
        raise SystemExit(f"{src}: {len(bad)} of {len(f['units'])} units failed to parse, e.g. {bad[:3]}")
    defs = [{"name": d["name"], "file": d["file"], "line": d["line"], "static": d["static"],
             "bodyKind": d["bodyKind"], "writes": d["writes"], "checked": d["checked"],
             "danger": sorted({u["param"] + ":" + u["kind"] for u in d["dangerUses"]}),
             "retConsts": d.get("retConsts", []), "retNonConst": d.get("retNonConst", False)} for d in f["defs"]]
    calls = [{"cf": c["callerFile"], "cl": c["callerLine"], "callee": c["calleeName"],
              "argConsts": c.get("argConsts", [])} for c in f["calls"]]
    out = {"arch": f["arch"], "units": len(f["units"]), "defs": defs, "calls": calls}
    with gzip.open(dst, "wt", encoding="utf-8") as fh:
        json.dump(out, fh)
    print(f"{src}: units={len(f['units'])} defs={len(defs)} calls={len(calls)} -> {dst}")


def load(path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------------------------------------------ per-build index
def is_global_key(k):
    return "p#" not in k  # "struct.field", "g:name" (possibly with * or [] around); parameter keys contain "p#"


def in_arch(path):
    return path.startswith("arch/")


class Build:
    def __init__(self, facts):
        self.arch = facts["arch"]
        self.by_name = defaultdict(list)
        for d in facts["defs"]:
            self.by_name[d["name"]].append(d)
        self.callees = defaultdict(list)  # (file, line) of the enclosing definition -> calls
        for c in facts["calls"]:
            self.callees[(c["cf"], c["cl"])].append(c)

    def impls(self, name):
        """criteria 3.1: non-static definitions, and static definitions in .h files"""
        return [d for d in self.by_name.get(name, []) if not d["static"] or d["file"].endswith(".h")]

    def calls_of(self, defs):
        return [c for d in defs for c in self.callees.get((d["file"], d["line"]), [])]

    def pure_common(self, name):
        ds = self.by_name.get(name)
        return bool(ds) and not any(in_arch(d["file"]) for d in ds)

    def derive(self, defs):
        """criteria 3.2 for one (merged) implementation"""
        kinds = {("normal" if d["bodyKind"] == "void" else d["bodyKind"]) for d in defs}
        form = "normal" if "normal" in kinds else ("const" if "const" in kinds else "empty")
        wd = {k for d in defs for k in d["writes"]}
        # transitive callees (names), up to DEPTH hops, resolved by name in this build
        reach, frontier, seen_defs = set(), list(defs), {(d["file"], d["line"]) for d in defs}
        for _ in range(DEPTH):
            nxt = []
            for c in self.calls_of(frontier):
                reach.add(c["callee"])
                for cd in self.by_name.get(c["callee"], []):
                    if (cd["file"], cd["line"]) not in seen_defs:
                        seen_defs.add((cd["file"], cd["line"]))
                        nxt.append(cd)
            frontier = nxt
        wt = set(wd)
        for name in reach:
            for cd in self.by_name.get(name, []):
                wt |= {k for k in cd["writes"] if is_global_key(k)}
        direct = self.calls_of(defs)
        cd_common = {c["callee"] for c in direct if self.pure_common(c["callee"])}
        args = defaultdict(lambda: defaultdict(set))
        for c in direct:
            if c["callee"] in cd_common:
                for i, v in enumerate(c["argConsts"]):
                    if v != "":
                        args[c["callee"]][i].add(v)
        errnos = {v for d in defs for v in d["retConsts"] if v.startswith("-")}
        danger = {u for d in defs for u in d["danger"]}
        checked = {p for d in defs for p in d["checked"]}
        return {"form": form, "wd": wd, "wt": wt, "ct": reach, "cd": cd_common, "args": args, "errno": errnos,
                "danger": danger, "checked": checked, "locs": sorted({f"{d['file']}:{d['line']}" for d in defs})}

    def writes_anything(self, name):
        return any(d["writes"] for d in self.by_name.get(name, []))


# ------------------------------------------------------------------ comparison
def compare_family(name, R, X, xb):
    """criteria 3.3: flags where counterpart X has the behaviour and target R lacks it"""
    out = []
    add = lambda t, detail: out.append((t, name, detail))
    if R["form"] in ("empty", "const") and X["form"] == "normal":
        add("stub", R["form"])
    for k in sorted(X["wd"] - R["wt"]):
        add("write-missing", k)
    for f in sorted(X["cd"]):
        if xb.writes_anything(f) and f not in R["ct"]:
            add("call-missing", f)
    for f in sorted(R["cd"] & X["cd"]):
        for i in sorted(set(R["args"][f]) & set(X["args"][f])):
            if not (R["args"][f][i] & X["args"][f][i]):
                add("arg-diff", f"{f}#{i}:{sorted(R['args'][f][i])}vs{sorted(X['args'][f][i])}")
    if R["errno"] and X["errno"] and (X["errno"] - R["errno"]):
        add("errno-diff", ",".join(sorted(X["errno"] - R["errno"])))
    for u in sorted(X["danger"]):
        p = u.split(":")[0]
        if p in X["checked"] and u in R["danger"] and p not in R["checked"]:
            add("param-check", u)
    return out


def candidates_from_pools(paths):
    funcs, macros = set(), set()
    for p in paths:
        for s in json.load(open(p, encoding="utf-8")):
            if s["direction"] == "public_to_arch":
                (funcs if s["kind"] == "function" else macros if s["kind"] == "macro" else set()).add(s["name"])
    return funcs, macros


def compare(target, counters, pools):
    rb = Build(target)
    cbs = {tag: Build(f) for tag, f in counters}
    cands, macro_providers = candidates_from_pools(pools)
    flags = defaultdict(lambda: {"counterparts": {}, "r_locs": None})
    n_rimpl = n_family = n_single = 0
    for name in sorted(cands):
        rdefs = rb.impls(name)
        xs = {tag: b.impls(name) for tag, b in cbs.items()}
        xs = {t: d for t, d in xs.items() if d}
        if not rdefs:
            continue  # counted as "riscv has no implementation"
        n_rimpl += 1
        if not xs:
            n_single += 1
            continue
        n_family += 1
        R = rb.derive(rdefs)
        for tag, xdefs in xs.items():
            X = cbs[tag].derive(xdefs)
            for key in compare_family(name, R, X, cbs[tag]):
                fl = flags[key]
                fl["counterparts"][tag] = X["locs"]
                fl["r_locs"] = R["locs"]
    out = [{"type": t, "family": n, "detail": d, "riscv": v["r_locs"], "counterparts": v["counterparts"]}
           for (t, n, d), v in sorted(flags.items())]
    summary = {
        "candidates": len(cands), "riscv_has_impl": n_rimpl, "families": n_family,
        "riscv_no_impl": len(cands) - n_rimpl, "riscv_only": n_single, "macro_providers_not_covered": len(macro_providers),
        "flags_by_counterpart": {tag: sum(1 for f in out if tag in f["counterparts"]) for tag in cbs},
        "distinct_flags": len(out), "by_type": {t: sum(1 for f in out if f["type"] == t) for t in FLAG_TYPES},
        "target_units": target["units"], "counter_units": {tag: f["units"] for tag, f in counters},
    }
    return out, summary


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("reduce")
    r.add_argument("src")
    r.add_argument("dst")
    c = sub.add_parser("compare")
    c.add_argument("--target", required=True)
    c.add_argument("--counter", action="append", required=True, help="tag=path")
    c.add_argument("--pool", action="append", required=True)
    c.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "reduce":
        reduce_facts(a.src, a.dst)
        return
    counters = [(s.split("=", 1)[0], load(s.split("=", 1)[1])) for s in a.counter]
    flags, summary = compare(load(a.target), counters, a.pool)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump({"summary": summary, "flags": flags}, fh, ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
