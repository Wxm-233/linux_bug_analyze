"""capsupply criteria 三/四: mechanical selection of capability-precondition candidate fixes, split by count (latest 40% = late). WSL, read-only.

    python3 mine.py
Writes design.json (design side, for Claude) and sealed_late/late.json (late side, scorer only -- Claude does not open it).
Prints counts only; never prints late-side ids or subjects. Sealed pools are compared mechanically (counts only).
"""
import json
import os
import re
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
REPO = "/root/repos/linux"
RANGE = "v4.0..aebb72744764"
PATHSPEC = [".", ":(exclude)tools", ":(exclude)Documentation", ":(exclude)samples", ":(exclude)scripts"]
LATE_FRAC = 0.40
KNOWN = {"b02019169284", "532b53cebe58", "09073396ea62"}   # hugetlb, secretmem, CPPC fixes -> design side
SELFTEST = {"b02019169284", "532b53cebe58"}

TRAILER = re.compile(r"^\s*(Fixes|Signed-off-by|Cc|Reported-by|Reviewed-by|Acked-by|Tested-by|Link|Suggested-by|Co-developed-by|"
                     r"Closes|Reported-and-tested-by|Message-ID|Debugged-by|Originally-by|Requested-by)\s*:", re.I)
MSG = re.compile(r"\b(not supported|unsupported|support(s|ed)?|capabilit(y|ies)|feature|availab(le|ility)|not present|absent|lack(s|ing)?|without|disabled)\b", re.I)
CAP = re.compile(r"\b(boot_cpu_has|static_cpu_has|cpu_feature_enabled|this_cpu_has|cpus_have_\w+|alternative_has_cap_\w+|system_supports_\w+|"
                 r"riscv_has_extension_(likely|unlikely)|riscv_isa_extension_available|has_vector|cpu_has_feature|mmu_has_feature|firmware_has_feature|"
                 r"radix_enabled|early_cpu_has|test_facility|MACHINE_HAS_\w+|cpu_has_\w+)\b|"
                 r"\b(arch_has_\w+|hugepages_supported|has_transparent_hugepage|can_set_direct_map|pgtable_l[45]_enabled|\w+_supported|\w+_available)\s*\(\s*\)")
CTX = re.compile(r"\bif\b|\breturn\b|\?|&&|\|\|")
FIXES = re.compile(r"^\s*Fixes:\s*([0-9a-f]{8,40})", re.I | re.M)
CHERRY = re.compile(r"cherry picked from commit ([0-9a-f]{12,40})", re.I)
HEX = re.compile(r"\b[0-9a-f]{12}")


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, errors="replace").stdout


def ids_in_tree(d):
    out = set()
    for root, dirs, files in os.walk(d):
        for fn in files:
            try:
                out |= set(HEX.findall(open(os.path.join(root, fn), encoding="utf-8", errors="ignore").read()))
            except Exception:
                pass
    return out


def main():
    t0 = time.time()
    raw = git("log", RANGE, "--no-merges", "--format=%H%x00%cs%x00%B%x01", "--", *PATHSPEC)
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
        if MSG.search(text):
            stage1.append((h, date, lines[0], body))
    print("commits in range/paths:", n_all, "| fix-marked & message match:", len(stage1), flush=True)
    cands = []
    for h, date, subj, body in stage1:
        patch = git("show", "--format=", "--no-color", "-U0", h, "--", *PATHSPEC)
        toks, files, fname = set(), set(), None
        for ln in patch.split("\n"):
            if ln.startswith("+++ ") or ln.startswith("--- "):
                if ln.startswith("+++ b/"):
                    fname = ln[6:]
                    files.add(fname)
                continue
            if ln.startswith("+") and fname and CTX.search(ln[1:]):
                toks.update(m.group(0) for m in CAP.finditer(ln[1:]))
        if toks:
            cands.append({"commit": h[:12], "date": date, "subject": subj, "fixes": sorted({f[:12] for f in FIXES.findall(body)}),
                          "cherry_from": sorted({c[:12] for c in CHERRY.findall(body)}), "tokens": sorted(toks), "files": sorted(files)})
    print("patch token match:", len(cands), "|", round(time.time() - t0), "s", flush=True)
    ids = {c["commit"] for c in cands}
    st = {s: (s in ids) for s in SELFTEST}
    print("selftest:", st, flush=True)
    if not all(st.values()):
        raise SystemExit("selftest failed -- stop (criteria 三), write amendment")
    # criteria 四.2: latest 40% by date -> late
    order = sorted((c for c in cands if c["commit"] not in KNOWN), key=lambda c: (c["date"], c["commit"]))
    n_late = round(len(order) * LATE_FRAC)
    late = order[len(order) - n_late:]
    cutoff = late[0]["date"] if late else None
    late_ids = {c["commit"] for c in late}
    design = [c for c in cands if c["commit"] not in late_ids]
    sp = json.load(open(CT / "heldout2_20261119/split.json"))
    sealed = {h[:12] for h in sp["sealed"]}
    analysis = {h[:12] for h in sp["analysis"]}
    used = set(json.load(open(HERE / "used_ids.json")))
    other_sealed = ids_in_tree(CT / "effsupply_20261120/sealed_late") | ids_in_tree(CT / "effzero_eval_20261120/sealed") | ids_in_tree(CT / "abisupply_20261121/sealed_late")
    d_sealed = [c for c in design if c["commit"] in sealed]
    design = [c for c in design if c["commit"] not in sealed]
    for c in design:
        c["used"] = c["commit"] in used
        c["analysis_set"] = c["commit"] in analysis
    ex = {"heldout2_sealed": 0, "heldout2_analysis": 0, "other_sealed_pools": 0, "used": 0}
    late_keep = []
    for c in late:
        if c["commit"] in sealed:
            ex["heldout2_sealed"] += 1
        elif c["commit"] in analysis:
            ex["heldout2_analysis"] += 1
        elif c["commit"] in other_sealed:
            ex["other_sealed_pools"] += 1
        elif c["commit"] in used:
            ex["used"] += 1
        else:
            late_keep.append(c)
    (HERE / "design.json").write_text(json.dumps(design, indent=1, ensure_ascii=False))
    (HERE / "sealed_late").mkdir(exist_ok=True)
    (HERE / "sealed_late/late.json").write_text(json.dumps(late_keep, indent=1, ensure_ascii=False))
    summ = {"range": RANGE, "commits_in_range_paths": n_all, "stage1_fix_and_message": len(stage1), "candidates": len(cands),
            "late_cutoff_date": cutoff, "design": len(design), "design_used": sum(c["used"] for c in design),
            "design_sealed_dropped": len(d_sealed), "late_total": len(late), "late_excluded": ex, "late_kept": len(late_keep),
            "late_kept_rootcause_upper": len({(tuple(c["fixes"]) or (c["commit"],)) for c in late_keep}),
            "secs": round(time.time() - t0)}
    (HERE / "mine_summary.json").write_text(json.dumps(summ, indent=1, ensure_ascii=False))
    print(json.dumps(summ, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
