"""Compare new-executor results with rankprune run1 on the same kernels (old tokens only), excluding cases unstable
in rankprune.   regress_check.py <new log dir> <rankprune runs/A171 dir>"""
import gzip, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse_log import parse_log
KMSG = re.compile(r"(?<=[^\n])\[\s*\d+\.\d+\][^\n]*\n")
W, R = Path(sys.argv[1]), Path(sys.argv[2])
unstable = set(json.loads((R / "compare.json").read_text())["unstable"])
tot = {"compared": 0, "equal": 0, "diff": 0}
for k in ("a171_pre", "a171_fix", "a171_ref_arm64", "a171_ref_x86_64"):
    new = parse_log(KMSG.sub("", (W / f"{k}.log").read_bytes().replace(b"\0", b"").decode("utf-8", "replace")))
    old = parse_log(KMSG.sub("", gzip.open(R / f"{k}.run1.log.gz").read().replace(b"\0", b"").decode("utf-8", "replace")))
    diffs = [c for c in old["cases"] if c not in unstable and new["cases"].get(c) != old["cases"][c]]
    n = sum(1 for c in old["cases"] if c not in unstable)
    tot["compared"] += n; tot["diff"] += len(diffs); tot["equal"] += n - len(diffs)
    print(k, "complete", new["complete"], "compared", n, "diff", len(diffs), [(c, old["cases"][c], new["cases"].get(c)) for c in diffs[:5]])
print("REGRESSION", "PASS" if tot["diff"] == 0 else "FAIL", tot)
