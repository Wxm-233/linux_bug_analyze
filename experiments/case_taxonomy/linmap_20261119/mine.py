"""linmap criteria 三.4: mine historical fixes for independent recall samples. WSL.

    python3 mine.py mine        -> mined.json  (mechanical; heldout2 analysis/sealed commits and the dev fixes excluded by id only)
    python3 mine.py packets     -> packets/<n>.txt for blind labelling (subject, message, the matched hunks)
"""
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
REPO = "/root/repos/linux"
SINK = re.compile(r"\b(virt_to_phys|__pa|virt_to_page|virt_to_pfn|virt_to_folio|virt_to_head_page|sg_init_one|sg_set_buf)\s*\(")
FIXTOK = re.compile(r"\b(__pa_symbol|lm_alias|vmalloc_to_page|vmalloc_to_pfn|is_vmalloc_addr|virt_addr_valid|kmap_to_page)\b")
EXCL = ("arch/", "tools/", "scripts/", "samples/", "Documentation/", "usr/")
DEV = {"2e2713ae1a05", "9c500835f279"}


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, errors="replace").stdout


def excluded_ids():
    """ids appearing anywhere in the heldout2 set files (positives, their fixes, negatives) -- by id only, nothing else read"""
    ids = set(DEV)
    for name in ("set_analysis.json", "set_sealed.json"):
        d = json.loads((CT / "heldout2_20261119" / name).read_text(encoding="utf-8"))
        for it in d["positives"] + d["negatives"]:
            ids.add(it["commit"][:12])
            ids.update(f[:12] for f in it.get("fixes", []))
    return ids


def mine():
    excl = excluded_ids()
    log = git("log", "--no-merges", "--format=%H", "-G", FIXTOK.pattern.replace(r"\b", ""), "HEAD", "--", "*.c")
    shas = [s for s in log.split() if s]
    print("commits touching fix tokens:", len(shas), file=sys.stderr, flush=True)
    out = []
    for i, h in enumerate(shas):
        if h[:12] in excl:
            continue
        diff = git("show", "--format=", "-U0", h, "--", "*.c")
        files, cur, rem, add = set(), None, [], []
        for ln in diff.split("\n"):
            if ln.startswith("+++ b/"):
                cur = ln[6:]
            elif cur and not cur.startswith(EXCL):
                if ln.startswith("-") and not ln.startswith("---") and SINK.search(ln):
                    rem.append((cur, ln[1:].strip()))
                elif ln.startswith("+") and not ln.startswith("+++") and FIXTOK.search(ln):
                    add.append((cur, ln[1:].strip()))
        rfiles = {f for f, _ in rem}
        both = rfiles & {f for f, _ in add}
        if both:
            subj = git("log", "-1", "--format=%cs|%s", h).strip()
            out.append({"commit": h[:12], "subject": subj, "files": sorted(both),
                        "removed": [x for f, x in rem if f in both][:6], "added": [x for f, x in add if f in both][:6]})
        if i % 200 == 0:
            print(f"{i}/{len(shas)} kept {len(out)}", file=sys.stderr, flush=True)
    (HERE / "mined.json").write_text(json.dumps({"n_scanned": len(shas), "excluded_ids": len(excl), "rows": out}, indent=1, ensure_ascii=False))
    print("kept", len(out))


def packets():
    rows = json.loads((HERE / "mined.json").read_text())["rows"]
    d = HERE / "packets"
    d.mkdir(exist_ok=True)
    for n, r in enumerate(rows, 1):
        msg = git("log", "-1", "--format=%B", r["commit"])
        msg = "\n".join(ln for ln in msg.split("\n") if not re.match(r"^(Signed-off-by|Cc|Reviewed-by|Acked-by|Tested-by|Link|Reported-by|"
                                                                     r"Suggested-by|Co-developed-by|Message-ID|Closes):", ln))
        diff = git("show", "--format=", "-U3", r["commit"], "--", *r["files"])
        (d / f"{n:03d}.txt").write_text(f"commit {r['commit']}\n{r['subject']}\n\n{msg.strip()}\n\n---- diff (matched files only)\n{diff[:6000]}\n")
    print("packets", len(rows))


if __name__ == "__main__":
    {"mine": mine, "packets": packets}[sys.argv[1]]()
