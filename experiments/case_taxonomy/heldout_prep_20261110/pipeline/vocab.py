"""C2 value vocabulary per group (casemodel criteria C2). Runs in WSL.
    TARGET=<目标> python3 vocab.py <group> --facts <facts.json.gz> --values <values.json> --out <vocab.json>"""
import gzip, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from hints4 import run  # noqa: E402
from cli import parse
args = parse('vocab')
g = args.group
tag = "CUR" if g == "CUR" else f"{g}_pre"
facts = json.load(gzip.open(args.facts, "rt"))
vals = json.loads(Path(args.values).read_text())
h = run(facts, vals, {"I1", "I2", "I3", "I4"})
v = h["vocab"]
st = {"syscalls": len(v), "params": sum(len(x) for x in v.values()),
      "eq_values": sum(len(p["eq"]) for x in v.values() for p in x.values()),
      "bits": sum(len(p["bits"]) for x in v.values() for p in x.values())}
out_path = Path(args.out)
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps({"group": g, "stats": st, "vocab": v}))
print(g, "vocab", st, "futex", {k: (len(p["eq"]), len(p["bits"])) for k, p in v.get("futex", {}).items()},
      "mmap", {k: (len(p["eq"]), len(p["bits"])) for k, p in v.get("mmap", {}).items()})
