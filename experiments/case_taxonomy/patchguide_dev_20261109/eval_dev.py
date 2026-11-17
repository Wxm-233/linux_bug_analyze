"""Run patch-guided detection on the dev set and on the current version (criteria sections 2-4).

    python3 eval_dev.py <iteration tag> [--only ID ...] [--no-current]

Outputs go to runs/<tag>/: samples.json (per sample), flags_current.json, summary.json.
"""
import argparse
import gzip
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
C2 = HERE.parent / "checks2_xarch_20261109"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(C2))
import mine_patches  # noqa: E402
import pguide  # noqa: E402
import xcmp  # noqa: E402
from eval_samples import POOLS, WORK, CUR  # noqa: E402

KSRC = "/root/repos/linux"
LABELS = HERE.parent / "boundary_taxonomy_20261106" / "labels.json"
SM = HERE.parent / "boundary_closure_20261108" / "sample_match_v2.json"
PATCHES = Path("/root/work/pgdev/patches_x86_arm64.json.gz")
C2IDS = ["A025", "A026", "A039", "A043", "A085", "A112", "A143", "A155", "A196", "A215", "A225", "A247", "A274",
         "A288", "A310", "A336", "A368", "A380", "A387", "A392", "A393", "A398", "B467", "B485"]


def dev_set(labels):
    return [r for r in labels if r["check"] in (1, 2, 3) and (r["mechanism"] in ("M8", "M10") or r["id"] in C2IDS)]


def git1(*args):
    return subprocess.run(["git", "-C", KSRC, *args], capture_output=True, text=True, check=True).stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tag")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--no-current", action="store_true")
    ap.add_argument("--diag-ext", action="store_true", help="iteration option, see iterations.md")
    ap.add_argument("--riscv-available", action="store_true", help="iteration option, see iterations.md")
    ap.add_argument("--reach-depth", type=int, default=pguide.DEPTH, help="iteration option, see iterations.md")
    a = ap.parse_args()
    out = HERE / "runs" / a.tag
    out.mkdir(parents=True, exist_ok=True)
    opts = {"diag_ext": a.diag_ext, "riscv_available": a.riscv_available, "reach_depth": a.reach_depth}
    (out / "opts.json").write_text(json.dumps(opts))
    labels = json.loads(LABELS.read_text())
    ents = {s["id"]: s["entities"] for s in json.loads(SM.read_text())["samples"]}
    with gzip.open(PATCHES, "rt") as fh:
        patches = json.load(fh)["commits"]
    cands, _ = xcmp.candidates_from_pools(POOLS)
    counters = {t: xcmp.load(str(CUR / f"facts_{t}.json.gz")) for t in ("x86", "arm64")}
    revmaps = {t: pguide.counter_reach(xcmp.Build(f), t, cands, a.reach_depth) for t, f in counters.items()}
    res = []
    for r in dev_set(labels):
        sid = r["id"]
        if a.only and sid not in a.only:
            continue
        fixfns = sorted({e["name"] for e in ents.get(sid, []) if e["kind"] == "function"})
        facts = WORK / "facts" / sid / "facts_riscv.json.gz"
        row = {"id": sid, "check": r["check"], "class": r["class"], "mechanism": r["mechanism"], "fix_functions": fixfns}
        if not fixfns:
            row["status"] = "no_function"
        elif not facts.exists():
            row["status"] = "no_facts"
        else:
            commit = r["commit"]
            cutoff = int(git1("log", "-1", "--format=%at", commit))
            rf = xcmp.load(str(facts))
            flags, summ = pguide.run(rf, KSRC, f"{commit}^", counters, cands, patches, cutoff, revmaps, opts)
            rb = xcmp.Build(rf)
            files = git1("diff", "--name-only", f"{commit}^", commit).split()
            fix_el = {"call": set(), "field": set(), "errno": set()}
            for h in mine_patches.hunk_elements(KSRC, commit, [f for f in files if f.endswith((".c", ".h"))]):
                if h["func"] in fixfns:
                    for k, v in h["added"].items():
                        fix_el[k] |= set(v)
            loose = [f for f in flags if pguide.reaches(rb, f["target"], fixfns)]
            precise = [f for f in loose if f["element"] in fix_el[f["kind"]]]
            row.update({"status": "ok", "cutoff": cutoff, "summary": summ, "loose_hit": bool(loose),
                        "precise_hit": bool(precise), "loose_flags": loose, "precise_flags": precise,
                        "fix_elements": {k: sorted(v) for k, v in fix_el.items()}})
        res.append(row)
        print(sid, row["status"], "loose" if row.get("loose_hit") else "-", "precise" if row.get("precise_hit") else "-",
              row.get("summary", {}).get("distinct_flags", ""), flush=True)
    (out / "samples.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    summary = {"tag": a.tag, "opts": opts, "dev_samples": len(res), "no_function": sum(r["status"] == "no_function" for r in res),
               "no_facts": sum(r["status"] == "no_facts" for r in res)}
    ok = [r for r in res if r["status"] == "ok"]
    summary.update({"evaluated": len(ok), "loose_hits": sum(r["loose_hit"] for r in ok),
                    "precise_hits": sum(r["precise_hit"] for r in ok),
                    "loose_ids": [r["id"] for r in ok if r["loose_hit"]], "precise_ids": [r["id"] for r in ok if r["precise_hit"]]})
    if not a.no_current:
        rf = xcmp.load(str(CUR / "facts_riscv.json.gz"))
        flags, summ = pguide.run(rf, KSRC, "HEAD", counters, cands, patches, None, revmaps, opts)
        (out / "flags_current.json").write_text(json.dumps({"summary": summ, "flags": flags}, ensure_ascii=False, indent=1))
        summary["current"] = summ
        summary["current_by_kind"] = {k: sum(1 for f in flags if f["kind"] == k) for k in ("call", "field", "errno")}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
