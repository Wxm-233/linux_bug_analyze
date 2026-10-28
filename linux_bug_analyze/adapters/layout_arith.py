"""Stored layout / geometry rows -> integer facts for core arithmetic.

Migrated from experiments/case_taxonomy/unified_impl_stage2_20261027/reproduce.py (section_arithmetic).
Inputs: a virtio_platform_qualification runtime_results row, or a btrfs_method diagnostics row.
"""

from __future__ import annotations

from typing import Any, Mapping

VERSION = "layout_arith/1"


def adapt_virtio_layout(row: Mapping[str, Any]) -> dict[str, Any]:
    base, lay = row["base"], row["layout"]
    values = {"granule": row["maintenance_stride"], "evt": base + lay["evts"], "end": base + lay["end"],
              "lock": base + lay["lock"]}
    return {"values": values, "types": {}, "observation": {"name": row.get("name"), "layout": dict(lay)}}


def adapt_btrfs_min(row: Mapping[str, Any]) -> dict[str, Any]:
    values = {"request": row["request"], "effective": row["effective"], "geometry": row["disk_sector_size"]}
    return {"values": values, "types": {},
            "observation": {k: row.get(k) for k in ("mode", "page_size", "disk_sector_size", "request")}}
