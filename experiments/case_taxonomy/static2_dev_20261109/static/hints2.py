"""Hint sites with switchable improvements I1-I4 (criteria 二、四). Runs anywhere (needs facts + values).

    python3 hints2.py <facts.json.gz> <values.json> <config> <out.json> [--group G]
        config: comma list of I1,I2,I3,I4 (and/or "fix"), or "base"; anything but "base" uses the fixed operator

With every switch off the decisions are those of ../../semhint_dev_20261109/static/hints.py (criteria 三 基线复现).
Output adds "reach_any" {function name: min depth} (calls followed without parameter mapping, criteria 4.1 可达)
and "reach_map" [function names reached with at least one mapped parameter], plus callback statistics.
"""
import gzip
import json
import re
import sys
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAMES = json.loads((HERE / "boundary_names.json").read_text())
KIND = NAMES["kind"]
BMAC = set(NAMES["macro"])
BNON = set(NAMES["nonmacro"])
BALL = BMAC | BNON
MASK = 2**64 - 1
ARCHS = ("riscv", "arm64", "x86_64")
ADDR_NAMES = {"addr", "start", "brk", "uaddr", "uaddr2", "new_addr", "old_addr", "start_addr", "addr_hint"}
ARCH_MAC_FILE = re.compile(r"(^|/)(arch/riscv/|include/asm-generic/)")
DRV = re.compile(r"^drivers/.*(riscv|sifive|-sbi)")


def width_of(ptype):
    t = ptype.replace("const ", "").strip()
    if t.endswith("*"):
        return 64
    if t in ("umode_t",):
        return 16
    if "long" in t or t in ("size_t", "ssize_t", "loff_t", "off_t", "aio_context_t", "u64", "__u64", "s64",
                            "cap_user_header_t", "cap_user_data_t"):
        return 64
    return 32


def signed(ptype):
    t = ptype.replace("const ", "").strip()
    return not (t.startswith("unsigned") or t.startswith("u") or t.startswith("__u") or t == "size_t"
                or t.endswith("*"))


def trunc(v, ptype):
    w = width_of(ptype)
    v &= (1 << w) - 1
    if signed(ptype) and v >> (w - 1):
        v -= 1 << w
    return v & MASK


def is_addr(pname, ptype):
    return ptype.strip().endswith("*") or (pname in ADDR_NAMES and width_of(ptype) == 64)


