"""ecrecall: name-independent check -- candidate rows on the sample's architectures that disappear when the fix is applied
(parent method: parent vs parent+fix; re-injection: re-injected vs df2908090cda baseline)"""
import json, subprocess
from pathlib import Path
V = Path("/root/work/ec_cache/v")
R = Path("/root/work/ecrecall")
def k(c): return (c["arch"], c["func"], c["class"])
out = {}
for h in ["6f74c0ec2095", "018e9828eb52", "144bb0aee33a", "e0fe5ab4192c", "5d9cea8a552e", "ddc1729b07cc", "23bc8f69f0ec", "fba88ede6a31", "ff1712f953e2"]:
    par = subprocess.run(["git", "-C", "/root/repos/linux", "rev-parse", "--short=12", h + "^"], capture_output=True, text=True).stdout.strip()
    full = subprocess.run(["git", "-C", "/root/repos/linux", "rev-parse", par], capture_output=True, text=True).stdout.strip()
    info = json.loads((V / f"{h}-fixed" / "fixinfo.json").read_text())
    import sys; sys.path.insert(0, "/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/ecscan_20261122")
    archs = set(info["archs"])
    P = json.loads((V / par / f"{full}.json").read_text())["cands"]
    fp = V / f"{h}-fixed" / f"{full}.json"
    F = json.loads(fp.read_text())["cands"] if fp.exists() else []
    fk = {k(c) for c in F}
    gone = [k(c) for c in P if c["arch"] in archs and k(c) not in fk]
    newf = [k(c) for c in F if c["arch"] in archs and k(c) not in {k(x) for x in P}]
    inj = R / h / "result.json"
    ij = json.loads(inj.read_text()) if inj.exists() else None
    out[h] = {"parent_rows_on_arch": [k(c) for c in P if c["arch"] in archs], "gone_after_fix": gone, "new_after_fix": newf,
              "inject_new_on_arch": [(c["arch"], c["func"], c["class"]) for c in (ij or {}).get("new", []) if c["arch"] in archs] if ij else None}
    print(h, par, "parent rows on arch", len(out[h]["parent_rows_on_arch"]), "gone", gone, "new", newf, "| inject new", out[h]["inject_new_on_arch"] and len(out[h]["inject_new_on_arch"]))
Path("/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/ecrecall_20261122/results/gone.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
