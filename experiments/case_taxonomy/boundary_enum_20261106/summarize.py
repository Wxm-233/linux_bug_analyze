"""Aggregate frozen boundary results and descriptive historical sample hits."""
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARCHES = ("riscv", "arm64", "x86_64")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def identity(s):
    return (s["kind"], s["name"], s["usr"], tuple(s["definition"][k] for k in ("file", "line", "column")))


def sample_hits(symbols):
    labels_path = HERE.parent / "boundary_taxonomy_20261106/labels.json"
    source_path = HERE.parent / "cross_arch_sample_set_20261102/labels_v2_1.json"
    labels = [r for r in read(labels_path) if r["check"] != 0]
    original = {r["id"]: r for r in read(source_path)}
    assert len(labels) == 120 and len({r["id"] for r in labels}) == 120
    boundary_functions = {identity(s) for s in symbols if s["kind"] == "function"}
    direct = defaultdict(list)
    for s in symbols:
        direct[(s["definition"]["file"], s["name"])].append({"mode": "boundary_symbol", "symbol": s})
    with gzip.open(HERE / "direct_calls_riscv.jsonl.gz", "rt", encoding="utf-8") as stream:
        for line in stream:
            call = json.loads(line)
            if identity(call["caller"]) in boundary_functions:
                s = call["callee"]
                direct[(s["definition"]["file"], s["name"])].append({"mode": "direct_callee_of_boundary_function", "call": call})
    rows = []
    for label in labels:
        source = original[label["id"]]
        evidence = []
        for function in source["functions"]:
            file, sep, name = function.rpartition(":")
            assert sep and file in source["files"], function
            evidence.extend({"sample_function": function, **e} for e in direct.get((file, name), []))
        rows.append({"id": label["id"], "check": label["check"], "commit": label["commit"],
                     "functions": source["functions"], "files": source["files"],
                     "hit": bool(evidence), "evidence": evidence,
                     "unmatched_reason": None if evidence else (
                         "empty_functions_no_independently_extracted_symbol" if not source["functions"] else "no_exact_file_and_name_match")})
    by_check = {}
    for check in (1, 2, 3):
        group = [r for r in rows if r["check"] == check]
        by_check[str(check)] = {"total": len(group), "hits": sum(r["hit"] for r in group),
                                "empty_functions": sum(not r["functions"] for r in group),
                                "miss_ids": [r["id"] for r in group if not r["hit"]]}
    result = {"method": "exact historical file+function name against RISC-V boundary definitions or one direct call from a boundary function; no file-only matches, no rename inference, empty functions are misses",
              "scope": "descriptive cross-version presence, not bug detection recall",
              "inputs_sha256": {str(p.relative_to(HERE.parent)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (labels_path, source_path)},
              "by_check": by_check, "hits": sum(r["hit"] for r in rows), "total": len(rows), "samples": rows}
    write("sample_hits.json", result)
    return result


def main():
    results = {a: read(HERE / f"result_{a}.json") for a in ARCHES}
    symbols = {a: read(HERE / f"symbols_{a}.json") for a in ARCHES}
    timings = [json.loads(line) for line in (HERE / "execution/timings.jsonl").read_text().splitlines()]
    initial = read(HERE / "execution/initial_timings.json")
    for arch in ARCHES:
        results[arch]["measured_execution_seconds"] = round(
            sum(t["elapsed_seconds"] for t in timings if t["args"][1] == arch)
            + (sum(t["seconds"] for t in initial["batches"]) if arch == initial["arch"] else 0), 3)
        results[arch]["timing_scope"] = "sum of scan and merge command wall times, excludes between-batch pauses; initial RISC-V 576 units exclude preflight/startup"
        counts = Counter()
        unique = set()
        with gzip.open(HERE / f"boundary_{arch}.jsonl.gz", "rt", encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                key = (tuple(row["use"][k] for k in ("file", "line", "column")), row["action"], row["symbol_id"])
                assert key not in unique, key
                unique.add(key)
                assert row["units"] == sorted(set(row["units"]))
                counts[row["symbol_id"]] += 1
        assert len(unique) == results[arch]["points"]
        assert len(counts) == len(symbols[arch]) == results[arch]["symbols"]
        assert all(counts[s["id"]] == s["points"] for s in symbols[arch])
        assert results[arch]["parsed_units"] + results[arch]["parse_failed_units"] == results[arch]["c_units"]
        results[arch]["artifact_consistency_verified"] = True
    common = set.intersection(*({(s["name"], s["kind"], s["direction"]) for s in symbols[a]} for a in ARCHES))
    write("common_symbols.json", [dict(zip(("name", "kind", "direction"), s)) for s in sorted(common)])
    samples = sample_hits(symbols["riscv"])
    stats = {"status": "completed", "selftest": read(HERE / "selftest/result.json"),
             "architectures": results, "common_symbols": len(common),
             "common_symbols_identity": ["name", "kind", "direction"],
             "sample_hits_by_check": samples["by_check"], "sample_hits": samples["hits"],
             "model_calls": 0, "new_confirmed_bugs": 0, "new_suspicions": 0}
    write("stats.json", stats)
    print(json.dumps({"common_symbols": len(common), "sample_hits_by_check": samples["by_check"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
