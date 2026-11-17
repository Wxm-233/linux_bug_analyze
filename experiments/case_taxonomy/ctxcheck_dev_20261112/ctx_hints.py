"""Step 6 of the pipeline: call-context hints (ctxcheck criteria 三). Runs in WSL (facts are there).

    python3 ctx_hints.py <flags.json> <facts.json.gz> <out.json>

flags.json: execution-context flags of checks_v1_20261108 (results/<sample>_{pre,fix}.json).
Output {"traps": {kind: {"n", "examples"}}, "syscalls": {sc: {"score", "examples"}}, "filtered": {...}}.
"""
import gzip
import json
import re
import sys
from collections import deque

DEPTH = 8
TOP = 20
TRAP = {"do_trap_break": "breakpoint", "do_trap_insn_illegal": "illegal_insn",
        "do_trap_load_misaligned": "misaligned_load", "do_trap_store_misaligned": "misaligned_store",
        "do_trap_load_fault": "access_fault", "do_trap_store_fault": "access_fault",
        "do_trap_insn_fault": "access_fault", "do_page_fault": "page_fault"}
NOISE_W = re.compile(r"^(preempt_schedule\w*|_printk|printk|vprintk\w*|__warn_printk|console_\w+)$")
NOISE_C = re.compile(r"^(start_kernel|rest_init|early_\w+)$")


def noisy(f):
    """criteria 三.1: known false-positive sources listed in checks_v1 README before this round"""
    if any(NOISE_W.match(w) for w in f.get("witness") or []):
        return "witness"
    if NOISE_C.match(f["caller"]):
        return "early"
    return None


def chain_names(f):
    return [f["caller"]] + [c[0] for c in f.get("origin_chain") or []]


def main():
    fp, factp, out = sys.argv[1:4]
    flags = json.load(open(fp))["flags"]
    kept, filt = [], {"witness": 0, "early": 0}
    for f in flags:
        why = noisy(f)
        if why:
            filt[why] += 1
        else:
            kept.append(f)
    # user trap entries
    traps = {}
    for f in kept:
        kinds = {TRAP[n] for n in chain_names(f) if n in TRAP}
        for k in kinds:
            t = traps.setdefault(k, {"n": 0, "sites": set(), "examples": []})
            key = tuple(f["site"])
            if key in t["sites"]:
                continue
            t["sites"].add(key)
            t["n"] += 1
            if len(t["examples"]) < 5:
                t["examples"].append({"kind": f["kind"], "caller": f["caller"], "site": f["site"], "callee": f["callee"],
                                      "witness": (f.get("witness") or [])[:6], "origin": f["origin"]})
    for t in traps.values():
        del t["sites"]
    # syscall entries: flags whose state is set inside the path (no trap / IPI entry in the origin chain)
    local = [f for f in kept if not any(c[0].startswith("<") for c in f.get("origin_chain") or [])]
    by_caller = {}
    for f in local:
        by_caller.setdefault(f["caller"], []).append(f)
    F = json.load(gzip.open(factp, "rt"))["functions"]
    byname = {}
    for u, f in F.items():
        byname.setdefault(f["name"], []).append(u)
    sc = {}
    for u, f in F.items():
        if not f["name"].startswith("__do_sys_"):
            continue
        name = f["name"][len("__do_sys_"):]
        dist, q = {u: 0}, deque([u])
        while q:
            x = q.popleft()
            if dist[x] >= DEPTH:
                continue
            for cu, cn, _ in F[x]["calls"]:
                for t in ([cu] if cu in F else byname.get(cn, [])):
                    if t not in dist:
                        dist[t] = dist[x] + 1
                        q.append(t)
        names = {F[x]["name"] for x in dist}
        sites, ex = set(), []
        for n in names & set(by_caller):
            for fl in by_caller[n]:
                if tuple(fl["site"]) not in sites:
                    sites.add(tuple(fl["site"]))
                    if len(ex) < 3:
                        ex.append({"kind": fl["kind"], "caller": fl["caller"], "callee": fl["callee"], "site": fl["site"]})
        if sites:
            sc[name] = {"score": len(sites), "examples": ex}
    top = dict(sorted(sc.items(), key=lambda kv: (-kv[1]["score"], kv[0]))[:TOP])
    res = {"flags": len(flags), "kept": len(kept), "filtered": filt, "traps": traps,
           "syscalls_with_flags": len(sc), "syscalls": top}
    json.dump(res, open(out, "w"), indent=1)
    print("flags", len(flags), "kept", len(kept), "filtered", filt)
    print("traps", {k: v["n"] for k, v in traps.items()})
    print("syscalls with flags", len(sc), "top", [(k, v["score"]) for k, v in top.items()])


if __name__ == "__main__":
    main()
