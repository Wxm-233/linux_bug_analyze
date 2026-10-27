"""Thin, known-case adapter: explicit reviewed purposes versus conditional effects.

No runtime values are imported and no rejected model text is read.
"""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json

from conditional_matcher import compare_guarantee

HERE = Path(__file__).resolve().parent
INNER = HERE.parents[2]
OUTER = INNER.parent
REL = HERE.relative_to(INNER).as_posix()


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2); f.write("\n")


def load(path): return json.loads(path.read_bytes())


def prepare():
    packet = load(HERE / "documents.json")
    manifest = load(HERE / "packet_manifest.json")
    assert sha(HERE / "documents.json") == manifest["documents_sha256"]
    for path, digest in packet["input_sha256"].items(): assert sha(INNER / path) == digest, path
    docs = {d["id"]: d for d in packet["documents"]}
    def doc_ref(doc_id, start=1, end=None):
        doc = docs[doc_id]
        assert hashlib.sha256(doc["text"].encode()).hexdigest() == doc["text_sha256"]
        end = doc["lines"] if end is None else end
        assert 1 <= start <= end <= doc["lines"]
        return {"artifact": REL + "/documents.json", "document": doc_id,
                "json_pointer": ["documents", list(docs).index(doc_id), "text"],
                "start_line": start, "end_line": end}
    def block_ref(doc_id, block):
        import re
        lines = docs[doc_id]["text"].splitlines()
        hits = [i for i, line in enumerate(lines) if re.fullmatch(r"\s*<bb " + str(block) + r">\s*:\s*", line)]
        assert len(hits) == 1
        start = hits[0]
        end = next((i for i in range(start + 1, len(lines)) if re.fullmatch(r"\s*<bb \d+>\s*:\s*", lines[i])), len(lines))
        return doc_ref(doc_id, start + 1, end)
    def review(refs):
        return {"status": "supported", "origin": "researcher_review", "references": refs,
                "limits": "assistant-reviewed conditional purpose/role; not expert normative gold or runtime proof"}
    input_paths = set(packet["input_sha256"]) | {
        REL + "/documents.json", REL + "/api_contract_evidence.json", REL + "/source_review.md",
        "experiments/case_taxonomy/preparation_effects_20261017/results.json",
        "experiments/case_taxonomy/preparation_effects_20261017/primitive_evidence.json",
        "experiments/case_taxonomy/gimple_cfg_contract_20261019/program_results.json"}
    contexts, requirements = {}, []
    lock_docs = {"old_s390": ("D09", "D10"), "fixed_s390": ("D11", "D12"), "old_x86": ("D13", "D14")}
    descriptions = {
        "target_membership": "若该循环承担保护本次目标rq且无其他已证保护，实际锁集合需覆盖合法目标；这是显式用途假设下的必要候选，不充分。",
        "search_witness": "若本次非单成员搜索的用途要求获得合适见证再继续关系更新，则须存在实际可遍历的非目标自指候选；不推全称入口义务。",
        "post_update_consistency": "对实际到达的第二循环成员，应在本次可选目标写入后检查关系；不把后置检查变成所有成员入口前正确。"}
    for profile, names in lock_docs.items():
        lock, getter = (docs[name] for name in names)
        assert lock["profile"] == getter["profile"] == profile
        assert lock["revision"] == getter["revision"] and lock["configuration_sha256"] == getter["configuration_sha256"]
        context = {"profile": profile, "revision": lock["revision"], "config_sha256": lock["configuration_sha256"], "basis": "noninstrumented_static"}
        contexts[profile] = context
        for kind, statement in descriptions.items():
            refs = [doc_ref(n) for n in names]
            card = {"id": profile + "." + kind, "kind": kind, "context": context,
                    "origin": "researcher_authored", "statement": statement,
                    "review": review(refs), "consumer_purpose_review": review(refs),
                    "target_symbol": "target", "mask_role": "consumer_thread_mask",
                    "normative_scope": "consumer_inferred_under_explicit_purpose_not_universal_contract"}
            if kind in {"search_witness", "post_update_consistency"}:
                cfg_doc = {"old_s390": "D01", "old_x86": "D02"}.get(profile)
                if cfg_doc:
                    assert docs[cfg_doc]["configuration_sha256"] == context["config_sha256"]
                    blocks = (4, 9, 10, 11) if kind == "search_witness" else (17, 18, 19)
                    card["review"] = review([block_ref(cfg_doc, b) for b in blocks])
                    card["consumer_purpose_review"] = review([block_ref(cfg_doc, b) for b in blocks])
                else:
                    card["review"] = {"status": "insufficient", "origin": "researcher_review", "references": refs,
                                      "reason": "no_fixed_configuration_CFG_for_this_control_requirement"}
            if kind == "search_witness" and profile == "old_s390":
                api_ref = {"artifact": REL + "/api_contract_evidence.json", "json_pointer": ["profiles", 0, "excerpts"]}
                card["search_summary"] = {
                    "review": review([block_ref("D01", 4), block_ref("D01", 11), api_ref]), "weight": "set_cardinality",
                    "iteration": "complete_postcondition", "singleton": "bypass_search",
                    "continuation_goal": "obtain_witness_before_update", "continuation_review": review([block_ref("D01", b) for b in (9, 10, 18, 12, 14, 15)]),
                    "domain_condition": "no_set_bits_outside_iteration_domain",
                    "stability_condition": "mask_and_nr_cpu_ids_stable",
                    "summary_origin": "explicit_researcher_API_and_purpose_assumptions_not_automatic_inference"}
            requirements.append(card)
    effects_path = INNER / "experiments/case_taxonomy/preparation_effects_20261017/results.json"
    primitive_evidence = load(INNER / "experiments/case_taxonomy/preparation_effects_20261017/primitive_evidence.json")
    effects = []
    for index, row in enumerate(load(effects_path)["results"]):
        profile = row["profile"]; context = contexts[profile]; assert row["revision"] == context["revision"]
        provider = load(INNER / ("experiments/case_taxonomy/provider_consumer_binding_20261017/" + profile + ".json"))
        primitive = next(p for p in primitive_evidence["profiles"] if p["profile"] == profile)
        provider_config = next(p["sha256"] for p in provider["selected_artifacts"] if p["path"].endswith("/build/.config"))
        primitive_config = next(p["sha256"] for p in primitive["bound_inputs"] if p["path"].endswith("/build/.config"))
        assert provider["revision"] == row["revision"] and provider_config == primitive_config == context["config_sha256"]
        for suffix in ("/arch/s390/kernel/topology.i", "/include/generated/autoconf.h"):
            assert next(p["sha256"] for p in provider["selected_artifacts"] if p["path"].endswith(suffix)) == next(p["sha256"] for p in primitive["bound_inputs"] if p["path"].endswith(suffix))
        a = row["under_explicit_assumptions"]
        complete = a["status"] == "conditional_postcondition" and row["path_status"] == "structural_terminal"
        if complete: assert type(a["target_membership"]) is bool and ("target" in a["postcondition"]) == a["target_membership"]
        effects.append({"id": profile + ".path" + str(row["path_index"]), "context": context,
                        "status": a["status"], "path_status": row["path_status"], "postcondition_complete": complete,
                        "postcondition": a["postcondition"], "assumed_premises": a["assumed_premises"],
                        "target_symbol": "target", "mask_role": "consumer_thread_mask",
                        "role_review": review([{"artifact": "experiments/case_taxonomy/preparation_effects_20261017/results.json",
                                                "json_pointer": ["results", index, "trace"]}, doc_ref("D10" if profile == "old_s390" else "D12")]),
                        "condition_guards": row["guard_alternatives"], "actual_branch_selected": row["actual_branch_selected"],
                        "source_effect_index": index, "runtime_target_identity": "unknown", "consumer_deadline_content": "unknown"})
        effects[-1]["source_config_binding"] = {"provider_config_sha256": provider_config,
                                               "primitive_config_sha256": primitive_config,
                                               "consumer_config_sha256": context["config_sha256"],
                                               "topology_i_and_autoconf_match": True}
    effects.append({"id": "old_x86.no_static_effect", "context": contexts["old_x86"], "status": "insufficient",
                    "path_status": "not_collected", "postcondition_complete": False, "postcondition": None,
                    "condition_guards": [], "actual_branch_selected": "unknown"})
    write(HERE / "matching_inputs.json", {"requirements": requirements, "effects": effects,
          "input_sha256": {path: sha(INNER / path) for path in sorted(input_paths)},
          "role_binding_scope": "symbolic correspondence under explicit premises; no physical pointer identity",
          "model_requirement_adoptions": 0, "runtime_values_imported": False})
    print(json.dumps({"status": "matching_inputs_prepared_no_comparison", "requirements": len(requirements), "provider_path_records": len(effects)}))


