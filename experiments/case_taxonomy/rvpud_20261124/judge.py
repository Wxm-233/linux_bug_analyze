"""rvpud criteria 三/五: python3 judge.py <tag>  -> runs/<tag>/judge.json and a printed table"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
P_RE = re.compile(r"vfio_pci_mmap_huge_fault\(,order = 18\) BAR 2 page offset 0x[0-9a-f]+: 0x100\b")


def one(log):
    s = log.read_text(errors="replace")
    return {"P": bool(P_RE.search(s)), "end": "@@END 0" in s, "bad_pud": len(re.findall(r"bad pud", s)),
            "oops": bool(re.search(r"Oops|Kernel panic|BUG:|Unable to handle", s)),
            "lines": [l for l in s.splitlines() if l.startswith("@@") or "bad pud" in l or "order = 18" in l][:40]}


def main(tag):
    d = HERE / "runs" / tag
    res = {}
    for log in sorted(d.glob("*.run*.log")):
        name = log.name.split(".run")[0]
        res.setdefault(name, []).append(dict(one(log), run=log.name))
    out = {}
    for name, rs in res.items():
        ev = [r for r in rs if r["P"]]
        out[name] = {"runs": len(rs), "evaluable": len(ev), "bad_pud_runs": sum(1 for r in ev if r["bad_pud"]),
                     "oops_runs": sum(1 for r in rs if r["oops"]), "ended": sum(1 for r in rs if r["end"])}
        print(f"{name:12s} runs {len(rs)} evaluable {len(ev)} bad_pud {out[name]['bad_pud_runs']} "
              f"oops {out[name]['oops_runs']} ended {out[name]['ended']}")
    g = lambda n: out.get(n, {"runs": 0, "evaluable": 0, "bad_pud_runs": 0})
    t1, t2, t3 = g("T1_orig_A"), g("T2_orig_C"), g("T3_fix_A")
    if t1["evaluable"] == 3 == t1["bad_pud_runs"] and t2["evaluable"] == 3 and not t2["bad_pud_runs"] \
            and t3["evaluable"] == 3 and not t3["bad_pud_runs"]:
        verdict = "复现"
    elif t1["evaluable"] == 3 and not t1["bad_pud_runs"]:
        verdict = "不复现"
    else:
        verdict = "其他（见各项）"
    print("VERDICT", verdict)
    json.dump({"summary": out, "verdict": verdict, "detail": res}, open(d / "judge.json", "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
