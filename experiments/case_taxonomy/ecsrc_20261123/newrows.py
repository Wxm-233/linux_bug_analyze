"""ecsrc criteria 四 G4: df rows of this round not in ecpud's 22 (r7/df/df.json), with their deviations."""
import json
from pathlib import Path
old = json.loads(Path("/root/work/ec_cache/r7/df/df.json").read_text(encoding="utf-8"))["cands"]
new = json.loads(Path("/root/work/ec_cache/r8/df/df.json").read_text(encoding="utf-8"))["cands"]
key = lambda c: (c["arch"], c["func"], c["class"])
ok = {key(c) for c in old}
add = [c for c in new if key(c) not in ok]
gone = [c for c in old if key(c) not in {key(x) for x in new}]
print("old", len(old), "new", len(new), "added", len(add), "gone", len(gone))
for c in add:
    print(json.dumps({k: c[k] for k in c if k not in ("devs",)}, ensure_ascii=False)[:900])
Path(__file__).resolve().parent.joinpath("results", "new_rows.json").write_text(json.dumps({"added": add, "gone": gone}, indent=1, ensure_ascii=False), encoding="utf-8")
