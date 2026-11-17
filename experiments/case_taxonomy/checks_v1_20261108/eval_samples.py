"""Run the context check on the current version and on the 6 samples before/after their fix (criteria section 5).

    python3 eval_samples.py [--only NAME ...]

For every target: export the source with `git archive` (the kernel repository is not touched), build it with
build_cfg.sh, extract the IR, analyse, and save results/<target>.json. Samples are then scored into sample_eval.json.
Steps already done are skipped, so the script can be rerun after an interruption.
"""
import argparse
import json
import re
import subprocess
import sys
import gzip
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
KSRC = "/root/repos/linux"
WORK = Path("/root/work/checks_v1")
RESULTS = HERE / "results"
SAMPLES = [  # id, fix commit, extra configs, kinds that count (criteria section 5)
    ("A076", "fb1cf0878328", ["DEBUG_PAGEALLOC"], {"S"}),
    ("A118", "6a97f4118ac0", [], {"R", "S"}),
    ("A122", "b3431a8bb336", ["KFENCE"], {"I"}),
    ("A158", "61a74ad25462", [], {"S"}),
    ("A175", "969f028bf2c4", [], {"R", "S"}),
    ("A344", "453805f0a28f", [], {"S"}),
]


def sh(*cmd, **kw):
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, check=True, **kw)


def export(rev, dest):
    if (dest / "Makefile").exists():
        return
    dest.mkdir(parents=True, exist_ok=True)
    archive = subprocess.Popen(["git", "-C", KSRC, "archive", rev], stdout=subprocess.PIPE)
    subprocess.run(["tar", "-x", "-C", str(dest)], stdin=archive.stdout, check=True)
    if archive.wait() != 0:
        raise SystemExit(f"git archive {rev} failed")


def run_target(name, src, extras):
    out = WORK / "build" / name
    cache = WORK / "cache" / name
    result = RESULTS / f"{name}.json"
    if result.exists():
        return json.loads(result.read_text())
    sh("bash", str(HERE / "build_cfg.sh"), str(src), str(out), *extras)
    if not (cache / "extract_done.json").exists():
        sh(sys.executable, "-B", str(HERE / "ctx_extract.py"), str(out), str(cache), "--jobs", "12", "--source", str(src))
    counts = json.loads((cache / "extract_done.json").read_text())["counts"]
    if "cached" in counts and set(counts) <= {"ok", "cached"}:
        # amendment 3, item 8: a resumed extraction reports earlier units as "cached"; recheck their stored status
        counts = defaultdict(int)
        for p in (cache / "units").glob("*.json.gz"):
            with gzip.open(p, "rt", encoding="utf-8") as fh:
                d = json.load(fh)
            counts["error" if "error" in d else ("fatal" if d.get("fatal") else "ok")] += 1
        counts = dict(counts)
    if set(counts) != {"ok"}:  # amendment 2, item 4: a fatal or failed unit stops the evaluation
        raise SystemExit(f"{name}: units not all parsed cleanly: {counts}")
    RESULTS.mkdir(exist_ok=True)
    sh(sys.executable, "-B", str(HERE / "ctx_analyze.py"), str(cache), str(Path(src) / "arch/riscv/kernel/entry.S"),
       str(result))
    return json.loads(result.read_text())


def changed(commit):
    """{file: (old_lines, new_lines)} from the fix diff; a pure insertion marks its anchor line."""
    diff = subprocess.run(["git", "-C", KSRC, "diff", "-U0", f"{commit}^", commit], capture_output=True, text=True,
                          check=True).stdout
    out, f = {}, None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            f = line[6:] if line.startswith("+++ b/") else None
            if f:
                out.setdefault(f, (set(), set()))
        m = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
        if m and f:
            os_, ol, ns, nl = int(m[1]), int(m[2] or 1), int(m[3]), int(m[4] or 1)
            out[f][0].update(range(os_, os_ + max(ol, 1)))
            out[f][1].update(range(ns, ns + max(nl, 1)))
    return out


def functions_hit(cache, lines_by_file, side):
    names = set()
    for p in (cache / "units").glob("*.json.gz"):
        with gzip.open(p, "rt", encoding="utf-8") as fh:
            d = json.load(fh)
        for fn in d.get("functions", []):
            lines = lines_by_file.get(fn["file"])
            if lines and any(fn["line"] <= x <= fn.get("end", fn["line"]) for x in lines[side]):
                names.add(fn["name"])
    return names


def score(sid, commit, kinds, pre, fix):
    lines = changed(commit)
    pre_fns = functions_hit(WORK / "cache" / f"{sid}_pre", lines, 0)
    fix_fns = functions_hit(WORK / "cache" / f"{sid}_fix", lines, 1)

    def related(fl, fns):
        names = {fl["caller"], fl["callee"], *fl.get("witness", [])} | {c[0] for c in fl.get("origin_chain", [])}
        return bool(names & fns)

    hits = [fl for fl in pre["flags"] if fl["kind"] in kinds and related(fl, pre_fns)]
    keys = {(fl["kind"], fl["caller"], fl["callee"]) for fl in hits}
    still = [fl for fl in fix["flags"] if (fl["kind"], fl["caller"], fl["callee"]) in keys]
    return {"id": sid, "commit": commit, "kinds": sorted(kinds), "fix_functions_pre": sorted(pre_fns),
            "fix_functions_fix": sorted(fix_fns), "hit": bool(hits), "hit_flags": hits,
            "same_flags_after_fix": still, "pre_summary": pre["summary"], "fix_summary": fix["summary"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    want = lambda n: not a.only or n in a.only
    if want("current"):
        run_target("current", KSRC, [])
    evals = []
    for sid, commit, extras, kinds in SAMPLES:
        if not want(sid):
            continue
        pre_src, fix_src = WORK / "src" / f"{sid}_pre", WORK / "src" / f"{sid}_fix"
        export(f"{commit}^", pre_src)
        export(commit, fix_src)
        pre = run_target(f"{sid}_pre", pre_src, extras)
        fix = run_target(f"{sid}_fix", fix_src, extras)
        evals.append(score(sid, commit, kinds, pre, fix))
        (HERE / "sample_eval.json").write_text(json.dumps(evals, ensure_ascii=False, indent=1))
        print(sid, "hit" if evals[-1]["hit"] else "miss", flush=True)


if __name__ == "__main__":
    main()
