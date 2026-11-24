"""rvpud criteria2 三/四: python3 judge2.py <tag> -> runs/<tag>/judge2.json"""
import json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
P_RE = re.compile(r"vfio_pci_mmap_huge_fault\(,order = 18\) BAR 2 page offset 0x[0-9a-f]+: 0x100\b")
d = HERE / "runs" / sys.argv[1]
res = {}
for log in sorted(d.glob("*.run*.log")):
    s = log.read_text(errors="replace")
    warns = re.findall(r"WARNING: (\S+) at (\S+)", s) + [("BUG", m) for m in re.findall(r"BUG: ([^\n]*)", s)]
    res.setdefault(log.name.split(".run")[0], []).append({
        "run": log.name, "P": bool(P_RE.search(s)), "end": "@@END 0" in s, "bad_pud": len(re.findall("bad pud", s)),
        "crash": bool(re.search(r"Oops|Kernel panic", s)), "child_ok": "@@CHILD read=0x5a5a write ok" in s,
        "pgtable_selftest": "Validating architecture page table helpers" in s, "ptc": bool(re.search(r"page_table_check", s)),
        "warnings": warns})
out = {}
for n, rs in res.items():
    ev = [r for r in rs if r["P"]]
    out[n] = {"runs": len(rs), "evaluable": len(ev), "bad_pud": sum(1 for r in ev if r["bad_pud"]), "crash": sum(1 for r in ev if r["crash"]),
              "ended": sum(1 for r in ev if r["end"]), "child_ok": sum(1 for r in ev if r["child_ok"]),
              "selftest_seen": sum(1 for r in rs if r["pgtable_selftest"]), "ptc_msgs": sum(1 for r in rs if r["ptc"]),
              "warnings": sorted({"%s@%s" % w for r in rs for w in r["warnings"]})}
    print(n, json.dumps(out[n], ensure_ascii=False))
g = lambda n: out[n]
c1 = g("M1_R0_A")["evaluable"] == 3 == g("M1_R0_A")["bad_pud"] and g("M3_R0_D")["evaluable"] == 3 == g("M3_R0_D")["crash"] \
     and g("M2_R0_C")["evaluable"] == 3 and not g("M2_R0_C")["bad_pud"]
c2 = all(g(n)["evaluable"] == 3 == g(n)["ended"] and not g(n)["bad_pud"] and not g(n)["crash"] for n in ("M4_RF_A", "M5_RF_D")) \
     and g("M5_RF_D")["child_ok"] == 3
base = set(g("M1_R0_A")["warnings"]) | set(g("M2_R0_C")["warnings"])
new = sorted((set(g("M4_RF_A")["warnings"]) | set(g("M5_RF_D")["warnings"])) - base)
c3 = all(g(n)["evaluable"] == 3 == g(n)["ended"] and not g(n)["bad_pud"] and not g(n)["crash"] for n in ("M6_X0_A", "M7_X0_D"))
v = {"问题确认": c1, "修复成立(不计告警)": c2, "RF 基线之外的新告警": new, "x86 对照成立": c3}
print("VERDICT", json.dumps(v, ensure_ascii=False))
json.dump({"summary": out, "verdict": v, "detail": res}, open(d / "judge2.json", "w"), ensure_ascii=False, indent=1)
