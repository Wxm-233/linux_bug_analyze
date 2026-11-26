"""taskcard: report-only diagnosis after run 2 - rank of the gold entry under other orderings (not a gate, rule unchanged)."""
import json, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import taskcard as T
G = T.build_graph()
cards = json.load(open(T.HERE / "cards_gold.json", encoding="utf-8"))
alt = {"D": ["ext4_dax_huge_fault", "ext4_dax_fault"]}
out = {}
for g in T.GOLD:
    c = cards[g["id"]]
    srcs = sorted({x.split(" ", 1)[1] for x in c["定位"]["consumers"]}) if g["engine"] == "EC" else [g["func"]]
    ents, n, nr = T.reach(G, srcs, maxd=16, cap=100000)
    # specificity: how many distinct consumers-of-anything an entry reaches is costly; use fan-out proxy = number of forward callees
    def rk(order):
        es = sorted(ents, key=order)
        for i, e in enumerate(es, 1):
            if e["entry"] == g["entry"] or g["entry"] in e["path"] or e["entry"] in alt.get(g["id"], []):
                return i, e["entry"], e["depth"]
        return None, None, None
    by_kind = rk(lambda e: (["系统调用", "回调", "架构入口"].index(e["kind"].split("：")[0].split("（")[0]), e["depth"]))
    by_depth = rk(lambda e: (e["depth"], ["系统调用", "回调", "架构入口"].index(e["kind"].split("：")[0].split("（")[0])))
    cb_first = rk(lambda e: (0 if e["kind"].startswith("回调") else 1, e["depth"]))
    out[g["id"]] = {"n_entries": len(ents), "rule_rank": by_kind, "depth_first_rank": by_depth, "callback_first_rank": cb_first}
    print(g["id"], len(ents), "rule", by_kind, "depth-first", by_depth, "callback-first", cb_first)
json.dump(out, open(T.HERE / "diag_rank.json", "w"), ensure_ascii=False, indent=1)
