import gzip, json
S = json.load(gzip.open("/root/work/xres/sites_arm64.json.gz", "rt"))
for s in S:
    if s["F"] in ("follow_pmd_mask", "follow_pud_mask") and s["G"] in ("pmd_present", "pud_bad"):
        print(s["line"], s["G"], s["G_kind"], [(r["role"], r.get("type"), r.get("use"), r["cat"]) for r in s["resources"]])
from collections import Counter
mac = [s for s in S if s["G_kind"] == "macro"]
print("arm64 macro sites", len(mac), "without return", sum(1 for s in mac if not any(r["role"] == "返回" for r in s["resources"])))
print(Counter(s["G"] for s in mac if not any(r["role"] == "返回" for r in s["resources"])).most_common(12))
