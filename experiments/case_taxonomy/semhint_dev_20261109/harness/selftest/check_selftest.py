"""Compare the three self-test logs case by case (Claude)."""
import json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
W = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE
exp = json.loads((HERE / "selftest_expect.json").read_text(encoding="utf-8"))
res, dbg = {}, {}
for a in ("riscv", "arm64", "x86_64"):
    res[a] = json.loads((W / f"{a}.json").read_text())
    dbg[a] = {}
    for line in (W / f"{a}.log").read_bytes().decode("utf-8", "replace").splitlines():
        if line.startswith('{"selftest":'):
            d = json.loads(line); dbg[a][d["selftest"]] = d
        if line.startswith('{"selftest_summary"'):
            print(a, line.strip())
    print(a, "complete", res[a]["complete"], "taint_changed", res[a]["taint_changed"], "harness_errors", res[a].get("harness_errors"))
for cid in sorted(exp, key=int):
    row = [res[a]["cases"].get(cid) for a in ("riscv", "arm64", "x86_64")]
    g = [ (dbg[a].get(int(cid)) or {}).get("graph") for a in ("riscv", "arm64", "x86_64")]
    ph = [ (dbg[a].get(int(cid)) or {}).get("pool_hash") for a in ("riscv", "arm64", "x86_64")]
    chk = [ ((dbg[a].get(int(cid)) or {}).get("fd_checks"), (dbg[a].get(int(cid)) or {}).get("memory_checks"), (dbg[a].get(int(cid)) or {}).get("graph_ok")) for a in ("riscv", "arm64", "x86_64")]
    ms = [round((dbg[a].get(int(cid)) or {}).get("elapsed_ms", 0), 1) for a in ("riscv", "arm64", "x86_64")]
    print(cid, exp[cid], "|", [r[:2] + [r[2]] if r else None for r in row], "graph_same" if len({json.dumps(x) for x in g}) == 1 else "GRAPH_DIFF", "pool_same" if len(set(ph)) == 1 else "POOL_DIFF", chk[0], ms)
