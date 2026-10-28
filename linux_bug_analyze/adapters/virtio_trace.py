"""virtio ordinary split two-buffer harness trace -> per-object-generation event sequence.

Migrated from experiments/case_taxonomy/unified_impl_stage2_20261027/reproduce.py (virtio_facts),
which follows virtio_add_recycle_20261027/checker.py's registered tags. Harness boundary
observations only; not hardware ordering or device DMA.
"""

from __future__ import annotations

from typing import Any, Mapping

VERSION = "virtio_split_trace/1"
KINDS = {"MAP_OK": "map", "MAP_FAIL": "map_fail", "BEFORE_PUBLISH": "barrier", "PUBLISHED": "publish",
         "SIM_USED": "used", "UNMAP": "unmap", "TOKEN": "token", "CPU_READ": "cpu_read"}
IGNORED = {"LOCK", "UNLOCK", "RMB", "EVENT_STORE", "NO_TOKEN", "KICK", "MANUAL_RECOVERY", "AFTER_FILL",
           "AFTER_RECV", "BROKEN_IN_CALLBACK"}
FINAL_KEYS = ["final_attempts", "final_maps", "final_unmaps", "final_reads", "final_kicks", "final_barriers",
              "final_g0", "final_g1"]


def adapt(row: Mapping[str, Any]) -> dict[str, Any]:
    gens: dict[int, int] = {}
    events, final, unknown, parse_ok = [], None, 0, row.get("code") == 0
    for line in row["stdout"].splitlines():
        p = line.split()
        if not p:
            parse_ok = False
            continue
        tag = p[0]
        try:
            if tag == "ATTEMPT":
                obj = int(p[2])
                gens[obj] = gens.get(obj, 0) + 1
                events.append(["attempt", "buf%d" % obj, gens[obj]])
            elif tag in ("MAP_OK", "MAP_FAIL", "BEFORE_PUBLISH", "PUBLISHED"):
                obj = int(p[2])
                events.append([KINDS[tag], "buf%d" % obj, gens.get(obj, 0)])
            elif tag == "BYPASS":
                obj = int(p[1])
                events.append(["bypass", "buf%d" % obj, gens.get(obj, 0)])
            elif tag == "ADD_RETURN":
                obj, ret = int(p[2]), int(p[3])
                events.append(["add_ok" if ret == 0 else "add_fail", "buf%d" % obj, gens.get(obj, 0)])
            elif tag in ("SIM_USED", "UNMAP", "TOKEN", "CPU_READ"):
                obj = int(p[1])
                events.append([KINDS[tag], "buf%d" % obj, gens.get(obj, 0)])
            elif tag == "FINAL":
                final = list(map(int, p[1:]))
            elif tag not in IGNORED:
                unknown += 1
        except (IndexError, ValueError):
            parse_ok = False
    values = {"route": row.get("route"), "events": events, "final_present": final is not None and len(final) == 8,
              "parse_ok": parse_ok and unknown == 0}
    values.update(zip(FINAL_KEYS, final if final is not None and len(final) == 8 else [-1] * 8))
    return {"values": values, "types": {"events": "event_seq"},
            "observation": {"mode": row.get("mode"), "route": row.get("route"), "indirect": row.get("indirect"),
                            "events": len(events)}}
