"""Generic kernel fact-bundle adapter (see ``linux_bug_analyze.kernel_facts``).

Input: {"bundle": path relative to the project root, "queries": [{"name", "kind", ...}]}. Each answered
query becomes a fact named ``name``; unanswered queries are omitted (the core then judges insufficient)
and listed in the observation with their reason.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from ..kernel_facts import BUNDLE_SCHEMA, query

VERSION = "kernel_source_facts/1"
ROOT = Path(__file__).resolve().parents[2]


def adapt(spec: Mapping[str, Any]) -> dict[str, Any]:
    path = ROOT / spec["bundle"]
    data = path.read_bytes()
    bundle = json.loads(data)
    if bundle.get("schema") != BUNDLE_SCHEMA:
        raise ValueError("unsupported bundle schema")
    values, unanswered = {}, {}
    for q in spec["queries"]:
        ok, value = query(bundle, q)
        if ok:
            values[q["name"]] = value
        else:
            unanswered[q["name"]] = value
    return {"values": values, "types": {},
            "observation": {"bundle": spec["bundle"], "bundle_sha256": hashlib.sha256(data).hexdigest(),
                            "revision": bundle["revision"], "arch": bundle["spec"]["arch"],
                            "config_sha256": bundle["config_sha256"], "answered": sorted(values), "unanswered": unanswered}}
