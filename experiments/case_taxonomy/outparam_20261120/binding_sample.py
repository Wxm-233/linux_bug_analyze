"""outparam criteria 六.1: sample 12 distinct interfaces among 'differ' units; print keys only (no bindings). WSL.

    python3 binding_sample.py sample   -> binding_sample.json (keys only)
    python3 binding_sample.py check    -> binding_check.csv (after binding_expect.json is written and hashed)
"""
import csv
import gzip
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = Path("/root/work/outparam")


def diff_rows():
    with gzip.open(WORK / "scope.csv.gz", "rt", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r["status"] == "双侧可绑定且不同"]


def sample(seed=20261120, outname="binding_sample.json", exclude=()):
    rows = diff_rows()
    ifaces = sorted({r["callee"] for r in rows} - set(exclude))
    rnd = random.Random(seed)
    pick = rnd.sample(ifaces, 12)
    out = []
    for name in pick:
        us = sorted((r for r in rows if r["callee"] == name), key=lambda r: (r["caller_file"], int(r["line"])))
        u = rnd.choice(us)
        out.append({"callee": name, "caller_file": u["caller_file"], "caller_func": u["caller_func"], "line": int(u["line"]),
                    "builds": sorted(json.loads(u["bindings"]).keys())})
    (HERE / outname).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    for x in out:
        print(x)


def check(expname="binding_expect.json", outname="binding_check.csv"):
    exp = json.loads((HERE / expname).read_text(encoding="utf-8"))
    rows = {(r["caller_file"], r["caller_func"], int(r["line"]), r["callee"]): json.loads(r["bindings"]) for r in diff_rows()}
    out, ok_all = [], True
    for e in exp:
        got = rows.get((e["caller_file"], e["caller_func"], e["line"], e["callee"]))
        if got is None:
            out.append([e["callee"], "-", "unit no longer 'differ'", "-", "n/a"])
            continue
        for b, want in e["expect"].items():
            g = got.get(b)
            gl = f"{g[1]}:{g[2]}" if g and g[0] == "bound" else (g[0] if g else "none")
            ok = (gl == want) or (want.endswith(":*") and gl.split(":")[0] == want[:-2])
            ok_all &= ok
            out.append([e["callee"], b, want, gl, ok])
    with open(HERE / outname, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["callee", "build", "expected", "got", "ok"])
        w.writerows(out)
    for r in out:
        print(r)
    n = [r for r in out if r[4] != "n/a"]
    print("ALL CORRECT" if ok_all else "MISMATCH", sum(r[4] is True for r in n), "/", len(n), "| dropped units:", len(out) - len(n))


if __name__ == "__main__":
    if sys.argv[1] == "sample":
        sample()
    elif sys.argv[1] == "sample2":  # amendment 1: fresh sample, excluding the first 12 interfaces
        first = [x["callee"] for x in json.loads((HERE / "binding_sample.json").read_text(encoding="utf-8"))]
        sample(20261121, "binding_sample2.json", first)
    elif sys.argv[1] == "check":
        check()
    elif sys.argv[1] == "check2":
        check("binding_expect2.json", "binding_check2.csv")
