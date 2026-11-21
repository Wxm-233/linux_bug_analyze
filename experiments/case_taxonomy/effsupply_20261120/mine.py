"""effsupply criteria 三/四 (+ amendment 1): mechanical selection of E-ZERO candidate fixes, split by date. WSL, read-only.

    python3 mine.py
Writes design.json (design side, for Claude) and sealed_late/late.json (late side, for the scorer only -- Claude does not open it).
Prints counts only; never prints late-side ids or subjects.
"""
import io
import json
import os
import re
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parent.parent                      # experiments/
CT = HERE.parent
REPO = "/root/repos/linux"
RANGE = "v4.0..df2908090cda"
PATHS = ["mm/", "kernel/", "lib/", "include/", "arch/", "drivers/iommu/", "drivers/firmware/"]
CUTOFF = "2024-01-01"
CALIB = {"5bebe8de1926", "6c2f761dad78"}       # X1, KASAN HW_TAGS zeroing fix
SEEN_LATE = {"6a288a4ddb4a"}
SELFTEST = {"5bebe8de1926", "6c2f761dad78"}

TRAILER = re.compile(r"^\s*(Fixes|Signed-off-by|Cc|Reported-by|Reviewed-by|Acked-by|Tested-by|Link|Suggested-by|Co-developed-by|"
                     r"Closes|Reported-and-tested-by|Message-ID|Debugged-by|Originally-by|Requested-by)\s*:", re.I)
ZMSG = re.compile(r"\b(zero(e?d|ing|es|i[sz]e[ds]?|i[sz]ing)?|uninitiali[sz]ed|stale|init_on_(alloc|free)|__GFP_ZERO|info(rmation)? leak)\b", re.I)
ZTOK = re.compile(r"__GFP_ZERO|GFP_ZERO\b|__GFP_ZEROTAGS|want_init_on_(alloc|free)|init_on_(alloc|free)|\bclear_(user_)?(high)?pages?\b|"
                  r"tag_clear_highpages?|clear_highpage_kasan_tagged|\bzero_user(_segments?|_segment)?\b|memzero_(explicit|page)|"
                  r"\bk[vz]?zalloc\b|\bvzalloc\b|\bkvzalloc\b|\bmemset\s*\(.*,\s*0\s*,|KASAN_\w*INIT|\bhuge_zero|ZERO_PAGE|\bzero_page")
FIXES = re.compile(r"^\s*Fixes:\s*([0-9a-f]{8,40})", re.I | re.M)
CHERRY = re.compile(r"cherry picked from commit ([0-9a-f]{12,40})", re.I)


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, errors="replace").stdout


