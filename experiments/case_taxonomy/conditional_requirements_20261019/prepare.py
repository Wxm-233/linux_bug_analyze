"""Prepare one new known-case conditional-requirement task, without API calls."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
INNER = HERE.parents[2]
OUTER = INNER.parent


def sha(raw): return hashlib.sha256(raw).hexdigest()


def write(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as f:
        f.write(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    inputs, documents = {}, []
    def load(relative):
        raw = (INNER / relative).read_bytes(); inputs[relative] = sha(raw)
        return json.loads(raw)
    def add(text, profile, revision, kind, source, pointer, config=None, function=None):
        documents.append({"id": "D" + str(len(documents) + 1).zfill(2), "profile": profile,
                          "revision": revision, "kind": kind, "configuration_sha256": config,
                          "source_artifact": source, "json_pointer": pointer, "function": function,
                          "text": text, "text_sha256": sha(text.encode()), "lines": len(text.splitlines())})
    cfg_stage = "experiments/case_taxonomy/gimple_cfg_contract_20261019/"
    for profile in ("old_s390", "old_x86"):
        source = cfg_stage + profile + ".consumer.cfg.txt"
        raw = (INNER / source).read_bytes(); inputs[source] = sha(raw)
        binding = load(cfg_stage + profile + ".consumer_binding.json")
        assert inputs[source] == binding["record_sha256"]
        add(raw.decode(), profile, binding["revision"], "compiler_normal_CFG_noninstrumented", source,
            None, binding["config"]["sha256"], binding["function"])
    for profile in ("old_s390", "fixed_s390"):
        source = "experiments/case_taxonomy/provider_consumer_binding_20261017/" + profile + ".json"
        packet = load(source)
        config = next(x["sha256"] for x in packet["selected_artifacts"] if x["path"].endswith("/build/.config"))
        for unit, name in [("arch/s390/kernel/topology.i", "cpu_thread_map"),
                           ("arch/s390/kernel/topology.i", "update_cpu_masks"),
                           ("arch/s390/kernel/smp.i", "smp_start_secondary")]:
            row = packet["functions_by_translation_unit"][unit][name]
            assert sha(row["text"].encode()) == row["sha256"]
            add(row["text"], profile, packet["revision"], "configured_definition_noninstrumented", source,
                ["functions_by_translation_unit", unit, name, "text"], config, name)
    for profile in ("old_s390", "fixed_s390", "old_x86"):
        source = "experiments/case_taxonomy/consumer_preprocessing_20261016/" + profile + ".json"
        packet = load(source)
        config = next(x["sha256"] for x in packet["selected_artifacts"] if x["path"].endswith("/kernel.config"))
        for name in ("sched_core_lock", "cpu_smt_mask"):
            row = packet["functions"][name]; assert sha(row["text"].encode()) == row["sha256"]
            add(row["text"], profile, packet["revision"], "configured_definition_noninstrumented", source,
                ["functions", name, "text"], config, name)
    source = "experiments/case_taxonomy/preparation_eligibility_20261016/source_material.json"
    original = load(source)
    for index, row in enumerate(original["documents"]):
        if row.get("function") == "smp_callin" and row.get("path", "").startswith("arch/x86/"):
            add(row["text"], "old_x86_original_source", row["revision"], "unconfigured_original_source", source,
                ["documents", index, "text"], None, row["function"])
    assert len(documents) == 15, len(documents)
    packet = {"scope": "already-read development, noninstrumented definitions and CFG; original x86 callin not a configured guarantee",
              "documents": documents, "input_sha256": inputs,
              "excluded": ["historical runtime values", "old model responses", "assistant source review", "reference predicates"]}
    write(HERE / "documents.json", packet)
    protocol = {"task": "N2.14 conditional public requirements and architecture preparation matching", "date": "2026-10-19",
                "known_case_development": True, "new_source_collection": 0, "compiler_invocations": 0, "kernel_runs": 0,
                "primary_client": "native Windows Claude Code 2.1.301", "primary_model": "AWS-Claude-Opus-5.5",
                "new_top_level_tasks": 1, "per_task_ceiling": 1000000, "runner_retry_count": 0,
                "failure_policy": "preserve incomplete/refused output; do not continue or rewrite to recover it",
                "evaluation_scope": "reference binding and reviewed conditional compatibility; not independent detection",
                "external_review": "source_review.md predates model response; assistant review, not expert gold"}
    write(HERE / "protocol_pre.json", protocol)
    folder = OUTER / "模型调用测试/2026-10-19/n214_conditional_requirements"
    folder.mkdir(parents=True, exist_ok=False)
    instructions = '''请依据下面已知Linux案例的材料，提出最多3项条件化公共要求候选，并分析架构准备路径怎样可能满足或错过它。目标是内核正确性研究，不生成补丁、利用或触发程序。不使用工具，不补画未给出的函数体或运行事实。
这些是已读开发材料，不是独立测试。编译器正常控制图只表示潜在控制转移，不证明实际可达、调用/asm必返回或对象同一。不同revision、配置、原始源与配置定义分别标注，不把它们自动合成同一次执行。没有提供运行值、既有模型回答或研究者要求答案。
请从源码用途与控制事实推导要求，而非把代码目前怎么做直接当唯一正确规范。区分条件、要求、局部事实、用途依据、外部规范仍缺的地方，以及从提供方到公共消费的对象/资格/期限联系。无法证明的前提明确保留，不能将提供者未准备转换成消费者不适用。
只输出一个JSON对象，schema=n214_conditional_candidates_v1，candidates是最多3项的数组。每项字段为id、condition、requirement、basis（structural_fact/consumer_inferred/external_requirement_needed三者之一）、evidence（对象数组，每个document,start_line,end_line均为本包局部行号，闭区间且单段不超过32行）、provider_assessments（对象数组，每个profile,assessment,reason,evidence，其中assessment为conditional_conflict/conditional_compatible/insufficient/not_applicable之一）、unknowns（字符串数组）。可另加limits字符串数组。无需压缩解释；参考范围须精确。引用绑定不等于语义正确，不输出任何实际运行已满足/已违反的结论。
'''
    blocks = []
    for doc in documents:
        meta = {k: v for k, v in doc.items() if k != "text"}
        blocks.append(json.dumps(meta, ensure_ascii=False) + "\n" + "\n".join(f"{i} | {line}" for i, line in enumerate(doc["text"].splitlines(), 1)))
    prompt = instructions + "\n\n" + "\n\n".join(blocks) + "\n"
    write(folder / "prompt.md", prompt)
    write(HERE / "packet_manifest.json", {"documents_sha256": sha((HERE / "documents.json").read_bytes()),
          "prompt_sha256": sha(prompt.encode()), "prompt_bytes": len(prompt.encode()), "document_count": len(documents),
          "model_directory": folder.relative_to(OUTER).as_posix(), "protocol_sha256": sha((HERE / "protocol_pre.json").read_bytes())})
    write(HERE / "notes_before.json", {name: sha((OUTER / name).read_bytes()) for name in ("当前代办.md", "当前研究方向与进展.md")})
    print(json.dumps({"status": "prepared_no_API", "documents": len(documents), "prompt_bytes": len(prompt.encode()), "model_directory": str(folder)}))


if __name__ == "__main__": main()
