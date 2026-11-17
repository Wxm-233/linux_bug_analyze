"""Stability, capability probes, automatic exclusion and majority verdicts (criteria sections 5-7).

    python compare2.py [run tag]     (default: all)  -> runs/<tag>/compare2.json

Reads runs/<tag>/<kernel>.run{1,2,3}.log and truth.json (from truth.py).
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REFS = ["cur_arm64", "cur_x86_64"]

# criteria section 5: test prerequisites (fixed before any run)
NEEDS = {"hw_cycles": "ev_cycles", "hw_instructions": "ev_instructions", "breakpoint_exec": "bp_pmu"}
for _t in ["hw_config_max", "hw_config_bogus", "cache_l1d_read_access", "cache_config_bogus", "raw_zero", "raw_bogus"]:
    NEEDS[_t] = "hw_pmu"

# capability -> configuration options whose presence means "the kernel has the feature" (per arch)
CAP_CONFIG = {
    "hw_pmu": {"riscv": ["RISCV_PMU_SBI", "RISCV_PMU_LEGACY"], "arm64": ["ARM_PMUV3", "HW_PERF_EVENTS"],
               "x86_64": ["CPU_SUP_INTEL", "CPU_SUP_AMD"]},
    "bp_pmu": {a: ["HAVE_HW_BREAKPOINT"] for a in ("riscv", "arm64", "x86_64")},
}
CAP_CONFIG["ev_cycles"] = CAP_CONFIG["ev_instructions"] = CAP_CONFIG["hw_pmu"]
EVENT_NAMES = {"ev_cycles": {"cpu_cycles", "cycles"}, "ev_instructions": {"inst_retired", "instructions"}}

# criteria section 7: symptom keys
SYMPTOMS = {
    "A101": ["mmap_hint_occupied"],
    "A310": ["syscall_minus1", "syscall_minus1_traced"],
    "A171": ["futex_wake_highalias"],
    "A181": ["cmsg_len_unaligned"],
    "B467": ["type_unknown", "cache_l1d_read_access", "breakpoint_exec", "hw_config_bogus", "hw_config_max",
             "raw_bogus", "cache_config_bogus"],
}


def is_hw_pmu(n):
    return n in ("cpu", "cpu_core", "cpu_atom") or n.startswith("armv8") or n.startswith("armv9")


def parse(log):
    text = log.read_bytes().replace(b"\x00", b"").decode("utf-8", "replace")
    m = re.search(r"@@DT BEGIN\r?\n(.*?)@@DT END", text, re.S)
    if not m:
        return None
    tests, probes = {}, {"pmu_events": {}}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        r = json.loads(line)
        if "test" in r:
            tests[r["test"]] = r["result"]
        elif r["probe"] == "pmu_events":
            probes["pmu_events"][r["pmu"]] = r["value"]
        elif r["probe"] == "cpuinfo":
            probes[f"cpuinfo_{r['key']}"] = r["value"]
        else:
            probes[r["probe"]] = r["value"]
    return {"tests": tests, "probes": probes}


def capabilities(probes):
    devs = probes.get("pmu_devices") or []
    hw = [d for d in devs if is_hw_pmu(d)]
    caps = {"hw_pmu": "met" if hw else "unmet", "bp_pmu": "met" if "breakpoint" in devs else "unmet"}
    for cap, names in EVENT_NAMES.items():
        if not hw:
            caps[cap] = "unmet"
            continue
        declared = [probes["pmu_events"].get(d) for d in hw]
        if all(v is None for v in declared):
            caps[cap] = "unknown"
        else:
            caps[cap] = "met" if any(v and names & set(v) for v in declared) else "unmet"
    return caps


def exclusion_kind(cap, kernel, truth):
    k = truth["kernels"][kernel]
    opts = CAP_CONFIG[cap][k["arch"]]
    has = any(k["config"].get(o, "n") in ("y", "m") for o in opts)
    return "环境" if has else "能力"


def load(tag, truth):
    d = HERE / "runs" / tag
    kernels = {}
    for name in truth["kernels"]:
        runs = [parse(p) for p in sorted(d.glob(f"{name}.run*.log"))]
        if not runs:
            continue
        kernels[name] = runs
    return kernels


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "all"
    truth = json.loads((HERE / "truth.json").read_text())
    kernels = load(tag, truth)
    out = {"tag": tag, "kernels": {}, "verdicts": {}, "evaluation": {}}
    stable_res, caps = {}, {}
    for name, runs in kernels.items():
        ok = [r for r in runs if r]
        keys = sorted(set().union(*(r["tests"] for r in ok))) if ok else []
        unstable = [k for k in keys if len({r["tests"].get(k) for r in ok}) > 1]
        stable_res[name] = {k: ok[0]["tests"].get(k) for k in keys if k not in unstable}
        probe_sets = [json.dumps(capabilities(r["probes"]), sort_keys=True) for r in ok]
        caps[name] = capabilities(ok[0]["probes"]) if ok else {}
        out["kernels"][name] = {
            "runs": len(runs), "complete_runs": len(ok), "unstable": unstable,
            "capabilities": caps[name], "capabilities_stable": len(set(probe_sets)) <= 1,
            "pmu_devices": ok[0]["probes"].get("pmu_devices") if ok else None,
            "mmu": ok[0]["probes"].get("cpuinfo_mmu") if ok else None,
            "taint_changed": sorted({str(r["probes"].get("taint_changed")) for r in ok}),
            "results": stable_res[name],
        }

    def status(kernel, test):
        need = NEEDS.get(test)
        if not need:
            return "met", None
        s = caps[kernel].get(need, "unmet")
        return s, need

    for name in kernels:
        if truth["kernels"][name]["arch"] != "riscv":
            continue
        v = {}
        for test, val in stable_res[name].items():
            rec = {"value": val}
            s, need = status(name, test)
            if s == "unmet":
                rec.update(verdict="剔除", kind=exclusion_kind(need, name, truth), need=need)
                v[test] = rec
                continue
            comparable, excluded = {}, {}
            for ref in REFS:
                if ref not in stable_res or test not in stable_res[ref]:
                    continue
                rs, rneed = status(ref, test)
                if rs == "unmet":
                    excluded[ref] = exclusion_kind(rneed, ref, truth)
                else:
                    comparable[ref] = stable_res[ref][test]
            rec.update(refs=comparable, refs_excluded=excluded)
            if not comparable:
                rec["verdict"] = "无参照"
            elif len(set(comparable.values())) > 1:
                rec["verdict"] = "参照分歧"
            elif val == next(iter(comparable.values())):
                rec["verdict"] = "一致"
            else:
                rec["verdict"] = "与众不同"
                rec["strength"] = "强" if len(comparable) == 2 else "弱"
            v[test] = rec
        for test in kernels[name][0]["tests"] if kernels[name][0] else []:
            if test not in v and test in out["kernels"][name]["unstable"]:
                v[test] = {"verdict": "不稳定"}
        out["verdicts"][name] = v

    # evaluation (criteria section 7)
    ev = {"per_sample": {}, "false_outliers": [], "outliers": []}
    for name, v in out["verdicts"].items():
        present = truth["present"].get(name, [])
        allowed = {k for sid in present for k in SYMPTOMS[sid]}
        for test, rec in v.items():
            if rec["verdict"] == "与众不同":
                item = {"kernel": name, "test": test, "value": rec["value"], "refs": rec["refs"],
                        "strength": rec["strength"], "explained_by": [s for s in present if test in SYMPTOMS[s]]}
                ev["outliers"].append(item)
                if test not in allowed:
                    ev["false_outliers"].append(item)
    for sid in SYMPTOMS:
        pre, fix = f"{sid.lower()}_pre", f"{sid.lower()}_fix"
        res = {}
        for kname, want in ((pre, True), (fix, False)):
            if kname not in out["verdicts"]:
                res[kname] = "not_run"
                continue
            hits = [t for t in SYMPTOMS[sid] if out["verdicts"][kname].get(t, {}).get("verdict") == "与众不同"]
            res[kname] = {"present_by_truth": sid in truth["present"].get(kname, []), "symptom_outliers": hits}
        detected = isinstance(res.get(pre), dict) and bool(res[pre]["symptom_outliers"])
        cleared = isinstance(res.get(fix), dict) and not res[fix]["symptom_outliers"]
        res["detected"], res["cleared"], res["pass"] = detected, cleared, detected and cleared
        ev["per_sample"][sid] = res
    # every riscv kernel in which a bug is present: detected there?
    ev["presence_matrix"] = {}
    for name, v in out["verdicts"].items():
        for sid in truth["present"].get(name, []):
            hits = [t for t in SYMPTOMS[sid] if v.get(t, {}).get("verdict") == "与众不同"]
            ev["presence_matrix"][f"{name}:{sid}"] = hits
    ev["pass_count"] = sum(1 for r in ev["per_sample"].values() if r["pass"])
    ev["verdict_counts"] = {n: dict(Counter(r["verdict"] for r in v.values())) for n, v in out["verdicts"].items()}
    out["evaluation"] = ev
    (HERE / "runs" / tag / "compare2.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for n, k in out["kernels"].items():
        print(f"{n:12s} runs={k['complete_runs']}/{k['runs']} unstable={k['unstable']} caps={k['capabilities']}")
    print("per sample:", {s: (r["detected"], r["cleared"]) for s, r in ev["per_sample"].items()})
    print("outliers:")
    for o in ev["outliers"]:
        print("  ", o["kernel"], o["test"], o["value"], o["refs"], o["strength"], "explained_by", o["explained_by"])
    print("false outliers:", len(ev["false_outliers"]))
    print("presence matrix:", ev["presence_matrix"])


if __name__ == "__main__":
    main()
