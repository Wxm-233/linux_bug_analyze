"""Confirmation stage (criteria v1 六.2), read-only, WSL: for the functions each fix changes, are they compiled in the
default configuration (in the facts), reachable from a system call (hints4 reach, depth 8), mapped with an argument,
a hint site (full, unpruned), and kept after pruning (hints_<g>.json)?
    TARGET=loongarch BOUNDARY_POOL=none PYTHONPATH=<pipeline> python3 reach.py > reach.json
"""
import gzip, json, os
import hints4
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXFN = {  # functions named in the fix hunks (read after all runs and scoring)
    "L02": ["kasan_mem_to_shadow"], "L03": ["do_syscall"], "L04": ["hw_breakpoint_slots", "arch_install_hw_breakpoint",
    "hw_breakpoint_arch_parse"], "L05": ["regs_irqs_disabled"],
    "L06": ["clock_getres_fallback", "clock_gettime_fallback", "gettimeofday_fallback", "getrandom_syscall"],
    "L07": ["__arch_prepare_bpf_trampoline", "arch_prepare_bpf_trampoline"], "L08": ["arch_protect_bpf_trampoline"],
    "L09": ["pte_wrprotect", "pmd_wrprotect"], "L10": ["bpf_jit_free"]}
out = {}
for g, names in FIXFN.items():
    F = json.load(gzip.open(f"{R}/static/{g}/facts.json.gz", "rt"))
    vals = json.load(open(f"{R}/static/{g}/values.json"))
    h = hints4.run(F, vals, {"I1", "I2", "I3", "I4"})
    pruned = json.load(open(f"{R}/static/{g}/hints_{g}.json"))["sites"]
    fn = F["functions"]
    called = {}
    for f in fn.values():
        for c in f["calls"]:
            called.setdefault(c[1], set()).add(f["name"])
    row = {}
    for n in names:
        defs = [(f["file"], f["line"]) for f in fn.values() if f["name"] == n]
        row[n] = {"in_facts": defs[:3], "callers": sorted(called.get(n, []))[:8], "reach_depth": h["reach_any"].get(n),
                  "arg_mapped": n in h["reach_map"],
                  "sites": sorted({sc for sc, ss in h["sites"].items() for s in ss if s["fn"] == n})[:10],
                  "sites_after_pruning": sorted({sc for sc, ss in pruned.items() for s in ss if s["fn"] == n})}
    out[g] = row
    print(g, json.dumps(row, ensure_ascii=False), flush=True)
json.dump(out, open(f"{R}/confirm/reach.json", "w"), indent=1)
