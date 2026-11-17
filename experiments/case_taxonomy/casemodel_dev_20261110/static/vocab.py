"""C2 value vocabulary per group (casemodel criteria C2). Runs in WSL.
    python3 vocab.py <group>  -> ../gen/vocab_<group>.json"""
import gzip, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from hints4 import run  # noqa: E402
g = sys.argv[1]
tag = "CUR" if g == "CUR" else f"{g}_pre"
facts = json.load(gzip.open(f"/root/work/casemodel/facts/{tag}.json.gz", "rt"))
vals = json.loads(Path(f"/root/work/static2/values/{g}.json").read_text())
h = run(facts, vals, {"I1", "I2", "I3", "I4"})
v = h["vocab"]
st = {"syscalls": len(v), "params": sum(len(x) for x in v.values()),
      "eq_values": sum(len(p["eq"]) for x in v.values() for p in x.values()),
      "bits": sum(len(p["bits"]) for x in v.values() for p in x.values())}
(HERE.parent / "gen" / f"vocab_{g}.json").write_text(json.dumps({"group": g, "stats": st, "vocab": v}))
print(g, "vocab", st, "futex", {k: (len(p["eq"]), len(p["bits"])) for k, p in v.get("futex", {}).items()},
      "mmap", {k: (len(p["eq"]), len(p["bits"])) for k, p in v.get("mmap", {}).items()})
