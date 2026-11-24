"""ecarm64 criteria 四 G5: whole-version scan = scan3's 8 frozen engines + this round's EC (ec10.py df). WSL.

    python3 scan11.py table <rev>   -> tables/<rev12>.{csv,json,md}; the EC part is /root/work/ec_cache/r10/<full>.json (copied from r9/df/df.json)
    python3 scan11.py verify        -> the 8 old engines' counts on df2908090cda equal scan3's
Reuses ecscan_20261122/scan4.py (imported, not modified).
"""
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "ecscan_20261122"))
import scan4 as S4  # noqa: E402

R10 = Path("/root/work/ec_cache/r10")
S4.EC_CACHE = R10
S4.HERE = HERE
S3, M = S4.S3, S4.M

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "table":
        full = M.full(sys.argv[2])
        if not (R10 / f"{full}.json").exists():
            shutil.copy(R10 / "df" / "df.json", R10 / f"{full}.json")
        S4.table(sys.argv[2])
    elif cmd == "verify":
        S4.verify()
