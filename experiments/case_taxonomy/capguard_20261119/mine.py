"""capguard criteria 三.5: mine historical fixes adding a capability-predicate condition in common code. WSL.

    python3 mine.py mine       -> mined.json (heldout2 commits and the dev fixes excluded by id only)
    python3 mine.py packets    -> packets/NNN.txt
"""
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(HERE))
import capguard as G  # noqa: E402

EXCL = G.EXCL
DEV = {"532b53cebe58", "b02019169284"}


def excluded_ids():
    ids = set(DEV)
    for name in ("set_analysis.json", "set_sealed.json"):
        d = json.loads((CT / "heldout2_20261119" / name).read_text(encoding="utf-8"))
        for it in d["positives"] + d["negatives"]:
            ids.add(it["commit"][:12])
            ids.update(f[:12] for f in it.get("fixes", []))
    return ids


def mine():
    head = G.full("df2908090cda")
    preds, _ = G.predicates(head)
    pat = G.alt(preds)
    cond = re.compile(r"(if\s*\(|&&|\|\|)\s*!?\s*(" + pat + r")\s*\(\s*\)")
    use = re.compile(r"\b(" + pat + r")\s*\(\s*\)")
    excl = excluded_ids()
    shas = G.git("log", "--no-merges", "--format=%H", "-G", r"(" + pat + r")[[:space:]]*\([[:space:]]*\)", head, "--", "*.c").split()
    print("predicates", len(preds), "commits", len(shas), file=sys.stderr, flush=True)
    out = []
    for i, h in enumerate(shas):
        if h[:12] in excl:
            continue
        diff = G.git("show", "--format=", "-U0", h, "--", "*.c")
        cur, add, rem = None, [], []
        for ln in diff.split("\n"):
            if ln.startswith("+++ b/"):
                cur = ln[6:]
            elif cur and G.common_c(cur):
                if ln.startswith("+") and not ln.startswith("+++") and cond.search(ln):
                    add.append((cur, ln[1:].strip(), cond.search(ln).group(2)))
                elif ln.startswith("-") and not ln.startswith("---") and use.search(ln):
                    rem.append((cur, use.search(ln).group(1)))
        rset = set(rem)
        keep = [(f, l, x) for f, l, x in add if (f, x) not in rset]
        if keep:
            out.append({"commit": h[:12], "subject": G.git("log", "-1", "--format=%cs|%s", h).strip(),
                        "files": sorted({f for f, _, _ in keep}), "preds": sorted({x for _, _, x in keep}), "added": [l for _, l, _ in keep][:6]})
        if i % 100 == 0:
            print(f"{i}/{len(shas)} kept {len(out)}", file=sys.stderr, flush=True)
    (HERE / "mined.json").write_text(json.dumps({"preds": sorted(preds), "n_scanned": len(shas), "excluded_ids": len(excl), "rows": out},
                                                indent=1, ensure_ascii=False))
    print("kept", len(out))


def packets():
    rows = json.loads((HERE / "mined.json").read_text())["rows"]
    d = HERE / "packets"
    d.mkdir(exist_ok=True)
    for n, r in enumerate(rows, 1):
        msg = G.git("log", "-1", "--format=%B", r["commit"])
        msg = "\n".join(ln for ln in msg.split("\n") if not re.match(r"^(Signed-off-by|Cc|Reviewed-by|Acked-by|Tested-by|Link|Reported-by|"
                                                                     r"Suggested-by|Co-developed-by|Message-ID|Closes):", ln))
        diff = G.git("show", "--format=", "-U3", r["commit"], "--", *r["files"])
        (d / f"{n:03d}.txt").write_text(f"commit {r['commit']}\n{r['subject']}\n\n{msg.strip()}\n\n---- diff (matched files only)\n{diff[:6000]}\n")
    print("packets", len(rows))


if __name__ == "__main__":
    {"mine": mine, "packets": packets}[sys.argv[1]]()
