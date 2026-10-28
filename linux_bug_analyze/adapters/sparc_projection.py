"""SPARC64 host-projection record (stage snapshots) -> identity/count/preparation facts.

Migrated from experiments/case_taxonomy/sparc_identity_chain_20261027/analyze.py (facts_of).
Projection tier with explicit substitutes; not a SPARC boot.
"""

from __future__ import annotations

from typing import Any, Mapping

VERSION = "sparc_projection/1"


def adapt(rec: Mapping[str, Any]) -> dict[str, Any]:
    stages = {s["stage"]: s for s in rec["observation"]["stages"]}
    fin, summ = stages["after_setup_nr_cpu_ids"], stages["summary"]
    online = stages["after_bringup"]["online"]
    provided = sorted({int(x) for x in rec["ids"].split(",")})
    limit = None if rec["L"] == "none" else int(rec["L"])
    possible = fin["possible"]
    values = {"supported_context": True, "limit_given": limit is not None, "limit": limit if limit is not None else 0,
              "no_truncation_needed": limit is None or len(provided) <= limit,
              "invented_possible": sorted(set(possible) - set(provided)), "possible_count": len(possible),
              "possible_set": possible, "provided_set": provided,
              "online_without_irqstack": sorted(set(online) - set(summ["irqstack_allocated"])),
              "online_without_percpu": sorted(set(online) - set(summ["percpu_offset_assigned"]))}
    return {"values": values, "types": {},
            "observation": {"version": rec["version"], "NR_CPUS": rec["NR_CPUS"], "input": rec["input"], "L": rec["L"]}}
