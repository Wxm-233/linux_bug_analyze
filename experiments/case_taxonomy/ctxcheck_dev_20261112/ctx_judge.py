"""Verdicts on kernel call-context warnings (ctxcheck criteria 六). Pure Python.

    python ctx_judge.py   -> judge.json, prints a summary
Reads runs/{trap,sys}/<kernel>.run<i>.log.gz; warning events by dbgassert_dev_20261111/warn_parse.py.
"""
import importlib.util
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location("warn_parse", HERE.parent / "dbgassert_dev_20261111" / "warn_parse.py")
WP = importlib.util.module_from_spec(_s)
_s.loader.exec_module(WP)
CTX = re.compile(r"sleeping function called from invalid context|BUG: scheduling while atomic|inconsistent lock state|"
                 r"possible circular locking dependency|suspicious RCU usage|Invalid wait context")
KERNELS = {"a175_pre": "riscv", "a175_fix": "riscv", "a175_ref_arm64": "arm64", "a175_ref_x86_64": "x86_64"}
FIXFN = re.compile(r"do_trap_break|do_trap_insn_illegal|do_trap_\w+|handle_break|force_sig_fault|do_trap_error")


def is_ctx(e):
    return bool(CTX.search("\n".join(e["text"])))


def main():
    res = {"runs": {}, "ctx": {}, "odd": {}, "detect_A175": None}
    occ = {}  # (type, kernel) -> first-line signature -> {runs, phases, cases, example}
    for t in ("trap", "sys"):
        for k in KERNELS:
            for i in (1, 2, 3):
                f = HERE / "runs" / t / f"{k}.run{i}.log.gz"
                if not f.exists():
                    res["runs"][f"{t}/{k}.run{i}"] = "missing"
                    continue
                p = WP.parse(f)
                res["runs"][f"{t}/{k}.run{i}"] = {"complete": p["complete"], "cases": p["cases_seen"],
                                                  "events": len(p["events"]),
                                                  "ctx_events": sum(1 for e in p["events"] if is_ctx(e))}
                for e in p["events"]:
                    if not is_ctx(e):
                        continue
                    d = occ.setdefault((t, k), {}).setdefault(e["first"], {"runs": set(), "phases": set(), "cases": set(),
                                                                            "example": e["text"][:30]})
                    d["runs"].add(i)
                    d["phases"].add(e["phase"])
                    if e.get("case"):
                        d["cases"].add(e["case"])
    for (t, k), sigs in occ.items():
        res["ctx"][f"{t}/{k}"] = {s: {"runs": sorted(v["runs"]), "phases": sorted(v["phases"]),
                                      "cases": sorted(v["cases"], key=int)[:10], "example": v["example"]}
                                  for s, v in sigs.items()}
    # criteria 六: odd = in >= 2 of 3 runs of the checked kernel, in no run of any other-architecture kernel
    for t in ("trap", "sys"):
        for k, arch in KERNELS.items():
            refs = [r for r, a in KERNELS.items() if a != arch]
            other = set().union(*[set(occ.get((t, r), {})) for r in refs])
            odd = {s: v for s, v in occ.get((t, k), {}).items() if len(v["runs"]) >= 2 and s not in other}
            if odd:
                res["odd"][f"{t}/{k}"] = {s: {"runs": sorted(v["runs"]), "phases": sorted(v["phases"]),
                                             "cases": sorted(v["cases"], key=int)[:10]} for s, v in odd.items()}
    pre = res["odd"].get("trap/a175_pre", {})
    fix_sigs = set(occ.get(("trap", "a175_fix"), {}))
    hits = {s: v for s, v in pre.items() if "cases" in v["phases"] and s not in fix_sigs}
    res["detect_A175"] = {"candidates": hits,
                          "stack_mentions_fixed_handler": {s: bool(FIXFN.search("\n".join(occ[("trap", "a175_pre")][s]["example"])))
                                                           for s in hits}}
    (HERE / "judge.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf8")
    for r, v in res["runs"].items():
        print(r, v)
    for key, sigs in res["ctx"].items():
        for s, v in sigs.items():
            print(f"[ctx] {key}: {s[:110]} runs={v['runs']} phases={v['phases']} cases={v['cases'][:5]}")
    print("odd:", json.dumps(res["odd"], ensure_ascii=False)[:1500])
    print("A175:", json.dumps(res["detect_A175"], ensure_ascii=False)[:1500])


if __name__ == "__main__":
    main()
