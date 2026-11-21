"""firstbreak criteria 三 (mechanical part): per analysis-set positive -> fix, parent, changed files/functions, S2, S5, S6. WSL.

    python3 collect.py   -> collected.json
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "scan3_20261119"))
REPO = "/root/repos/linux"
SRC = "/root/repos/linux/"
BUILDS = {a: f"/root/work/boundary_build/{a}_defconfig" for a in ("riscv", "arm64", "x86_64")}


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, errors="replace").stdout


def main():
    import scan3 as S
    S.check_frozen()
    dbs = {}
    for a, d in BUILDS.items():
        cc = json.load(open(d + "/compile_commands.json"))
        dbs[a] = {e["file"][len(SRC):] for e in cc if e["file"].startswith(SRC)}
    head_files = set(git("ls-tree", "-r", "--name-only", "df2908090cda").split("\n"))
    s = json.loads((CT / "heldout2_20261119/set_analysis.json").read_text(encoding="utf-8"))
    ez = {r["commit"]: r for r in json.loads((CT / "effzero_eval_20261120/analysis_rows.json").read_text(encoding="utf-8"))}
    out = []
    for p in s["positives"]:
        names = {fn for _, fn in p.get("fix_funcs", [])}
        row = {"commit": p["commit"][:12], "used": bool(p["used"]), "categories": p["categories"], "info": p.get("info"),
               "fixes": [], "fix_funcs": sorted(names)}
        s5, s6 = False, []
        for f in p["fixes"]:
            par = git("rev-parse", f + "^").strip()
            files = [x for x in git("show", "--format=", "--name-only", f).split("\n") if x]
            subj = git("log", "-1", "--format=%cs %s", f).strip()
            s2 = {}
            for x in files:
                if not x.endswith(".c"):
                    continue
                s2[x] = ("not-at-head" if x not in head_files else {a: (x in dbs[a]) for a in dbs})
            rows, st = S.rows_of(par)
            hits = [r for r in rows if r["func"] in names]
            if hits:
                s5 = True
                s6 += [{"engine": r["engine"], "no": r["no"], "prio": r["prio"], "file": r["file"], "func": r["func"],
                        "of": len(rows)} for r in hits[:6]]
            row["fixes"].append({"fix": f[:12], "parent": par[:12], "subject": subj, "files": files, "s2_c_files": s2})
        e = ez.get(p["commit"][:12])
        if e and e.get("ez"):
            s5 = True
            s6 += [{"engine": "EZ", "hit": h} for h in e["ez_hits"]]
        row["S5"] = s5
        row["S6"] = s6
        out.append(row)
    (HERE / "collected.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    for r in out:
        print(r["commit"], "used" if r["used"] else "clean", r["fixes"][0]["fix"], r["fixes"][0]["subject"][:70], "| S5", r["S5"],
              [(x["engine"], x.get("no"), x.get("prio")) for x in r["S6"]][:3])


if __name__ == "__main__":
    main()
