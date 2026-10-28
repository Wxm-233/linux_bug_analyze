"""SMMU registered qtest transcript -> event sequence and reply facts.

Migrated from experiments/case_taxonomy/unified_impl_stage2_20261027/reproduce.py (smmu_facts),
which follows smmu_review_20261026/checker.py's registered layout. Not a general transcript parser.
"""

from __future__ import annotations

from typing import Any, Mapping

VERSION = "smmu_qtest/1"
KINDS = ["payload_write", "payload_readback", "base_config", "enable", "enable_ack", "prod_write", "status_read"]


def adapt(raw: Mapping[str, Any]) -> dict[str, Any]:
    words = raw.get("words") or []
    pairs = list(words) + [[0x46, 0]]
    reserved = commands = 0
    for a, b in words:
        if a & 255 == 0x12:
            commands += 1
            tg, ttl, num, scale = (b >> 10) & 3, (b >> 8) & 3, (a >> 12) & 31, (a >> 20) & 31
            reserved += int(tg != 0 and ttl == num == scale == 0)
    lo, hi = 0x40010000, 0x40010000 + len(pairs) * 16
    events, anomalies, status, written = [], 0, {}, {}
    requests = raw.get("requests", [])
    responses = raw.get("stdout", "").splitlines()
    anomalies += abs(len(requests) - len(responses))
    for req, resp in zip(requests, responses):
        p = req.split()
        opn, addr = p[0], int(p[1], 0)
        f = resp.split()
        anomalies += int(f != ["OK"]) if opn.startswith("write") else int(len(f) != 2 or f[0] != "OK")
        if opn == "writeq" and lo <= addr < hi:
            kind = "payload_write"
            written[addr] = int(p[2], 0)
        elif opn == "readq" and lo <= addr < hi:
            kind = "payload_readback"
            if len(f) == 2 and int(f[1], 0) != written.get(addr):
                anomalies += 1
        elif opn == "writeq" and addr == 0x9050090:
            kind = "base_config"
        elif opn == "writel" and addr == 0x9050020:
            kind = "enable"
        elif opn == "readl" and addr == 0x9050024:
            kind = "enable_ack"
            anomalies += int(len(f) != 2 or int(f[1], 0) != 8)
        elif opn == "writel" and addr == 0x9050098:
            kind = "prod_write"
            anomalies += int(int(p[2], 0) != len(pairs))
        elif opn == "readl" and addr in (0x9050098, 0x905009C, 0x9050060, 0x9050064):
            kind = "status_read"
            if len(f) == 2:
                status[addr] = int(f[1], 0)
        else:
            kind = "unregistered"
        events.append([kind, "cmdq", 0])
    cons = status.get(0x905009C)
    unsupported = cons is None or bool(cons & ~((127 << 24) | 127)) or (cons & 127) > len(pairs)
    values = {"authority_verified": True, "commands_present": commands > 0, "expected_payload_words": 2 * len(pairs),
              "events": events, "reply_anomalies": anomalies, "unsupported_consumer_state": unsupported,
              "reserved_commands": reserved}
    return {"values": values, "types": {"events": "event_seq"},
            "observation": {"requests": len(requests), "responses": len(responses), "commands": commands}}
