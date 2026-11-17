"""Checkpoint the same merge algorithm without changing scan/cache identity.

Only load our own local pickle checkpoint under the input-bound cache directory.
Definition collection is one pass; reference resolution advances in bounded batches.
"""
from collections import Counter, defaultdict
import os
import pickle
import sys
import tempfile
from pathlib import Path
import enumerate as e


def checkpoint_path(build):
    return build.cache / ("merge_" + e.sha256(Path(__file__)) + ".pickle")


def save(path, state):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        pending = Path(stream.name)
        pickle.dump(state, stream, protocol=pickle.HIGHEST_PROTOCOL)
    pending.replace(path)


def initialize(build):
    entries = [entry for entry in build.entries if entry.is_c]
    if any(not build.unit_path(entry).is_file() for entry in entries):
        raise ValueError("All C units need a recorded status before merge")
    paths = e.Paths(build.source, build.output)
    objects, archive = e.object_evidence(build, paths)
    definitions, by_object, statuses = defaultdict(dict), defaultdict(set), Counter()
    for index, (entry, result) in enumerate(e.unit_records(build, entries), 1):
        statuses[result["status"]] += 1
        if result["status"] == "ok":
            obj = str(entry.output.relative_to(build.output))
            for number in result["definitions"]:
                symbol = e.Symbol.from_row(result["symbols"][number])
                candidates = definitions[(symbol.kind, symbol.usr)]
                candidates[symbol] = obj in archive or candidates.get(symbol, False)
                by_object[(obj, symbol.kind, symbol.link_name)].add(symbol)
        if index % 512 == 0:
            print(f"{build.arch}: definitions {index}/{len(entries)}", flush=True)
    if not statuses["ok"]:
        raise ValueError("No successfully parsed C unit")
    return dict(objects=objects, archive=archive, definitions=definitions, by_object=by_object,
                statuses=statuses, points=e.BoundaryPoints(), calls={}, units=[], missing=Counter(),
                missing_units=0, visible_macros=0, indirect_calls=0, offset=0)


def advance(build, state, limit):
    entries = [entry for entry in build.entries if entry.is_c]
    paths = e.Paths(build.source, build.output)
    batch = entries[state["offset"]:state["offset"] + limit]
    for entry, result in e.unit_records(build, batch):
        obj = str(entry.output.relative_to(build.output))
        unit = {"id": entry.number, "source": paths.name(str(entry.source)), "object": obj,
                "status": result["status"], "severity_counts": result.get("severity_counts"),
                "diagnostics": result.get("diagnostics", []), "unresolved": None}
        state["units"].append(unit)
        if result["status"] == "ok":
            local = [e.Symbol.from_row(row) for row in result["symbols"]]
            resolved = {}
            counts = Counter(result["unresolved"])
            examples = result["unresolved_examples"]
            state["visible_macros"] += result["visible_macros"]
            state["indirect_calls"] += result["indirect_calls"]
            for at, action, number, owner in result["refs"]:
                at = (sys.intern(at[0]), at[1], at[2])
                if number not in resolved:
                    resolved[number] = e.resolve(local[number], obj in state["archive"], state["definitions"],
                                                  state["by_object"], state["objects"]["weak_overrides"])
                target, reason = resolved[number]
                if target is None:
                    counts[reason] += 1
                    if len(examples) < 20:
                        examples.append([reason, local[number].name, at])
                    continue
                if owner is not None:
                    state["calls"].setdefault((local[owner], target), (at, entry.number))
                cross = e.direction(at[0], target.at[0])
                if cross is not None:
                    state["points"].add(at, action, target, cross, entry.number)
            unit.update(unresolved=dict(counts), unresolved_examples=examples,
                        visible_macros=result["visible_macros"], indirect_calls=result["indirect_calls"])
            state["missing"].update(counts)
            state["missing_units"] += bool(counts)
        state["offset"] += 1
        if state["offset"] % 256 == 0:
            print(f"{build.arch}: references {state['offset']}/{len(entries)}", flush=True)
    return state["offset"] == len(entries)


def finalize(build, state, output):
    entries = [entry for entry in build.entries if entry.is_c]
    assert state["offset"] == len(entries)
    objects, calls, missing = state["objects"], state["calls"], state["missing"]
    summary = state["points"].emit(output, build.arch)
    e.save_json(output / f"units_{build.arch}.json.gz", state["units"])
    e.save_json(output / f"object_evidence_{build.arch}.json.gz", objects)
    e.save_lines(output / f"direct_calls_{build.arch}.jsonl.gz", (
        {"caller": e.symbol_json(caller), "callee": e.symbol_json(callee),
         "example_use": e.location_json(at), "unit": unit}
        for (caller, callee), (at, unit) in calls.items()))
    summary.update({
        "inputs": build.inputs, "compile_commands_entries": len(build.entries), "c_units": len(entries),
        "parsed_units": state["statuses"]["ok"], "parse_failed_units": len(entries) - state["statuses"]["ok"],
        "unit_statuses": dict(state["statuses"]), "units_with_unresolved_refs": state["missing_units"],
        "unresolved_refs": sum(missing.values()), "unresolved_by_reason": dict(sorted(missing.items())),
        "visible_macro_instantiations": state["visible_macros"], "nested_macro_expansions_not_exposed": None,
        "indirect_calls_without_target_resolution": state["indirect_calls"], "direct_call_relations": len(calls),
        "object_evidence": {"objects_scanned": objects["objects_scanned"], "weak_overrides": len(objects["weak_overrides"]),
                            "asm_boundary_refs": len(objects["asm_boundaries"]), "asm_unresolved_refs": len(objects["asm_unresolved"]),
                            "asm_undefined_refs": objects["asm_undefined_references"]}})
    e.save_json(output / f"result_{build.arch}.json", summary)
    return summary


def main():
    arch = sys.argv[1]
    assert arch in e.ARCHES
    build = e.kernel_build(arch)
    path = checkpoint_path(build)
    if not path.exists():
        state = initialize(build)
        save(path, state)
        print(f"{arch}: definition checkpoint saved; rerun to process reference batches", flush=True)
        return
    with path.open("rb") as stream:
        state = pickle.load(stream)
    if state.get("complete"):
        print(f"{arch}: merge already complete")
        return
    complete = advance(build, state, int(sys.argv[2]) if len(sys.argv) > 2 else 1024)
    if complete:
        result = finalize(build, state, e.HERE)
        state["complete"] = True
        print(f"{arch}: merged {result['symbols']} symbols and {result['points']} points", flush=True)
    save(path, state)
    print(f"{arch}: checkpoint saved at {state['offset']} references units", flush=True)


if __name__ == "__main__":
    main()
