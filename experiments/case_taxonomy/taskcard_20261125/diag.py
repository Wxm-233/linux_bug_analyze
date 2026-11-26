"""taskcard: diagnosis of T3/T4 misses (after the run; report only, no rule change). WSL."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import taskcard as T
G = T.build_graph()
res = json.load(open(T.HERE / "result.json", encoding="utf-8"))
cards = json.load(open(T.HERE / "cards_gold.json", encoding="utf-8"))
out = {}
for g, gg in zip(T.GOLD, res["gold"]):
    c = cards.get(g["id"])
    srcs = sorted({x.split(" ", 1)[1] for x in c["定位"]["consumers"]}) if g["engine"] == "EC" else [g["func"]]
    ents, n, nr = T.reach(G, srcs, maxd=16, cap=100000)
    rank = next((i for i, e in enumerate(ents, 1) if e["entry"] == g["entry"] or g["entry"] in e["path"]), None)
    hit = ents[rank - 1] if rank else None
    kinds = {}
    for e in ents:
        k = e["kind"].split("：")[0]
        kinds[k] = kinds.get(k, 0) + 1
    out[g["id"]] = {"entry": g["entry"], "reachable": rank is not None, "rank": rank, "n_entries": len(ents), "by_kind": kinds,
                    "depth": hit["depth"] if hit else None, "path": hit["path"] if hit else None,
                    "first20_kinds": [e["kind"].split("：")[0] for e in ents[:20]].count("系统调用")}
    print(g["id"], g["entry"], "rank", rank, "of", len(ents), kinds, "depth", hit["depth"] if hit else None)
    if hit: print("   ", " ".join(hit["path"])[:400])
json.dump(out, open(T.HERE / "diag_t3.json", "w"), ensure_ascii=False, indent=1)