def run(d, vals, cfg):
    I1, I2, I3, I4 = ("I1" in cfg), ("I2" in cfg), ("I3" in cfg), ("I4" in cfg)
    OPFIX = bool(cfg)  # amendment 1: every configuration except "base" uses the libclang operator
    DEPTH = 8 if I4 else 4
    active = {"base"} | ({"drivers"} if I3 else set())
    F = {u: f for u, f in d["functions"].items() if active & set(f.get("unit_class", []))}
    md_all = d["macros"]

    def in_arch(path):
        return path.startswith("arch/") or bool(DRV.search(path))

    # I1: tree-own boundary symbols
    tree_mac, tree_fn = set(), set()
    if I1:
        used_outside = set()
        for f in F.values():
            if not in_arch(f["file"]):
                used_outside |= set(f["body"])
        for n, m in md_all.items():
            if m.get("file") and ARCH_MAC_FILE.search(m["file"]) and n in used_outside:
                tree_mac.add(n)
        for f in F.values():
            if (f["file"].startswith("arch/riscv/") or (I3 and DRV.search(f["file"]))) and f["name"] in used_outside:
                tree_fn.add(f["name"])
    macdefs = {n: m for n, m in md_all.items() if n in BMAC or n == "NR_syscalls" or n in tree_mac}
    univ = BALL | tree_mac | tree_fn

    def item_names(raw):
        """facts names -> boundary item names (round-1 semantics for the current list)"""
        out = set()
        for x in raw:
            if x.startswith("#"):
                n = x[1:]
                if n in BMAC or n == "NR_syscalls" or n in tree_mac:
                    out.add(n)
            elif x in BNON or x in tree_fn:
                out.add(x)
        return sorted(out)

    byname = {}
    for usr, f in F.items():
        byname.setdefault(f["name"], []).append(usr)

    def value(name, arch):
        v = vals[arch].get(name)
        return v if isinstance(v, int) else None

    def divergent(item):
        if item in BALL or item == "NR_syscalls":  # round-1 rules, unchanged
            k = KIND.get(item)
            if item in BMAC and item not in BNON:
                md = macdefs.get(item)
                if md is not None and md["fl"]:
                    return True, "function-like macro"
                vs = [vals[a].get(item) for a in ARCHS]
                if any(not isinstance(v, int) for v in vs):
                    return True, "object-like macro: " + "/".join(str(v) if not isinstance(v, int) else "c" for v in vs)
                return len(set(vs)) > 1, "object-like macro values " + ("differ" if len(set(vs)) > 1 else "equal")
            if k == "function" or (item in BNON and byname.get(item)):
                return True, "function"
            if k == "object":
                return True, "object"
            if k == "enum_constant":
                vs = [vals[a].get(item) for a in ARCHS]
                if any(not isinstance(v, int) for v in vs):
                    return True, "enum constant (not const everywhere)"
                return len(set(vs)) > 1, "enum constant values " + ("differ" if len(set(vs)) > 1 else "equal")
            return True, "unknown kind"
        if item in tree_fn:
            return True, "I1 function"
        md = macdefs.get(item)
        if md is not None and md["fl"]:
            return True, "I1 function-like macro"
        vs = [vals[a].get(item) for a in ARCHS]
        if any(not isinstance(v, int) for v in vs):
            return True, "I1 object-like macro: " + "/".join(str(v) if not isinstance(v, int) else "c" for v in vs)
        return len(set(vs)) > 1, "I1 object-like macro values " + ("differ" if len(set(vs)) > 1 else "equal")

    def body_of(name):
        if name in macdefs:
            return sorted(set(macdefs[name]["body"]) & univ)
        if name in byname:
            s = set()
            for u in byname[name]:
                s |= set(F[u]["body"]) & univ
            s.discard(name)
            return sorted(s)
        return None

    def objlike(name):
        if name in BMAC and name not in BNON:
            md = macdefs.get(name)
            return md is None or not md["fl"]
        if name in tree_mac:
            return not macdefs[name]["fl"]
        return KIND.get(name) == "enum_constant"

    def expand(items):
        found, unknown = set(), set()
        for it in items:
            if objlike(it):
                found.add(it)
                continue
            b1 = body_of(it)
            if b1 is None:
                unknown.add(it)
                continue
            for x in b1:
                if objlike(x):
                    found.add(x)
                else:
                    b2 = body_of(x)
                    if b2 is None:
                        unknown.add(x)
                        continue
                    found |= {y for y in b2 if objlike(y)}
        return sorted(found), sorted(unknown)

    # I2 callback table
    cb, cb_field, cb_stats = {}, {}, {"registrations": 0, "typed": 0, "untyped": 0}
    if I2:
        regs = [r for f in F.values() for r in f.get("regs", [])]
        regs += [r[:5] for r in d.get("global_regs", []) if r[5] in active]
        for st, field, fname, *_ in regs:
            if fname not in byname:
                continue
            cb_stats["registrations"] += 1
            if st:
                cb.setdefault((st, field), set()).add(fname)
                cb_stats["typed"] += 1
            else:
                cb_stats["untyped"] += 1
            cb_field.setdefault(field, {}).setdefault(st, set()).add(fname)

    def targets(callee_usr, cname):
        """[(usr, via)]: direct callee, or callback targets for 'field:<struct>:<field>' (criteria I2)"""
        if not callee_usr.startswith("field:"):
            return [(callee_usr, "direct")] if callee_usr in F else []
        if not I2:
            return []
        _, st, field = callee_usr.split(":", 2)
        names = set()
        via = "typed"
        if st and (st, field) in cb:
            names |= cb[(st, field)]
        untyped = cb_field.get(field, {}).get("", set())
        if untyped:
            names |= untyped
            via = "field-only" if not names - untyped else "typed+field-only"
        if not st:
            for s2 in cb_field.get(field, {}).values():
                names |= s2
            via = "field-only"
        return [(u, via) for n in sorted(names) for u in byname.get(n, [])]

    entries = {}
    for usr, f in F.items():
        if f["name"].startswith("__do_sys_"):
            entries.setdefault(f["name"][len("__do_sys_"):], usr)

    sites, stats = {}, {"entries": len(entries), "reached_functions": 0, "guards_seen": 0, "sites": 0,
                        "sites_by_kind": {"K1": 0, "K2": 0, "K2_addrbits": 0}, "nondivergent_only": 0,
                        "cb_edges_used": {"typed": 0, "field-only": 0, "typed+field-only": 0}}
    reach_any, reach_map = {}, set()
    for sc, eusr in sorted(entries.items()):
        params = F[eusr]["params"]
        # reachability without mapping
        dist = {eusr: 0}
        q = deque([eusr])
        while q:
            u = q.popleft()
            if dist[u] >= DEPTH:
                continue
            for cusr, cname, args in F[u]["calls"]:
                for t, via in targets(cusr, cname):
                    if t not in dist:
                        dist[t] = dist[u] + 1
                        q.append(t)
        for u, dd in dist.items():
            n = F[u]["name"]
            reach_any[n] = min(reach_any.get(n, 99), dd)
        # BFS with parameter mapping (round-1 algorithm, callback targets added)
        maps = {eusr: {i: {i} for i in range(len(params))}}
        depth = {eusr: 0}
        q = deque([eusr])
        while q:
            u = q.popleft()
            if depth[u] >= DEPTH:
                continue
            for cusr, cname, args in F[u]["calls"]:
                tg = targets(cusr, cname)
                if not tg:
                    continue
                m = {}
                for ai, ps in enumerate(args):
                    s = set()
                    for p in ps:
                        s |= maps[u].get(p, set())
                    if s:
                        m[ai] = s
                if not m:
                    continue
                for t, via in tg:
                    if via != "direct":
                        stats["cb_edges_used"][via] += 1
                    old = maps.get(t)
                    if old is None:
                        maps[t], depth[t] = {k: set(v) for k, v in m.items()}, depth[u] + 1
                        q.append(t)
                    else:
                        grew = False
                        for k, v in m.items():
                            if not v <= old.get(k, set()):
                                old.setdefault(k, set()).update(v)
                                grew = True
                        if grew and depth[t] < DEPTH:
                            q.append(t)
        stats["reached_functions"] += len(maps)
        reach_map |= {F[u]["name"] for u in maps}
        out = []
        for u, m in maps.items():
            f = F[u]
            for g in f["guards"]:
                stats["guards_seen"] += 1
                sp = set()
                for p in g["p"]:
                    sp |= m.get(p, set())
                if not sp:
                    continue
                gitems = item_names(g["items"])
                div = [(it, divergent(it)) for it in gitems]
                dv = [it for it, (yes, _) in div if yes]
                if not dv:
                    if gitems:
                        stats["nondivergent_only"] += 1
                    continue
                values, kinds = {}, set()
                for c in g["cmps"]:
                    op = c["op"] if OPFIX else c["op_tok"]
                    if op not in ("<", "<=", ">", ">=", "==", "!=", "&"):
                        continue
                    for a, b in ((0, 1), (1, 0)):
                        cst = c["sides"][b]["const"]
                        if cst is None:
                            continue
                        tp = set()
                        for p in c["sides"][a]["p"]:
                            tp |= m.get(p, set())
                        for p in tp:
                            ptype = params[p][1]
                            if op == "&":
                                bits = [1 << i for i in range(64) if (cst >> i) & 1][:8]
                                vs = [cst, 0] + bits
                            else:
                                vs = [cst - 1, cst, cst + 1]
                            values.setdefault(p, set()).update("i:%x" % trunc(v, ptype) for v in vs)
                            kinds.add("K1")
                objs, unknown = expand(gitems)
                for o in objs:
                    avs = [value(o, a) for a in ARCHS]
                    for p in sp:
                        pname, ptype = params[p]
                        for v in avs:
                            if v is None:
                                continue
                            values.setdefault(p, set()).update("i:%x" % trunc(v + dd, ptype) for dd in (-1, 0, 1))
                            kinds.add("K2")
                            if is_addr(pname, ptype) and v > 0 and v.bit_length() <= 64:
                                values[p].add("o:%d" % (v.bit_length() - 1))
                                kinds.add("K2_addrbits")
                if not values:
                    continue
                out.append({"fn": f["name"], "file": f["file"], "line": g["line"], "depth": depth[u],
                            "items": gitems, "divergent": {it: why for it, (yes, why) in div if yes},
                            "objects": objs, "unknown_defs": unknown, "kinds": sorted(kinds),
                            "values": {str(p): sorted(v) for p, v in values.items()}})
                for k in kinds:
                    stats["sites_by_kind"][k] += 1
        if out:
            sites[sc] = out
            stats["sites"] += len(out)
    nr_ifs = [{"fn": f["name"], "file": f["file"], "line": x["line"]} for f in F.values()
              if f["file"].startswith("arch/riscv/kernel/") for x in f["nr_ifs"]]
    raw = None
    if nr_ifs:
        raw = {"ifs": nr_ifs, "values": ["r:%d" % dd for dd in (-1, 0, 1)] + ["i:%x" % (MASK)],
               "NR_syscalls": {a: vals[a].get("NR_syscalls") for a in ARCHS}}
    T = sorted(sites) + (["raw_nr"] if raw else [])
    stats["T"] = len(T)
    stats["tree_boundary"] = {"macros": len(tree_mac), "functions": len(tree_fn)}
    stats["callbacks"] = cb_stats
    return {"config": sorted(cfg), "depth": DEPTH, "entries": {sc: F[u]["params"] for sc, u in entries.items()},
            "sites": sites, "raw_nr": raw, "T": T, "stats": stats,
            "NR_syscalls": {a: vals[a].get("NR_syscalls") for a in ARCHS},
            "reach_any": reach_any, "reach_map": sorted(reach_map),
            "functions_index": {f["name"]: [f["file"], f["line"], f["end"]] for f in F.values()}}


def main():
    facts, values, config, out = sys.argv[1:5]
    cfg = set() if config == "base" else set(config.split(","))
    d = json.load(gzip.open(facts, "rt"))
    vals = json.loads(Path(values).read_text())
    res = run(d, vals, cfg)
    if "--group" in sys.argv:
        res["group"] = sys.argv[sys.argv.index("--group") + 1]
    Path(out).write_text(json.dumps(res))
    print(config, json.dumps(res["stats"]))


if __name__ == "__main__":
    main()
