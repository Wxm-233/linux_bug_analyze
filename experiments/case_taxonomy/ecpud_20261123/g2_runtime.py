"""ecpud criteria 四 G2 (substitute measure): runtime predicates per build, round 3 df vs this round's df. Change 3 can only act where a
predicate was met; a predicate folded to a constant disappears from the list."""
import json
from pathlib import Path
old = Path("/root/work/ec_cache/r3/df2908090cda"); new = Path("/root/work/ec_cache/v7/df2908090cda/df2908090cda")
out = {}
for f in sorted(new.glob("beh_*.json")):
    b = f.stem[4:]
    n = json.loads(f.read_text()).get("runtime")
    o = json.loads((old / f.name).read_text()).get("runtime") if (old / f.name).exists() else "new build"
    out[b] = {"r3": o, "now": n}
    print(f"{b:13s} r3 {o}  now {n}")
Path(__file__).resolve().parent.joinpath("results", "g2_runtime_df.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
