"""ecnoise criteria 三 G2: whole-version scan = scan3's 8 frozen engines + round-3 EC. WSL.

    python3 scan5.py scan <rev> [N]     -> run missing jobs (8 old engines via scan3, then ec3.py engine), then table
    python3 scan5.py table <rev>        -> tables/<rev12>.{csv,json,md} in this directory
    python3 scan5.py verify             -> the 8 old engines' counts on df2908090cda equal scan3's
Reuses ecscan_20261122/scan4.py (imported, not modified) with the EC cache pointed at /root/work/ec_cache/r3 and tables written here.
"""
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "ecscan_20261122"))
import scan4 as S4  # noqa: E402

S4.EC_CACHE = Path("/root/work/ec_cache/r3")
S4.HERE = HERE
S3, M = S4.S3, S4.M


def scan(rev, n=8):
    S3.check_frozen()
    rev = M.full(rev)
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
        subprocess.run([sys.executable, str(HERE / "ec3.py"), "engine", rev], stdout=out, stderr=subprocess.STDOUT)
    return S4.table(rev)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "scan":
        scan(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 8)
    elif cmd == "table":
        S4.table(sys.argv[2])
    elif cmd == "verify":
        S4.verify()
