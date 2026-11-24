import json, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ec5
import ec3  # noqa
import ec as EC2
d = Path("/root/work/ec_cache/r5/df/df2908090cda")
laws, devs = ec5.rules45(EC2, d)
print("raw rule devs", Counter(x["rule"] for x in devs))
r3 = {(x["key"], x["build"]) for x in json.load(open("/root/work/ec_cache/r3/df2908090cda/deviations.json"))}
print("rule4 overlapping round3", sum((x["key"], x["build"]) in r3 for x in devs if x["rule"] == 4))
for x in devs[:0]: pass
L4 = {k: v for k, v in laws.items() if k.startswith("PTP")}
print("rule4 law majorities", Counter(v["majority"] for v in L4.values()).most_common(6))
print("rule4 laws by n_comparable", Counter(v["n_comparable"] for v in L4.values()).most_common(8))
base = json.load(open("/root/work/ec_cache/r3/df2908090cda368b01ff43709f51890076c56157.json"))["cands"]
bk = {(c["arch"], c["func"], c["class"]) for c in base}
R = json.load(open("/root/work/ec_cache/r5/df/df.json"))["cands"]
for c in R:
    if (c["arch"], c["func"], c["class"]) not in bk:
        print(c["arch"], c["func"], c["class"], c["n"], c["builds"], c["example"])
