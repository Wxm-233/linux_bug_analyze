"""Evaluate two frozen contract implications over manually extracted source facts.

This program does not discover interfaces, infer providers, evaluate Kconfig, or
parse C code. Facts and source references must be supplied independently.
"""

import argparse
import json
from pathlib import Path


def bool_fact(row: dict, name: str):
    value = row.get(name)
    if value is not None and not isinstance(value, bool):
        raise ValueError(f"{row['id']}: {name} must be boolean or null")
    return value


def integer_fact(row: dict, name: str):
    value = row.get(name)
    if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
        raise ValueError(f"{row['id']}: {name} must be nonnegative integer or null")
    return value


def capability(row: dict) -> tuple[str, str]:
    built = bool_fact(row, "interface_built")
    if built is False:
        return "not_applicable", "target interface is not built"
    if built is None:
        return "insufficient", "interface build reachability is unknown"

    paired = bool_fact(row, "paired_native_contract")
    guard = bool_fact(row, "guard_resolved")
    exported = bool_fact(row, "exported")
    if paired is not True:
        return "insufficient", "native ID/map provider contract is not established"
    if guard is not True or exported is None:
        return "insufficient", "export visibility cannot be resolved"
    if not exported:
        return "normal", "applicable interface does not expose these attributes"

    native_id = bool_fact(row, "native_id")
    native_map = bool_fact(row, "native_map")
    if native_id is False or native_map is False:
        return "hit", "attributes exported without both native providers"
    if native_id is None or native_map is None:
        return "insufficient", "provider declaration origin is unknown"
    return "normal", "exported attributes have both native providers"


def representation(row: dict) -> tuple[str, str]:
    built = bool_fact(row, "interface_built")
    if built is False:
        return "not_applicable", "target interface is not built"
    if built is None:
        return "insufficient", "interface build reachability is unknown"

    xarray = bool_fact(row, "xarray_consumer_reachable")
    if xarray is False:
        return "not_applicable", "target path does not reach this xarray page cache"
    if xarray is None:
        return "insufficient", "downstream page-cache consumer is unknown"

    policy = bool_fact(row, "pmd_policy_active")
    if policy is False:
        return "not_applicable", "PMD-page selection is disabled for this input"
    if policy is None:
        return "insufficient", "PMD selection applicability is unknown"

    resolved = bool_fact(row, "selection_resolved")
    selected = bool_fact(row, "pmd_selected")
    pmd_order = integer_fact(row, "pmd_order")
    max_order = integer_fact(row, "max_pagecache_order")
    if resolved is not True or selected is None or pmd_order is None or max_order is None:
        return "insufficient", "selection or target-version order bound is unknown"
    if selected and pmd_order > max_order:
        return "hit", "PMD page selected beyond xarray page-cache order bound"
    if selected:
        return "normal", "selected PMD page fits the order bound"
    return "normal", "applicable selector rejects PMD page"


def run(rows: list[dict]) -> list[dict]:
    result = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            raise ValueError("every fact record needs a string id")
        if row["id"] in seen:
            raise ValueError(f"duplicate id: {row['id']}")
        seen.add(row["id"])
        if row.get("rule") == "C":
            status, reason = capability(row)
        elif row.get("rule") == "R":
            status, reason = representation(row)
        else:
            raise ValueError(f"{row['id']}: unknown rule {row.get('rule')}")
        result.append({"id": row["id"], "rule": row["rule"],
                       "status": status, "reason": reason,
                       "source_refs": row.get("source_refs", []),
                       "fact_method": row.get("fact_method", "unspecified")})
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--facts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.facts.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("records"), list):
        parser.error("facts file must contain a records list")
    output = {"rule_version": 1, "facts_file": str(args.facts),
              "results": run(data["records"])}
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"records": len(output["results"]),
                      "statuses": {name: sum(row["status"] == name for row in output["results"])
                                   for name in ("hit", "normal", "not_applicable", "insufficient")}}))


if __name__ == "__main__":
    main()
