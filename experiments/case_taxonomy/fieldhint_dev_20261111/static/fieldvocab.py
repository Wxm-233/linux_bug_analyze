"""Field vocabulary per syscall (fieldhint criteria 二.3). Pure Python (runs in WSL on the facts).

    python3 fieldvocab.py <facts.json.gz> <layouts.json> <out.json>

For every syscall entry __do_sys_<sc>: functions reachable within 8 calls (direct calls, and indirect calls through
'field:<struct>:<field>' resolved with the registrations, as in hints4 I2), without parameter mapping.  In those
functions: guard comparisons whose one side is a constant and whose other side reads struct members ("m"), and
switch conditions that read struct members.  Kept: members of struct types reachable from the syscall's pointer
parameters within two levels of the riscv layout (the same roots as the structured buffers).
Output {sc: {"struct T|field": {"eq": [...], "bits": [...], "bounds": [...]}}}
"""
import gzip
import json
import sys
from collections import deque

DEPTH = 8
EQ, BITS, BOUNDS = ("==", "!="), ("&",), ("<", "<=", ">", ">=")


def pointee(ptype):
    t = ptype.replace("const ", "").replace("volatile ", "").strip()
    if t.endswith("*"):
        b = t[:-1].strip()
        if b.startswith(("struct ", "union ")) and "*" not in b:
            return b
    return None


def main():
    facts = json.load(gzip.open(sys.argv[1], "rt"))
    lay = json.loads(open(sys.argv[2]).read())["riscv"]
    F = facts["functions"]
    byname = {}
    for u, f in F.items():
        byname.setdefault(f["name"], []).append(u)
    regs = [r for f in F.values() for r in f.get("regs", [])] + [r[:5] for r in facts.get("global_regs", [])]
    cb = {}
    for st, field, fname, *_ in regs:
        cb.setdefault((st, field), set()).update(byname.get(fname, []))
        cb.setdefault(("", field), set()).update(byname.get(fname, []))

    def callees(c):
        u = c[0]
        if u.startswith("field:"):
            _, st, field = u.split(":", 2)
            return cb.get((st, field), set()) | (cb.get(("", field), set()) if not st else set())
        return {u} if u in F else set()

    entries = {f["name"][len("__do_sys_"):]: u for u, f in F.items() if f["name"].startswith("__do_sys_")}
    out, stats = {}, {"syscalls": 0, "fields": 0}
    for sc, eu in sorted(entries.items()):
        roots = {pointee(t) for _, t in F[eu]["params"]} - {None}
        types, todo = set(), [(t, 0) for t in roots]
        while todo:
            t, d = todo.pop()
            if t in types or t not in lay:
                continue
            types.add(t)
            if d < 2:
                todo += [(f["pointee"], d + 1) for f in lay[t]["fields"] if f.get("pointee")]
        if not types:
            continue
        seen, q = {eu: 0}, deque([eu])
        while q:
            u = q.popleft()
            if seen[u] >= DEPTH:
                continue
            for c in F[u]["calls"]:
                for v in callees(c):
                    if v not in seen:
                        seen[v] = seen[u] + 1
                        q.append(v)
        voc = {}
        for u in seen:
            f = F[u]
            for g in f["guards"]:
                for c in g["cmps"]:
                    op = c["op"] or c["op_tok"]
                    for a, b in ((0, 1), (1, 0)):
                        cst, ms = c["sides"][b]["const"], c["sides"][a].get("m", [])
                        if cst is None or not ms:
                            continue
                        kind = "eq" if op in EQ else "bits" if op in BITS else "bounds" if op in BOUNDS else None
                        if kind is None:
                            continue
                        for m in ms:
                            t, field = m.split("|", 1)
                            if t in types and any(x["name"] == field for x in lay[t]["fields"]):
                                e = voc.setdefault(m, {"eq": set(), "bits": set(), "bounds": set()})
                                if kind == "bits":
                                    e["bits"].update(1 << i for i in range(64) if (cst >> i) & 1 and i < 64)
                                else:
                                    e[kind].add(cst)
            for sw in f.get("switches", []):
                for m in sw.get("m", []):
                    t, field = m.split("|", 1)
                    if t in types and any(x["name"] == field for x in lay[t]["fields"]):
                        voc.setdefault(m, {"eq": set(), "bits": set(), "bounds": set()})["eq"].update(sw["cases"])
        if voc:
            out[sc] = {m: {k: sorted(v)[:64] for k, v in e.items()} for m, e in sorted(voc.items())}
            stats["syscalls"] += 1
            stats["fields"] += len(voc)
    open(sys.argv[3], "w").write(json.dumps({"stats": stats, "vocab": out}, indent=0))
    print(json.dumps(stats), "perf_event_open:", {k: v for k, v in out.get("perf_event_open", {}).items()
                                                   if k.endswith("|type")})


if __name__ == "__main__":
    main()
