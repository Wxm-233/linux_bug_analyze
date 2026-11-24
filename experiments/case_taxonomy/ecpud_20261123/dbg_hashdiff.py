"""ecpud: how many behaviours differ between ppc64le and ppc64le_hash at df after change 3 (previously identical)."""
import json
from collections import Counter
from pathlib import Path
d = Path("/root/work/ec_cache/v7/df2908090cda/df2908090cda")
A = json.loads((d / "beh_ppc64le.json").read_text())["laws"]; B = json.loads((d / "beh_ppc64le_hash.json").read_text())["laws"]
diff = [k for k in set(A) | set(B) if (A.get(k) or {}).get("beh") != (B.get(k) or {}).get("beh")]
print("keys", len(A), len(B), "differ", len(diff), Counter("|".join(k.split("|")[:2]) for k in diff).most_common(5))
print("radix beh classes", Counter(v["beh"].split(":")[0] for v in A.values()).most_common(4))
for k in sorted(diff)[:6]:
    print(" ", k, "|", (A.get(k) or {}).get("beh", "-")[:50], "|", (B.get(k) or {}).get("beh", "-")[:50])
