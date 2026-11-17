"""Select base cases from the calibration run (mutate criteria 二). Runs in WSL.

    python3 bases.py /root/work/mutate/calib -> bases.json {sc: {"kind": ok|deep|default, "bases": [case...]}}
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "casemodel_dev_20261110" / "harness"))
from parse_log import parse_log  # noqa: E402
sys.path.insert(0, str(HERE))
import mutate_lib as ML  # noqa: E402

KMSG = re.compile(r"(?<=[^\n])\[\s*\d+\.\d+\][^\n]*\n")


def main():
    W = Path(sys.argv[1])
    res = {}
    for a in ML.ARCHS:
        text = KMSG.sub("", (W / f"{a}.log").read_bytes().replace(b"\0", b"").decode("utf-8", "replace"))
        p = parse_log(text)
        assert p["complete"], a
        res[a] = p["cases"]
    meta = json.loads((HERE / "cases_calib.json").read_text())
    by = {}
    for c in meta["cases"]:
        by.setdefault(c["sc"], []).append(c)
    out, st = {}, {"ok": 0, "deep": 0, "default": 0}
    for sc, cs in by.items():
        cs.sort(key=lambda c: c["cand"])
        rs = {c["id"]: [res[a].get(str(c["id"]), ["missing"])[0] for a in ML.ARCHS] for c in cs}
        ok = [c for c in cs if sum(ML.is_ok(r) for r in rs[c["id"]]) >= 2]
        if ok:
            kind, chosen = "ok", ok[:2]
        else:
            deep = []
            for c in cs:
                r = rs[c["id"]]
                for e in set(r):
                    if r.count(e) >= 2 and e.startswith("E") and e not in ML.SHALLOW:
                        deep.append(c)
                        break
            kind, chosen = ("deep", deep[:1]) if deep else ("default", cs[:1])
        st[kind] += 1
        out[sc] = {"kind": kind, "results": [rs[c["id"]] for c in chosen],
                   "bases": [{k: v for k, v in c.items() if k not in ("id", "cand")} | {"cand": c["cand"]}
                             for c in chosen]}
    (HERE / "bases.json").write_text(json.dumps({"stats": st, "bases": out}, indent=0))
    print(st)
    for sc in ("mmap", "recvmsg", "perf_event_open", "futex", "sendmsg", "mremap", "brk"):
        if sc in out:
            print(sc, out[sc]["kind"], out[sc]["results"], [b["args"] for b in out[sc]["bases"]])


if __name__ == "__main__":
    main()
