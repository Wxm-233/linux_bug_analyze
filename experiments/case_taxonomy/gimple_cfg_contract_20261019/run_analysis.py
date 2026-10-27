"""Bound the new CFG record to the previous local facts and identical inputs."""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from linux_bug_analyze.gimple_cfg_facts import analyze_cfg


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    old_stage = HERE.parent / "compiler_consumer_frontend_20261018"
    local_stage = HERE.parent / "gimple_local_flow_20261018"
    assert sha(local_stage / "method_baseline.json") == "a89db3ef1e89fe25249a436f316f1463d205a7ba5e37ba9d85da0cca1718f82a"
    old_method = json.loads((local_stage / "method_baseline.json").read_bytes())
    for path, digest in old_method["files"].items(): assert sha(ROOT / path) == digest, path
    old_plan = json.loads((old_stage / "command_plan.json").read_bytes())
    assert sha(old_stage / "command_plan.json") == "fb174a23f1126e899099839d503af7148f62678e681a0e6b5ec4d9f8c07ce6af"
    assert sha(local_stage / "program_results.json") == "fb34eb9a1fabbe6d7b6e762ff1ed4860a39bec1665aab9fdab171b41a28805c4"
    local_results = json.loads((local_stage / "program_results.json").read_bytes())
    documents = []
    for profile in ("old_s390", "old_x86"):
        path = HERE / (profile + ".consumer.cfg.txt")
        binding_path = HERE / (profile + ".consumer_binding.json")
        binding = json.loads(binding_path.read_bytes())
        old_profile = next(x for x in old_plan["profiles"] if x["profile"] == profile)
        for key in ("profile", "arch", "revision", "source_i", "config"):
            assert binding[key] == old_profile[key], key
        assert sha(path) == binding["record_sha256"]
        previous = next(x for x in local_results["documents"] if x["id"] == profile)
        assert previous["input_sha256"] == previous["analysis"]["source_sha256"] == sha(old_stage / (profile + ".consumer.gimple.txt"))
        analysis = analyze_cfg({"id": profile, "path": str(path.relative_to(ROOT)),
                                "revision": binding["revision"], "text": path.read_text(encoding="utf-8")},
                               local_analysis=previous["analysis"])
        documents.append({"id": profile, "binding_sha256": sha(binding_path),
                          "same_input_config_as_local_facts": True,
                          "local_source_sha256": previous["input_sha256"], "analysis": analysis})
    result = {"scope": "N2.13 known-source compiler normal CFG development",
              "documents": documents, "paid_calls": 0, "compiler_invocations": 2,
              "kernel_runs": 0, "new_confirmed_defects": 0, "formal_independent_positive_normal": [0, 0]}
    with (HERE / "program_results.json").open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False); f.write("\n")
    print(json.dumps({"profiles": [{"id": d["id"], "status": d["analysis"].get("status")} for d in documents]}))


if __name__ == "__main__": main()
