"""Summarize machine facts and attach only uniquely mapped prior local edges.

No source-query truth score, runtime inference or alteration of either analysis.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    result = json.loads((HERE / "program_results.json").read_bytes())
    prior_path = HERE.parent / "gimple_local_flow_20261018/program_results.json"
    assert sha(prior_path) == "fb34eb9a1fabbe6d7b6e762ff1ed4860a39bec1665aab9fdab171b41a28805c4"
    previous = json.loads(prior_path.read_bytes())
    rows = []
    for document in result["documents"]:
        analysis = document["analysis"]
        prior = next(d["analysis"] for d in previous["documents"] if d["id"] == document["id"])
        bindings = {b["local_event"]: b for b in analysis["event_bindings"]}
        attached = []
        for edge in prior["dependencies"]:
            use, definition = bindings.get(edge["use_event"]), bindings.get(edge["definition_event"])
            if use and definition and use["status"] == definition["status"] == "unique":
                attached.append(dict(edge, use_cfg_event=use["cfg_event"], definition_cfg_event=definition["cfg_event"],
                                     use_block=use["block"], definition_block=definition["block"]))
        rows.append({"id": document["id"], "status": analysis["status"], "blocks": len(analysis["blocks"]),
                     "normal_edges": len(analysis["edges"]), "explicit_branches": len(analysis["branch_polarity"]),
                     "compiler_loops_including_synthetic_root": len(analysis["loops"]),
                     "binding_status": dict(Counter(b["status"] for b in analysis["event_bindings"])),
                     "insufficient_binding_reasons": dict(Counter(b["reason"] for b in analysis["event_bindings"] if b["status"] != "unique")),
                     "relation_counts": dict(Counter(r["kind"] for r in analysis["relations"])),
                     "effect_unknown_counts": dict(Counter(u.get("kind", u.get("reason")) for u in analysis["unknowns"])),
                     "prior_local_dependencies": len(prior["dependencies"]), "local_dependencies_bound_at_both_ends": len(attached),
                     "bound_dependencies_in_same_block": sum(e["use_block"] == e["definition_block"] for e in attached),
                     "bound_local_dependencies": attached,
                     "scope": "prior same-region may-dependencies located in compiler blocks; not cross-block reaching-def or runtime values"})
    summary = {"scope": "N2.13 known-source structural control development", "profiles": rows,
               "method_tests": 14, "previous_local_method_regression_tests": 15,
               "compiler_invocations": 2, "kernel_builds": 0, "kernel_runs": 0, "paid_model_calls": 0,
               "new_confirmed_defects": 0, "formal_independent_positive_normal": [0, 0],
               "method_file_sha256": {str(p.relative_to(ROOT)): sha(p) for p in [
                   ROOT / "linux_bug_analyze/gimple_cfg_facts.py", ROOT / "tests/test_gimple_cfg_facts.py", HERE / "run_analysis.py"]},
               "whole_contract_proved": False, "runtime_reachability_proved": False,
               "next": "N2.14 conditional public requirements and architecture preparation matching"}
    with (HERE / "results_summary.json").open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2); stream.write("\n")
    print(json.dumps({"profiles": [{"id": r["id"], "blocks": r["blocks"], "edges": r["normal_edges"],
                                  "unique_event_bindings": r["binding_status"].get("unique", 0),
                                  "bound_local_dependencies": r["local_dependencies_bound_at_both_ends"]} for r in rows]}))


if __name__ == "__main__": main()
