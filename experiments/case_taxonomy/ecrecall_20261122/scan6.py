"""ecrecall criteria 三.2: whole-version scan on any revision = scan3's 8 frozen engines + the frozen round-3 EC through ec4.py
(variants from mkvariants.sh). WSL.

    python3 scan6.py scan <rev> [N]   -> run missing jobs of the 8 engines (scan3's job list), EC via ec4.py engine, then the table
    python3 scan6.py table <rev>      -> tables/<rev12>.{csv,json,md} in this directory
"""
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "ecscan_20261122"))
import scan4 as S4  # noqa: E402

S4.HERE = HERE
S3, M = S4.S3, S4.M
VCACHE = Path("/root/work/ec_cache/v")


def point(rev):
    S4.EC_CACHE = VCACHE / M.full(rev)[:12]


def scan(rev, n=8):
    S3.check_frozen()
    rev = M.full(rev)
    point(rev)
    todo = [j for j in S3.rev_jobs(rev) if S3.cache_state(j[2]) not in ("ok", "error")]
    running = []
    out = open(HERE / "engines_output.log", "a")
    while todo or running:
        running = [(j, pr) for j, pr in running if pr.poll() is None]
        while todo and len(running) < n:
            j = todo.pop(0)
            running.append((j, subprocess.Popen([sys.executable, *j[3]], stdout=out, stderr=subprocess.STDOUT)))
        time.sleep(3)
    if S4.ec_rows(rev)[1] in ("todo", "broken"):
        subprocess.run([sys.executable, str(HERE / "ec4.py"), "engine", rev], stdout=out, stderr=subprocess.STDOUT)
    return S4.table(rev)


if __name__ == "__main__":
    if sys.argv[1] == "scan":
        scan(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 8)
    elif sys.argv[1] == "table":
        point(sys.argv[2])
        S4.table(sys.argv[2])
