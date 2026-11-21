"""Mechanical consistency check of the scorer's sealed output. Prints counts / booleans only, never ids or text.

    python check_scorer.py
"""
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
S = HERE / "sealed_late"
late = json.loads((S / "late.json").read_text(encoding="utf-8"))
jud = json.loads((S / "scorer_judgement.json").read_text(encoding="utf-8"))
rcs = json.loads((S / "rootcauses.json").read_text(encoding="utf-8"))
summ = json.loads((S / "summary.json").read_text(encoding="utf-8"))
pos = json.loads((HERE / "design_positives.json").read_text(encoding="utf-8"))

late_ids = {c["commit"] for c in late}
jid = [j["commit"][:12] for j in jud]
v = Counter(j["verdict"] for j in jud)
yes = [j for j in jud if j["verdict"] == "是"]
yes_rc = {j.get("rootcause_id") for j in yes}
meta = {c["commit"]: c for c in late}
design_keys = {p["commit"] for p in pos} | {f for p in pos for f in p["fixes"]}
overlap = sum(1 for j in yes if j["commit"][:12] in design_keys or set(meta.get(j["commit"][:12], {}).get("fixes", [])) & design_keys)
rc_list = rcs if isinstance(rcs, list) else rcs.get("rootcauses", list(rcs.values()) if isinstance(rcs, dict) else [])
out = {
    "judgement_entries": len(jud), "all_late_judged_once": sorted(jid) == sorted(late_ids),
    "verdict_counts_match_summary": (v.get("是", 0), v.get("同族非架构", 0), v.get("说不清", 0), v.get("不是", 0)) ==
    (summ["yes_commits"], summ["family_nonarch_commits"], summ["unclear_commits"], summ["no_commits"]),
    "yes_distinct_rootcause_ids": len(yes_rc - {None}), "rootcauses_file_entries": len(rc_list),
    "yes_all_read_full_patch": all(j.get("read_full_patch") for j in yes),
    "yes_with_null_request_variation_or_consumer": sum(1 for j in yes if not (j.get("request") and j.get("variation") and j.get("consumer"))),
    "yes_mechanically_overlapping_design_positive_or_fixes_target": overlap,
    "yes_distinct_fixes_targets_or_self": len({tuple(meta[j["commit"][:12]]["fixes"]) or (j["commit"][:12],) for j in yes}),
}
print(json.dumps(out, indent=1))