def execute():
    packet = load(HERE / "matching_inputs.json")
    for path, digest in packet["input_sha256"].items(): assert sha(INNER / path) == digest, path
    rows = []
    for effect in packet["effects"]:
        for requirement in packet["requirements"]:
            if requirement["context"] != effect["context"]: continue
            result = compare_guarantee(requirement, effect, effect["context"])
            rows.append({"effect_id": effect["id"], "requirement_id": requirement["id"], "comparison": result})
    write(HERE / "matching_results.json", {"scope": "one known case, reviewed symbolic path/property comparisons, not new experiments or defects",
          "input_sha256": sha(HERE / "matching_inputs.json"), "matcher_sha256": sha(HERE / "conditional_matcher.py"),
          "rows": rows, "counts": dict(Counter(r["comparison"]["status"] for r in rows)),
          "all_actual_verdicts_insufficient": all(r["comparison"]["actual_verdict"] == "insufficient" for r in rows),
          "automatic_requirement_extractions": 0, "new_defects": 0, "formal_independent_positive_normal": [0, 0]})
    print(json.dumps({"comparisons": len(rows), "counts": dict(Counter(r["comparison"]["status"] for r in rows))}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--prepare", action="store_true")
    args = parser.parse_args()
    prepare() if args.prepare else execute()
