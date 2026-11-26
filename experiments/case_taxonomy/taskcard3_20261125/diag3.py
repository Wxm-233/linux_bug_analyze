"""taskcard3: report-only - ranks of the gold entries without the per-kind caps (after the run; no rule change)."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import taskcard3 as T3
T2, T = T3.T2, T3.T
G = T.build_graph(); T2.extras(G); T3.extras3(G)
cards = json.load(open(T3.HERE / "cards_gold.json", encoding="utf-8"))
big = {k: 10 ** 6 for k in T2.CAP}
out = {}
def rank(ents, want):
    for kind in ("系统调用", "回调", "启动时", "架构入口"):
        es = [e for e in ents if e["kind"].startswith(kind)]
        for i, e in enumerate(es, 1):
            if e["entry"] in want:
                return {"kind": kind, "rank_in_kind": i, "hubs": e["hubs"], "depth": e["depth"], "n_kind": len(es)}
    return None
# H trigger
ents, n, _ = T3.entries(G, ["folio_pte_batch_flags"], big)
out["H_trigger"] = rank(ents, ["memory_reclaim"]); print("H trigger", out["H_trigger"])
for gid, want in T3.PRE_GOLD.items():
    c = cards.get(gid)
    pe = c["前置状态入口"]
    if isinstance(pe, str):
        out[gid] = "无产生者"; print(gid, "no producers"); continue
    ents, n, _ = T3.entries(G, pe["producers"] if pe["n_producers"] <= 20 else pe["producers"], big)
    out[gid] = {"producers": pe["n_producers"], "how": pe["how"], "rank": rank(ents, want)}
    print(gid, out[gid])
json.dump(out, open(T3.HERE / "diag_rank.json", "w"), ensure_ascii=False, indent=1)
