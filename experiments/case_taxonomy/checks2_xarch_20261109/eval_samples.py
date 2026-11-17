"""Evaluate check 2 on the 24 evaluable samples' pre-fix riscv code (criteria section 5).

    python3 eval_samples.py [--only ID ...] [--keep]

For every sample: git archive the fix's parent (the kernel repository is not touched), partial riscv build
(build_partial.sh), collect + reduce (collect_build.sh), compare with the current x86_64 / arm64 facts, score.
The sample's source and build trees are deleted afterwards unless --keep (only the reduced facts are kept).
Steps already done are skipped, so the script can be rerun after an interruption.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import xcmp  # noqa: E402

KSRC = "/root/repos/linux"
WORK = Path("/root/work/checks2")
CUR = WORK / "current"
SM = HERE.parent / "boundary_closure_20261108" / "sample_match_v2.json"
LABELS = HERE.parent / "boundary_taxonomy_20261106" / "labels.json"
POOLS = [str(p) for p in sorted((HERE.parent / "boundary_audit_20261107" / "revised").glob("*/*/symbols_runtime_*.json"))]
SCOPE = ("arch/riscv/ kernel/ mm/ lib/ init/ drivers/irqchip/ drivers/perf/ drivers/acpi/ drivers/clocksource/ "
         "drivers/iommu/ drivers/cpuidle/ drivers/firmware/")
EVALUABLE = ["A025", "A026", "A039", "A043", "A085", "A112", "A143", "A155", "A196", "A215", "A225", "A247",
             "A274", "A288", "A310", "A336", "A368", "A380", "A387", "A392", "A393", "A398", "B467", "B485"]
EXTRA_CONFIGS = {"A039": ["BPF_SYSCALL", "BPF_JIT"], "A196": ["KPROBES"], "A392": ["KEXEC_FILE"], "A393": ["KEXEC"]}
CLASS_TYPES = {"Q1": {"stub"}, "Q2": {"write-missing", "call-missing"}, "Q3": {"call-missing", "arg-diff"},
               "Q4": {"errno-diff"}, "P1": {"param-check"}}


def sh(*cmd, **kw):
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, **kw)


def fix_dirs(commit):
    files = subprocess.run(["git", "-C", KSRC, "diff", "--name-only", f"{commit}^", commit], capture_output=True,
                           text=True, check=True).stdout.split()
    dirs = {str(Path(f).parent) + "/" for f in files if f.endswith(".c")}
    # amendment 2: a directory already inside a scope directory is not passed again as its own make target
    # (overlapping targets race in a parallel build: A196's arch/riscv/kernel/probes/ next to arch/riscv/)
    return sorted(d for d in dirs if not d.startswith(tuple(SCOPE.split())))


def export(rev, dest):
    if (dest / "Makefile").exists():
        return
    dest.mkdir(parents=True, exist_ok=True)
    archive = subprocess.Popen(["git", "-C", KSRC, "archive", rev], stdout=subprocess.PIPE)
    subprocess.run(["tar", "-x", "-C", str(dest)], stdin=archive.stdout, check=True)
    if archive.wait() != 0:
        raise SystemExit(f"git archive {rev} failed")


def current_flags():
    p = HERE / "flags_current.json"
    return json.loads(p.read_text())["flags"] if p.exists() else None


def run_sample(sid, commit, cls, entities, counters, cur, keep):
    res_path = HERE / "results" / f"{sid}.json"
    if res_path.exists():
        return json.loads(res_path.read_text())
    src, out, fdir = WORK / "src" / sid, WORK / "build" / sid, WORK / "facts" / sid
    facts = fdir / "facts_riscv.json.gz"
    extra = fix_dirs(commit)
    if not facts.exists():
        export(f"{commit}^", src)
        b = sh("bash", str(HERE / "build_partial.sh"), str(src), str(out), SCOPE + " " + " ".join(extra),
               *EXTRA_CONFIGS.get(sid, []))
        if b.returncode != 0:  # criteria section 5: a build failure is recorded, not worked around
            tail = (out / "failed.txt").read_text() if (out / "failed.txt").exists() else ""
            r = {"id": sid, "status": "build_failed", "returncode": b.returncode, "tail": tail[-3000:]}
            res_path.write_text(json.dumps(r, ensure_ascii=False, indent=1))
            return r
        c = sh("bash", str(HERE / "collect_build.sh"), "riscv", str(out), "riscv", str(fdir), str(src), *extra)
        if c.returncode != 0 or not facts.exists():
            raise SystemExit(f"{sid}: collect/reduce failed (see {fdir}/collect_riscv.log)")
    flags, summary = xcmp.compare(xcmp.load(str(facts)), counters, POOLS)
    names = {e["name"] for e in entities if e["kind"] == "function"}
    allowed = CLASS_TYPES[cls]
    hits = [f for f in flags if f["family"] in names and f["type"] in allowed]
    related = [f for f in flags if f["family"] in names]
    cur_keys = {(f["type"], f["family"], f["detail"]) for f in cur} if cur is not None else None
    for f in hits:
        f["still_in_current"] = None if cur_keys is None else (f["type"], f["family"], f["detail"]) in cur_keys
    r = {"id": sid, "status": "ok", "class": cls, "commit": commit, "fix_functions": sorted(names),
         "allowed_types": sorted(allowed), "hit": bool(hits), "hit_flags": hits,
         "flags_on_fix_functions": related, "summary": summary, "extra_dirs": extra,
         "extra_configs": EXTRA_CONFIGS.get(sid, [])}
    res_path.write_text(json.dumps(r, ensure_ascii=False, indent=1))
    if not keep:
        # storage only (no effect on results): the source tree is re-creatable with `git archive`; the build dir is kept
        # without object files, so compile_commands.json, .config and the generated headers stay for re-parsing
        shutil.rmtree(src, ignore_errors=True)
        prune_build(out)
    return r


def prune_build(out):
    for pat in ("*.o", "*.a", "*.ko", "*.mod", "vmlinux*", "*.lto.o"):
        for f in out.rglob(pat):
            if f.is_file():
                f.unlink()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()
    (HERE / "results").mkdir(exist_ok=True)
    labels = {r["id"]: r for r in json.loads(LABELS.read_text())}
    ents = {s["id"]: s["entities"] for s in json.loads(SM.read_text())["samples"]}
    counters = [("x86", xcmp.load(str(CUR / "facts_x86.json.gz"))), ("arm64", xcmp.load(str(CUR / "facts_arm64.json.gz")))]
    cur = current_flags()
    evals = []
    for sid in EVALUABLE:
        if a.only and sid not in a.only:
            continue
        r = run_sample(sid, labels[sid]["commit"], labels[sid]["class"], ents[sid], counters, cur, a.keep)
        evals.append(r)
        print(sid, r["status"], "hit" if r.get("hit") else "miss", flush=True)
    if not a.only:
        (HERE / "sample_eval.json").write_text(json.dumps(evals, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
