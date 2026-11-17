"""Hint sites and hint values per syscall (criteria 4.3-4.6, amendment 2). Runs in WSL (needs the facts and values).

    python3 hints.py <group> -> ../gen/hints_<group>.json

Output: {"group", "entries": {syscall: [[pname, ptype], ...]}, "sites": {syscall: [site, ...]}, "T": [...],
         "raw_nr": {...} | null, "stats": {...}}
  site = {"fn", "file", "line", "depth", "items", "divergent", "kinds": [...],
          "values": {param idx: [token, ...]}, "unknown_defs": [...]}
Tokens: "i:<hex>" integer, "o:<bit>" valid buffer address | 2^bit (fill chosen by the generator),
        raw_nr: "r:<delta>" (relative to each arch's NR_syscalls) or "i:<hex>" absolute (negative).
"""
import gzip
import json
import sys
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAMES = json.loads((HERE / "boundary_names.json").read_text())
KIND = NAMES["kind"]
BMAC = set(NAMES["macro"])
BNON = set(NAMES["nonmacro"])
MASK = 2**64 - 1
ARCHS = ("riscv", "arm64", "x86_64")
DEPTH = 4
ADDR_NAMES = {"addr", "start", "brk", "uaddr", "uaddr2", "new_addr", "old_addr", "start_addr", "addr_hint"}


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


def main():
    group = sys.argv[1]
    tag = "CUR" if group == "CUR" else f"{group}_pre"
    d = json.load(gzip.open(f"/root/work/semhint/facts/{tag}.json.gz", "rt"))
    vals = json.loads(Path(f"/root/work/semhint/values/{group}.json").read_text())
    F = d["functions"]
    macdefs = d["macros"]
    byname = {}
    for usr, f in F.items():
        byname.setdefault(f["name"], []).append(usr)

    def value(name, arch):
        v = vals[arch].get(name)
        return v if isinstance(v, int) else None

    def divergent(item):
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

    def body_of(name):
        """identifiers in B of the definition body, or None when no definition is found"""
        if name in macdefs:
            return macdefs[name]["body"]
        if name in byname:
            s = set()
            for u in byname[name]:
                s |= set(F[u]["body"])
            s.discard(name)
            return sorted(s)
        return None

    def objlike(name):
        if name in BMAC and name not in BNON:
            md = macdefs.get(name)
            return md is None or not md["fl"]
        return KIND.get(name) == "enum_constant"

    def expand(items):
        """object-like boundary macros / enum constants within 2 levels of definition bodies (criteria 4.2)"""
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

    entries = {}
    for usr, f in F.items():
        if f["name"].startswith("__do_sys_"):
            entries.setdefault(f["name"][len("__do_sys_"):], usr)

    sites, stats = {}, {"entries": len(entries), "reached_functions": 0, "guards_seen": 0, "sites": 0,
                        "sites_by_kind": {"K1": 0, "K2": 0, "K2_addrbits": 0}, "nondivergent_only": 0}
    for sc, eusr in sorted(entries.items()):
        params = F[eusr]["params"]
        # BFS with parameter mapping: usr -> {callee param idx: set(syscall param idx)}
        maps = {eusr: {i: {i} for i in range(len(params))}}
        depth = {eusr: 0}
        q = deque([eusr])
        while q:
            u = q.popleft()
            if depth[u] >= DEPTH:
                continue
            for cusr, cname, args in F[u]["calls"]:
                if cusr not in F:
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
                old = maps.get(cusr)
                if old is None:
                    maps[cusr], depth[cusr] = m, depth[u] + 1
                    q.append(cusr)
                else:
                    grew = False
                    for k, v in m.items():
                        if not v <= old.get(k, set()):
                            old.setdefault(k, set()).update(v)
                            grew = True
                    if grew and depth[cusr] < DEPTH:
                        q.append(cusr)
        stats["reached_functions"] += len(maps)
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
                div = [(it, divergent(it)) for it in g["items"]]
                dv = [it for it, (yes, _) in div if yes]
                if not dv:
                    if g["items"]:
                        stats["nondivergent_only"] += 1
                    continue
                values, kinds = {}, set()
                # K1 thresholds
                for c in g["cmps"]:
                    for a, b in ((0, 1), (1, 0)):
                        cst = c["sides"][b]["const"]
                        if cst is None:
                            continue
                        tp = set()
                        for p in c["sides"][a]["p"]:
                            tp |= m.get(p, set())
                        for p in tp:
                            ptype = params[p][1]
                            if c["op"] == "&":
                                bits = [1 << i for i in range(64) if (cst >> i) & 1][:8]
                                vs = [cst, 0] + bits
                            else:
                                vs = [cst - 1, cst, cst + 1]
                            values.setdefault(p, set()).update("i:%x" % trunc(v, ptype) for v in vs)
                            kinds.add("K1")
                # K2 cross-arch values of object-like items within 2 definition levels
                objs, unknown = expand(g["items"])
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
                            "items": g["items"], "divergent": {it: why for it, (yes, why) in div if yes},
                            "objects": objs, "unknown_defs": unknown, "kinds": sorted(kinds),
                            "values": {str(p): sorted(v) for p, v in values.items()}})
                for k in kinds:
                    stats["sites_by_kind"][k] += 1
        if out:
            sites[sc] = out
            stats["sites"] += len(out)

    # K3 entry channel (criteria 4.3, amendment 2)
    nr_ifs = [{"fn": f["name"], "file": f["file"], "line": x["line"]} for f in F.values()
              if f["file"].startswith("arch/riscv/kernel/") for x in f["nr_ifs"]]
    raw = None
    if nr_ifs:
        raw = {"ifs": nr_ifs, "values": ["r:%d" % dd for dd in (-1, 0, 1)] + ["i:%x" % (MASK)],
               "NR_syscalls": {a: vals[a].get("NR_syscalls") for a in ARCHS}}
    T = sorted(sites) + (["raw_nr"] if raw else [])
    stats["T"] = len(T)
    res = {"group": group, "tree": tag, "entries": {sc: F[u]["params"] for sc, u in entries.items()},
           "sites": sites, "raw_nr": raw, "T": T, "stats": stats,
           "NR_syscalls": {a: vals[a].get("NR_syscalls") for a in ARCHS}}
    (HERE.parent / "gen" / f"hints_{group}.json").write_text(json.dumps(res, indent=0))
    print(group, json.dumps(stats))


if __name__ == "__main__":
    main()
