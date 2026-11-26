"""taskcard2: report-only diagnosis of the validation misses (after the run; no rule change)."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import taskcard2 as T2
T = T2.T
G = T.build_graph()
T2.extras(G)
out = {}
# H: rank of memory_reclaim among callbacks
T2.CAP.update({k: 10 ** 6 for k in T2.CAP})
ents, n, nr = T2.reach2(G, ["folio_pte_batch_flags"])
cb = [e for e in ents if e["kind"].startswith("回调")]
r = next((i for i, e in enumerate(cb, 1) if e["entry"] == "memory_reclaim"), None)
out["H"] = {"n_entries": len(ents), "n_callbacks": len(cb), "memory_reclaim_rank_in_callbacks": r,
            "depth": cb[r - 1]["depth"] if r else None, "callbacks_top15_depths": [e["depth"] for e in cb[:15]]}
print("H", out["H"])
# J: are the consumer and the hook in the graph (compiled in some build)?
out["J"] = {k: (k in G["defs"]) for k in ("__kernel_map_pages", "debug_pagealloc_unmap_pages", "debug_pagealloc_map_pages",
                                           "flush_tlb_kernel_range", "smp_call_function_many_cond")}
print("J in graph", out["J"])
# I: direct consumers of pmd_mkinvalid in the boundary records, and the evidence F of the row
import gzip
cons = set()
for b in T.BUILDS:
    for rr in json.load(gzip.open(T.W / f"rec_{b}.json.gz", "rt")):
        if rr["iface"] == "pmd_mkinvalid":
            cons.add((b, rr["F"]["file"], rr["F"]["name"], rr["line"], rr["kind"]))
rows = json.load(open(T2.CT / "task4_20261125" / "out" / "table.json", encoding="utf-8"))["rows"]
row = next(x for x in rows if x["no"] == 165)
evF = sorted({e["F"] for e in row["evidence"]})
ents2, n2, _ = T2.reach2(G, sorted({f.split(" ", 1)[1] for f in evF}))
out["I"] = {"direct_consumers": sorted(cons)[:20], "evidence_F": evF,
            "if_evidence_used": {"debug_vm_pgtable_in_entries": any(e["entry"] == "debug_vm_pgtable" for e in ents2), "n": len(ents2)}}
print("I", out["I"])
json.dump(out, open(T2.HERE / "diag_val.json", "w"), ensure_ascii=False, indent=1)
