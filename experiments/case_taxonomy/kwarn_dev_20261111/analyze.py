"""Warnings per kernel and comparison with the quiet runs (kwarn criteria 三). Pure Python.

    python analyze.py -> cmp/<g>/compare.json, runs/<g>/warnings.json, stats.json
"""
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
T = CT / "difftest_tools_20261111"


def mod(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


N = mod("tools_compare", T / "compare.py")
Wn = mod("tools_warnings", T / "warnings.py")
GROUPS = ["CUR", "A101", "A310", "A171", "A181", "B467"]


def detecting(out, g):
    p = g.lower()
    pre, fix = out["checked"][f"{p}_pre"]["verdicts"], out["checked"][f"{p}_fix"]["verdicts"]
    return sorted((i for i, v in pre.items() if v in ("odd_riscv", "weak_diff")
                   and fix.get(i, "same") in ("same", "weak_same")), key=int)


def main():
    stats = {"warnings": {}, "vs_quiet": {}}
    for g in GROUPS:
        # --- warnings
        sig, runs = {}, {}
        import glob, os, re
        for f in sorted(glob.glob(str(HERE / "runs" / g / "*.log.gz"))):
            k, i = re.match(r"(.*)\.run(\d)\.log\.gz", os.path.basename(f)).groups()
            p = Wn.parse(f)
            runs[f"{k}.run{i}"] = {"complete": p["complete"], "taint_changed": p["taint_changed"],
                                   "cases_seen": p["cases_seen"], "events": p["events"]}
            for e in p["events"]:
                ph = "cases" if e["phase"] == "cases_tail" else e["phase"]
                d = sig.setdefault((ph, e["signature"]), {}).setdefault(k, {"runs": set(), "cases": set()})
                d["runs"].add(i)
                if e.get("case"):
                    d["cases"].add(e["case"])
        summ = [{"phase": ph, "signature": s, "kernels": {k: {"runs": sorted(v["runs"]),
                                                              "cases": sorted(v["cases"], key=int)[:20]}
                                                          for k, v in ks.items()}}
                for (ph, s), ks in sorted(sig.items())]
        (HERE / "runs" / g / "warnings.json").write_text(
            json.dumps({"runs": runs, "signatures": summ}, indent=1, ensure_ascii=False), encoding="utf8")
        stats["warnings"][g] = {"signatures": summ,
                                "incomplete": [r for r, p in runs.items() if not p["complete"]],
                                "taint_changed": {r: p["taint_changed"] for r, p in runs.items()
                                                  if p["taint_changed"] not in ("0", None)},
                                "events_per_run": {r: len(p["events"]) for r, p in runs.items()}}
        # --- verdicts vs the quiet run of the diverse round (same tool, same rules)
        new = N.run(HERE / f"kernels_{g}.json")
        old = json.loads((T / "regress" / f"{g}_tc_on" / "compare.json").read_text(encoding="utf8"))
        row = {}
        ids = set()
        for k in new["checked"]:
            vo, vn = old["checked"][k]["verdicts"], new["checked"][k]["verdicts"]
            ch = [i for i in set(vo) | set(vn) if vo.get(i, "same") != vn.get(i, "same")]
            moves = {}
            for i in ch:
                m = f"{vo.get(i, 'same')} -> {vn.get(i, 'same')}"
                moves[m] = moves.get(m, 0) + 1
            row[k] = {"differ": len(ch), "moves": dict(sorted(moves.items())),
                      "clusters_quiet": {a: len(x) for a, x in old["checked"][k]["clusters"].items()},
                      "clusters_loglevel5": {a: len(x) for a, x in new["checked"][k]["clusters"].items()},
                      "unstable": [old["checked"][k]["summary"].get("unstable", 0),
                                   new["checked"][k]["summary"].get("unstable", 0)]}
        if g != "CUR":
            d0, d1 = detecting(old, g), detecting(new, g)
            row["detecting"] = {"quiet": len(d0), "loglevel5": len(d1), "same_set": d0 == d1,
                                "lost": sorted(set(d0) - set(d1), key=int), "gained": sorted(set(d1) - set(d0), key=int)}
        stats["vs_quiet"][g] = row
    (HERE / "stats.json").write_text(json.dumps(stats, indent=1, ensure_ascii=False), encoding="utf8")
    print("\n=== warnings")
    for g, w in stats["warnings"].items():
        print(g, "incomplete", w["incomplete"], "taint", w["taint_changed"], "events", sum(w["events_per_run"].values()))
        for s in w["signatures"]:
            print("   [%s] %s" % (s["phase"], s["signature"][:140]))
            for k, v in s["kernels"].items():
                print("        ", k, "runs", v["runs"], "cases", v["cases"][:6])
    print("\n=== vs quiet")
    for g, row in stats["vs_quiet"].items():
        print(g, {k: (v["differ"], v["moves"]) for k, v in row.items() if k != "detecting"
                  and ("riscv" in k or "_pre" in k or "_fix" in k)}, row.get("detecting"))


if __name__ == "__main__":
    main()
