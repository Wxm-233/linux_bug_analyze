"""Pre-fix riscv facts for the 18 dev samples that do not have them yet (criteria section 2).

    python3 build_dev.py [--only ID ...]

Same method as checks2_xarch_20261109 section 5 (git archive of the fix's parent, partial build of the scope
directories plus the fix directories, extended archbound collect, reduce). Facts go to /root/work/checks2/facts/<id>/;
the source tree is removed afterwards, the build directory is kept without object files.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
C2 = HERE.parent / "checks2_xarch_20261109"
sys.path.insert(0, str(C2))
from eval_samples import export, fix_dirs, prune_build, SCOPE, WORK  # noqa: E402

LABELS = HERE.parent / "boundary_taxonomy_20261106" / "labels.json"
NEED = "A013 A032 A086 A091 A101 A142 A190 A191 A202 A211 A243 A254 A299 A301 A313 A359 A379 B506".split()
EXTRA = {"A086": ["BPF_SYSCALL", "BPF_JIT"], "A211": ["BPF_SYSCALL", "BPF_JIT"], "A301": ["BPF_SYSCALL", "BPF_JIT"],
         "A190": ["KEXEC_FILE"], "A191": ["KEXEC_FILE"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    labels = {r["id"]: r for r in json.loads(LABELS.read_text())}
    status = {}
    for sid in NEED:
        if a.only and sid not in a.only:
            continue
        commit = labels[sid]["commit"]
        src, out, fdir = WORK / "src" / sid, WORK / "build" / sid, WORK / "facts" / sid
        if (fdir / "facts_riscv.json.gz").exists():
            status[sid] = "already"
            print(sid, "already", flush=True)
            continue
        extra = fix_dirs(commit)
        export(f"{commit}^", src)
        b = subprocess.run(["bash", str(C2 / "build_partial.sh"), str(src), str(out), SCOPE + " " + " ".join(extra),
                            *EXTRA.get(sid, [])])
        if b.returncode != 0:
            tail = (out / "failed.txt").read_text() if (out / "failed.txt").exists() else ""
            status[sid] = {"build_failed": b.returncode, "tail": tail[-2000:]}
            print(sid, "build_failed", flush=True)
            continue
        c = subprocess.run(["bash", str(C2 / "collect_build.sh"), "riscv", str(out), "riscv", str(fdir), str(src), *extra])
        status[sid] = "ok" if c.returncode == 0 and (fdir / "facts_riscv.json.gz").exists() else {"collect_failed": c.returncode}
        print(sid, status[sid] if isinstance(status[sid], str) else "collect_failed", flush=True)
        if status[sid] == "ok":
            shutil.rmtree(src, ignore_errors=True)
            prune_build(out)
    prev = json.loads((HERE / "build_dev_status.json").read_text()) if (HERE / "build_dev_status.json").exists() else {}
    prev.update(status)
    (HERE / "build_dev_status.json").write_text(json.dumps(prev, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