def used_ids():
    """12-char hex tokens appearing anywhere in experiments/ (taint_check.py convention), excluding this dir and two global lists"""
    skip = {"case_taxonomy/heldout_commit_20261117/pool.json", "case_taxonomy/depmine_20261115/candidates.json"}
    tok = re.compile(r"\b[0-9a-f]{12}")
    out = set()
    for root, dirs, files in os.walk(EXP):
        if "effsupply_20261120" in root or "__pycache__" in root:
            continue
        for fn in files:
            p = os.path.relpath(os.path.join(root, fn), EXP).replace("\\", "/")
            if p in skip or not fn.endswith((".md", ".json", ".txt", ".log", ".py", ".sh", ".csv")):
                continue
            try:
                s = io.open(os.path.join(root, fn), encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            out.update(tok.findall(s))
    return out


def main():
    t0 = time.time()
    raw = git("log", RANGE, "--no-merges", "--format=%H%x00%cs%x00%B%x01", "--", *PATHS)
    n_all, stage1 = 0, []
    for rec in raw.split("\x01"):
        rec = rec.strip("\n")
        if not rec:
            continue
        h, date, body = rec.split("\x00", 2)
        n_all += 1
        lines = body.split("\n")
        fix = bool(FIXES.search(body)) or any(re.match(r"^\s*Cc:.*stable@", ln, re.I) for ln in lines)
        if not fix:
            continue
        text = "\n".join(ln for ln in lines if not TRAILER.match(ln))
        if ZMSG.search(text):
            stage1.append((h, date, lines[0], body))
    print("commits in range/paths:", n_all, "| fix-marked & message match:", len(stage1), flush=True)
    cands = []
    for h, date, subj, body in stage1:
        patch = git("show", "--format=", "--no-color", "-U0", h, "--", *PATHS)
        toks, files = set(), set()
        fname = None
        for ln in patch.split("\n"):
            if ln.startswith("+++ ") or ln.startswith("--- "):
                if ln.startswith("+++ b/"):
                    fname = ln[6:]
                    files.add(fname)
                continue
            if ln.startswith(("+", "-")) and fname:
                toks.update(m.group(0) for m in ZTOK.finditer(ln))
        if toks:
            cands.append({"commit": h[:12], "date": date, "subject": subj, "fixes": sorted({f[:12] for f in FIXES.findall(body)}),
                          "cherry_from": sorted({c[:12] for c in CHERRY.findall(body)}), "tokens": sorted(toks), "files": sorted(files)})
    print("patch token match:", len(cands), "|", round(time.time() - t0), "s", flush=True)
    ids = {c["commit"] for c in cands}
    st = {s: (s in ids) for s in SELFTEST}
    print("selftest:", st, flush=True)
    if not all(st.values()):
        raise SystemExit("selftest failed -- stop (criteria 三), write amendment")
    sp = json.load(open(CT / "heldout2_20261119/split.json"))
    sealed = {h[:12] for h in sp["sealed"]}
    analysis = {h[:12] for h in sp["analysis"]}
    a2 = HERE / "used_ids_a2.json"            # amendment 2: precomputed by used_ids_a2.py (global lists > 1000 ids skipped)
    used = set(json.loads(a2.read_text())) if a2.exists() else used_ids()
    print("used ids from", "amendment 2 file" if a2.exists() else "run-1 walk", len(used), flush=True)
    design = [c for c in cands if c["date"] < CUTOFF or c["commit"] in CALIB]
    late = [c for c in cands if not (c["date"] < CUTOFF or c["commit"] in CALIB)]
    d_sealed = [c for c in design if c["commit"] in sealed]
    design = [c for c in design if c["commit"] not in sealed]
    for c in design:
        c["used"] = c["commit"] in used
        c["analysis_set"] = c["commit"] in analysis
    ex = {"sealed": 0, "analysis": 0, "used": 0, "seen_subject": 0}
    late_keep = []
    for c in late:
        if c["commit"] in sealed:
            ex["sealed"] += 1
        elif c["commit"] in analysis:
            ex["analysis"] += 1
        elif c["commit"] in SEEN_LATE:
            ex["seen_subject"] += 1
        elif c["commit"] in used:
            ex["used"] += 1
        else:
            late_keep.append(c)
    (HERE / "design.json").write_text(json.dumps(design, indent=1, ensure_ascii=False))
    (HERE / "sealed_late").mkdir(exist_ok=True)
    (HERE / "sealed_late/late.json").write_text(json.dumps(late_keep, indent=1, ensure_ascii=False))
    summ = {"commits_in_range_paths": n_all, "stage1_fix_and_message": len(stage1), "candidates": len(cands),
            "design": len(design), "design_used": sum(c["used"] for c in design), "design_sealed_dropped": len(d_sealed),
            "late_total": len(late), "late_excluded": ex, "late_kept": len(late_keep),
            "late_kept_rootcause_upper": len({(tuple(c["fixes"]) or (c["commit"],)) for c in late_keep}),
            "secs": round(time.time() - t0)}
    (HERE / "mine_summary.json").write_text(json.dumps(summ, indent=1, ensure_ascii=False))
    print(json.dumps(summ, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
