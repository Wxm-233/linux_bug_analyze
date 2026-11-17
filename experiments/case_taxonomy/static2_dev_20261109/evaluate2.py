"""Ablation of I1-I4 (criteria 四, amendment 1). Runs in WSL.

    python3 evaluate2.py   -> ablation.json, baseline_check.json, sample_entities.json,
                              ../gen hints (static2_dev_20261109/gen/hints_<group>.json, configuration "all")
"""
import gzip
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "static"))
from hints2 import run  # noqa: E402

R1 = HERE.parent / "semhint_dev_20261109"
GROUPS = ["A101", "A310", "A171", "A181", "B467", "CUR"]
CONFIGS = {"base": set(), "fix": {"fix"}, "I1": {"I1"}, "I2": {"I2"}, "I3": {"I3"}, "I4": {"I4"},
           "all": {"I1", "I2", "I3", "I4"}}
FIXC = {"A101": "2116988d5372", "A310": "61119394631f", "A171": "890ba5be6335", "A181": "1046791390af",
        "B467": "c625154993d0"}
FIXPOINT = {"A101": ("macro", ["arch_get_mmap_end"]), "A171": ("macro", ["TASK_SIZE_MAX"]),
            "A181": ("macro", ["__put_user", "put_user"]), "A310": ("entry", ["do_trap_ecall_u"]), "B467": None}


def changed_functions(sample, facts):
    """functions of the pre-fix tree containing a removed/changed line of the fix (old side of the diff)"""
    diff = subprocess.run(["git", "-C", "/root/repos/linux", "diff", "-U0", f"{FIXC[sample]}^", FIXC[sample]],
                          capture_output=True, text=True, check=True).stdout
    lines, cur = [], None
    for l in diff.splitlines():
        if l.startswith("--- a/"):
            cur = l[6:]
        m = re.match(r"^@@ -(\d+)(?:,(\d+))? ", l)
        if m and cur:
            a, n = int(m.group(1)), int(m.group(2) or 1)
            lines += [(cur, x) for x in range(a, a + max(n, 1))]
    names = set()
    for f in facts["functions"].values():
        for (p, x) in lines:
            if f["file"] == p and f["line"] <= x <= f.get("end", f["line"]):
                names.add(f["name"])
    return sorted(names), sorted({p for p, _ in lines})


def status(h, facts, kind, names):
    """可达 / 映射可达 / 进入提示点 for function or macro fix points (criteria 4.1)"""
    ra, rm = h["reach_any"], set(h["reach_map"])
    active = {f["name"]: f for f in facts["functions"].values() if f["name"] in ra}
    if kind == "function":
        reach = any(n in ra for n in names)
        mreach = any(n in rm for n in names)
    else:
        users = {fn for fn, f in active.items() if set(names) & set(f["body"])}
        reach = bool(users)
        mreach = bool(users & rm)
    insite = []
    for sc, ss in h["sites"].items():
        for s in ss:
            if (kind == "function" and s["fn"] in names) or set(names) & (set(s["items"]) | set(s["objects"])):
                insite.append(f"{sc}:{s['fn']}:{s['line']}")
    return {"reach": reach, "map_reach": mreach, "in_site": bool(insite), "n_sites": len(insite),
            "sites": insite[:8]}


def main():
    ablation, bcheck, ents = {}, {}, {}
    samples = json.loads((HERE.parent / "boundary_closure_20261108/sample_match_v2.json").read_text(
        encoding="utf-8"))["samples"]
    for g in GROUPS:
        tag = "CUR" if g == "CUR" else f"{g}_pre"
        facts = json.load(gzip.open(f"/root/work/static2/facts/{tag}.json.gz", "rt"))
        vals = json.loads(Path(f"/root/work/static2/values/{g}.json").read_text())
        old = json.loads((R1 / "gen" / f"hints_{g}.json").read_text())
        ablation[g] = {"units": facts["unit_status"]}
        fixpt = FIXPOINT.get(g)
        if g == "B467":
            fns, files = changed_functions(g, facts)
            fixpt = ("function", fns)
            ablation[g]["fix_functions"] = {"functions": fns, "files": files}
        for cname, cfg in CONFIGS.items():
            h = run(facts, vals, cfg)
            st = h["stats"]
            row = {"sites": st["sites"], "T": st["T"], "entries": st["entries"],
                   "reached_functions": st["reached_functions"], "reach_any": len(h["reach_any"]),
                   "reach_map": len(h["reach_map"]), "tree_boundary": st["tree_boundary"],
                   "callbacks": st["callbacks"], "cb_edges_used": st["cb_edges_used"],
                   "sites_by_kind": st["sites_by_kind"]}
            if cname == "base":
                same_sites = {sc: [(s["fn"], s["line"], s["values"]) for s in ss] for sc, ss in h["sites"].items()} == \
                    {sc: [(s["fn"], s["line"], s["values"]) for s in ss] for sc, ss in old["sites"].items()}
                bcheck[g] = {"sites": [st["sites"], old["stats"]["sites"]], "T": [st["T"], old["stats"]["T"]],
                             "equal": st["sites"] == old["stats"]["sites"] and st["T"] == old["stats"]["T"],
                             "sites_identical": same_sites}
            if g != "CUR":
                kind, names = fixpt
                if kind == "entry":
                    ok = bool(h["raw_nr"]) and any(x["fn"] == "do_trap_ecall_u" for x in h["raw_nr"]["ifs"])
                    row["fixpoint"] = {"reach": ok, "map_reach": ok, "in_site": ok, "n_sites": int(ok), "sites": []}
                else:
                    row["fixpoint"] = status(h, facts, kind, names)
            else:
                # criteria 4.2: 112 samples with fix entities, current version, descriptive
                per = {}
                for s in samples:
                    re_ = [e for e in s.get("resolved_entities", []) if e.get("current_name")]
                    if not re_:
                        continue
                    best = {"reach": False, "map_reach": False, "in_site": False}
                    for e in re_:
                        k = "function" if e.get("current_kind") == "function" else "macro"
                        r = status(h, facts, k, [e["current_name"]])
                        for x in best:
                            best[x] = best[x] or r[x]
                    per[s["id"]] = best
                row["samples"] = {"evaluable": len(per), **{x: sum(1 for v in per.values() if v[x])
                                                             for x in ("reach", "map_reach", "in_site")}}
                ents[cname] = per
            ablation[g][cname] = row
            if cname == "all":
                (HERE / "gen").mkdir(exist_ok=True)
                keep = {k: h[k] for k in ("config", "depth", "entries", "sites", "raw_nr", "T", "stats", "NR_syscalls")}
                (HERE / "gen" / f"hints_{g}.json").write_text(json.dumps(keep, indent=0))
            print(g, cname, json.dumps({k: row[k] for k in ("sites", "T", "reach_map")}),
                  json.dumps(row.get("fixpoint") or row.get("samples")), flush=True)
    (HERE / "ablation.json").write_text(json.dumps(ablation, indent=1))
    (HERE / "baseline_check.json").write_text(json.dumps(bcheck, indent=1))
    (HERE / "sample_entities.json").write_text(json.dumps(ents, indent=0))
    print("BASELINE", json.dumps(bcheck))


if __name__ == "__main__":
    main()
