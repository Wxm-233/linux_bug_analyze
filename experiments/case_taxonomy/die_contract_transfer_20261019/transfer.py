"""Known-case source/runtime adapters for the unchanged contract evaluator."""
from pathlib import Path
from collections import Counter
import argparse
import copy
import hashlib
import json
import re
import sys

HERE = Path(__file__).resolve().parent
INNER = HERE.parents[2]
OUTER = INNER.parent
BASE = HERE.parent / "die_arch_contract_20261013"
sys.path.insert(0, str(INNER))
from linux_bug_analyze.contract_protocol import CLAIM_ROLES, evaluate_contract
from projection import project_static, project_runtime

OLD = "555a0ce4558d87d5b97c4321f34b19e051c7b0c1"
FIXED = "2c4dcd7fd57b20a21b65da04d89c38a7217d79cf"


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path): return json.loads(path.read_bytes())
def save(path, value):
    with path.open("x", encoding="utf-8") as f: json.dump(value, f, ensure_ascii=False, indent=2); f.write("\n")


def config_value(text, key):
    yes = re.findall(r"(?m)^" + re.escape(key) + r"=(.*)$", text)
    no = re.findall(r"(?m)^# " + re.escape(key) + r" is not set$", text)
    if len(yes) == 1 and not no and yes[0] in {"y", "n"}: return yes[0] == "y"
    if len(no) == 1 and not yes: return False
    return None


def native_body_review(pp, sources):
    """Exact reviewed known definitions, not arbitrary architecture semantics."""
    normalized = lambda value: re.sub(r"\s+", "", value)
    docs = {d["id"]: d for d in sources["documents"]}
    approved = {}
    for name in ("topology_die_id", "topology_die_cpumask"):
        approved[name] = {}
        for doc_id in ("E_x86", "E_fallback"):
            hits = [line[line.index("#define"):].strip() for line in docs[doc_id]["text"].splitlines()
                    if re.search(r"#define\s+" + name + r"\(", line)]
            assert len(hits) == 1, (doc_id, name)
            approved[name][doc_id] = normalized(hits[0])
    for name, allowed in approved.items():
        rows = pp["macro_definitions"].get(name, [])
        if len(rows) != 1: return False
        row = rows[0]
        origin = "E_x86" if row["file"].endswith("/arch/x86/include/asm/topology.h") else "E_fallback" if row["file"].endswith("/include/linux/topology.h") else None
        if origin is None or normalized(row["definition"]) != allowed[origin]: return False
    return True


def validate_runtime_identity(profile, boot, build, events):
    """Bind archived observation identity, not the old expected verdict."""
    assert build["status"] == "READY"
    assert boot["profile"] == build["profile"] == profile
    for key in ("revision", "arch", "release", "image_sha256", "init_source_sha256", "init_binary_sha256", "initrd_sha256"):
        assert boot[key] == build[key], key
    assert build["source_c_modified"] is False
    receipt = boot["qemu_receipt"]
    assert receipt["status"] == "finished" and type(receipt["exit_code"]) is int and receipt["exit_code"] == 0
    assert type(receipt["attempt"]) is int and receipt["attempt"] == 1
    archive = "/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/die_arch_contract_20261013/runtime/profiles/" + profile
    assert receipt["stdout"] == archive + "/qemu_boot.stdout.log"
    assert receipt["stderr"] == archive + "/qemu_boot.stderr.log"
    argv = boot["qemu_argv"]
    assert receipt["argv"] == argv
    for option, expected in (("-kernel", build["image"]), ("-initrd", build["initrd"])):
        assert argv.count(option) == 1 and argv[argv.index(option) + 1] == expected
    assert argv.count("-append") == 1
    arguments = argv[argv.index("-append") + 1].split()
    assert [v for v in arguments if v.startswith("die_case=")] == ["die_case=" + profile]
    uname = [e for e in events if e.get("event") == "uname"]
    commands = [e for e in events if e.get("event") == "file_read" and e.get("path") == "/proc/cmdline"]
    assert len(uname) == len(commands) == 1
    assert uname[0]["release"] == build["release"]
    assert uname[0]["machine"] == {"s390": "s390x", "x86_64": "x86_64"}[build["arch"]]
    assert [v for v in commands[0]["raw"].split() if v.startswith("die_case=")] == ["die_case=" + profile]
    return True


def envelope(profile, revision, basis, context, projection, sysfs, evidence_path):
    ident = "die." + context
    origins = {k: "researcher_authored" for k in ("scope", "relation", "symbols", "required_claims", "authority_kind")}
    symbols = {name: {"type": "bool", "role": "configuration" if name != "listed_any" else "observation"}
               for name in ("sysfs_enabled", "native_id", "native_mask", "listed_any")}
    contract = {"schema": "architecture_contract_v1", "id": ident, "revision": revision,
                "authority_kind": "consumer_inferred", "sufficient_for_correctness": False,
                "field_origins": origins, "symbols": symbols,
                "required_claims": {role: "review." + role for role in CLAIM_ROLES},
                "scope": {"symbol": "sysfs_enabled"},
                "relation": {"op": "or", "args": [{"op": "not", "args": [{"symbol": "listed_any"}]},
                    {"op": "and", "args": [{"symbol": "native_id"}, {"symbol": "native_mask"}]}]}}
    object_id = context + ".die_attribute_group"
    sample = context + (".compiled_table" if basis == "source_projection" else ".probe_read_window")
    deadline = context + ".potential_sysfs_content_read"
    record = {"id": ident + ".record", "revision": revision, "basis": basis, "context_id": context,
              "object_id": object_id, "sample_event": sample, "deadline_event": deadline,
              "sample_kind": "sample", "facts": {},
              "observation_binding": {"object_id": object_id, "event_id": sample, "deadline_id": deadline, "claim": "review.observation"}}
    policy_path = HERE / "policy_card.md"
    documents = {
        "evidence": {"context_revision": revision, "source_revision": revision,
                     "path": str(evidence_path.relative_to(INNER)), "start_line": 1,
                     "end_line": len(evidence_path.read_text(encoding="utf-8").splitlines()), "sha256": sha(evidence_path)},
        "policy_application": {"context_revision": revision, "source_policy_revision": FIXED,
                               "path": str(policy_path.relative_to(INNER)), "start_line": 1,
                               "end_line": len(policy_path.read_text(encoding="utf-8").splitlines()), "sha256": sha(policy_path),
                               "interpretation": "counterfactual_policy_from_fixed" if revision == OLD else "repair_policy_application"}}
    refs = lambda doc: [{"document": doc, "start_line": 1, "end_line": documents[doc]["end_line"]}]
    ledger = {"contract_id": ident, "revision": revision, "basis": basis, "context_id": context,
              "field_origins": copy.deepcopy(origins), "documents": documents, "claims": {},
              "source_policy_revision": FIXED, "historical_normative_verdict": "insufficient"}
    statements = {
        "authority": "Explicit researcher application of repair group policy; parent application is counterfactual, not an old ABI prohibition.",
        "interface": "Selected public die trio, evaluated at this evidence tier; not hardware topology truth.",
        "consumer_requirement": "Only the reviewed publication/source-gate implication is required by the selected policy scenario.",
        "provider_binding": "Source-origin candidates also require exact reviewed macro bodies and this configuration; no physical value claim.",
        "object_binding": "Compiled attribute group or selected observed CPU attribute group, never a different configuration's object.",
        "deadline_binding": "Prospective public content use is a distinct conditional sink, not an observed execution or sample-to-deadline bridge.",
        "applicability": "Scope uses only actual SYSFS configuration; provider availability does not disable the consumer scope."}
    for role in CLAIM_ROLES:
        ledger["claims"]["review." + role] = {"role": role, "status": "supported", "origin": "researcher_review",
             "context_id": context, "statement": statements[role], "references": refs("policy_application" if role in {"authority", "consumer_requirement"} else "evidence")}
    ledger["claims"]["review.authority"].update(authority_kind="consumer_inferred", supports_requirement="review.consumer_requirement", source_policy_revision=FIXED)
    for role, expr in (("applicability", "scope"), ("consumer_requirement", "relation")):
        ledger["claims"]["review." + role].update(expression=copy.deepcopy(contract[expr]), symbols=copy.deepcopy(symbols))
    for role in ("consumer_requirement", "provider_binding", "object_binding", "deadline_binding"):
        ledger["claims"]["review." + role]["object_id"] = object_id
    ledger["claims"]["review.deadline_binding"].update(event_id=deadline, event_kind="content_consumption", actual_occurrence_proved=False)
    binding = {"object_id": object_id, "event_id": sample, "deadline_id": deadline, "context_id": context, "event_kind": "sample"}
    ledger["claims"]["review.observation"] = {"role": "observation_binding", "status": "supported", "origin": "researcher_review",
       "context_id": context, "statement": "Sample identity limited to this evidence context; no actual content-consumption deadline is observed.",
       "references": refs("evidence"), "binding": binding}
    values = {"sysfs_enabled": sysfs, "native_id": projection.get("id_native"),
              "native_mask": projection.get("mask_native"), "listed_any": projection.get("listed_any")}
    if projection.get("status") != "supported":
        # Diagnostics may retain useful partial values; they are not accepted facts.
        values.update(native_id=None, native_mask=None, listed_any=None)
    if not all(type(values[n]) is bool for n in ("native_id", "native_mask")) or not projection.get("provider_body_reviewed", False):
        ledger["claims"]["review.provider_binding"]["status"] = "unknown"
    for name, value in values.items():
        if type(value) is not bool: continue
        fact = {"value": value, "claim": "fact." + name}
        declared = {"symbol": name, "value": value, "role": symbols[name]["role"], "context_id": context}
        if symbols[name]["role"] == "observation":
            fact.update(object_id=object_id, event_id=sample); declared.update(object_id=object_id, event_id=sample)
        record["facts"][name] = fact
        ledger["claims"]["fact." + name] = {"role": "fact", "status": "supported", "origin": "program_projection", "context_id": context,
            "statement": "Fact projected from this exact archived evidence; source-origin facts are not hardware facts.", "references": refs("evidence"), "fact": declared}
    return {"profile": profile, "policy_application": documents["policy_application"]["interpretation"], "historical_normative_verdict": "insufficient",
            "contract": contract, "ledger": ledger, "record": record, "projection": projection}


def prepare():
    inputs = {}
    def read(path): inputs[str(path.relative_to(INNER))] = sha(path); return load(path)
    protocol = read(HERE / "protocol_pre.json")
    assert sha(INNER / protocol["core"]) == protocol["core_sha256"]
    for name in ("source_review.md", "input_review.md", "policy_card.md", "policy_evidence.json", "projection.py", "transfer.py", "method_tests.json"):
        inputs[str((HERE / name).relative_to(INNER))] = sha(HERE / name)
    old_sources = read(HERE.parent / "arch_witness_checks_20261014/requests/export_pair.json")
    old_map, fixed_map = read(BASE / "old_source_map.json"), read(BASE / "fixed_source_map.json")
    for name in ("arch/x86/include/asm/topology.h", "arch/s390/include/asm/topology.h"):
        assert next(r["git_blob"] for r in old_map if r["path"] == name) == next(r["git_blob"] for r in fixed_map if r["path"] == name)
    rows = []
    for variant in ("old", "fixed"):
        revision = OLD if variant == "old" else FIXED
        for config in ("x86_smp", "s390_smp", "x86_up"):
            profile = variant + "_" + config; folder = BASE / "profiles" / profile
            pp = read(folder / "preprocessed_evidence.json"); result = read(folder / "result.json")
            assert result["profile"] == profile and result["revision"] == revision and result["preprocessing"] == pp
            conf = folder / "kernel.config"; inputs[str(conf.relative_to(INNER))] = sha(conf)
            prefix = "/root/.cache/linux-bug-analyze/die-contract-20261013/" + variant + "/linux"
            projection = project_static(pp, prefix, result["source_arch"])
            projection["provider_body_reviewed"] = native_body_review(pp, old_sources)
            context = "source." + profile + "." + sha(conf)[:16]
            rows.append(envelope(profile, revision, "source_projection", context, projection,
                                 config_value(conf.read_text(), "CONFIG_SYSFS"), folder / "preprocessed_evidence.json"))
    for variant in ("old", "fixed"):
        for arch in ("x86_64", "s390"):
            profile = variant + "_" + arch; folder = BASE / "runtime/profiles" / profile
            boot, build = read(folder / "boot.json"), read(folder / "build.json")
            conf, raw = folder / "kernel.config", folder / "qemu_boot.stdout.log"
            for path in (conf, raw): inputs[str(path.relative_to(INNER))] = sha(path)
            assert sha(conf) == build["config_sha256"] and boot["image_sha256"] == build["image_sha256"]
            assert boot["revision"] == build["revision"] and build["source_c_modified"] is False
            events = []
            for line in raw.read_text(encoding="utf-8").splitlines():
                at = line.find('{"event":')
                if at >= 0: events.append(json.loads(line[at:]))
            assert events == boot["observations"]["events"]
            assert validate_runtime_identity(profile, boot, build, events)
            projection = project_runtime(events)
            # Provider origin was not reconstructed in this minimal run config.
            projection.update(id_native=None, mask_native=None, provider_body_reviewed=False)
            projection["listed_any"] = (any(c.get("listed_any") is True for c in projection["cpus"])
                                        if projection["status"] == "supported" else None)
            context = "runtime." + profile + "." + sha(conf)[:12] + "." + build["image_sha256"][:12]
            row = envelope(profile, build["revision"], "archived_runtime", context, projection,
                           config_value(conf.read_text(), "CONFIG_SYSFS"), folder / "boot.json")
            row["runtime_identity"] = {"config_sha256": sha(conf), "image_sha256": build["image_sha256"], "raw_log_sha256": sha(raw), "source_c_modified": False}
            rows.append(row)
    save(HERE / "transfer_inputs.json", {"scope": "already-read mechanism transfer, separate static/runtime contexts", "input_sha256": inputs,
         "core_sha256": protocol["core_sha256"], "rows": rows, "automatic_requirement_extractions": 0})
    print(json.dumps({"status": "prepared_no_evaluation", "rows": len(rows)}))


def execute():
    packet = load(HERE / "transfer_inputs.json")
    assert sha(INNER / "linux_bug_analyze/contract_protocol.py") == packet["core_sha256"]
    for path, digest in packet["input_sha256"].items(): assert sha(INNER / path) == digest, path
    rows = []
    for row in packet["rows"]:
        result = evaluate_contract(row["contract"], row["ledger"], row["record"])
        rows.append({"profile": row["profile"], "basis": row["record"]["basis"], "policy_application": row["policy_application"],
                     "historical_normative_verdict": "insufficient", "evaluator": result,
                     "interpretation": "counterfactual_policy_mismatch_not_old_ABI_fault" if row["policy_application"] == "counterfactual_policy_from_fixed" and result["relation_at_observation"] == "violated" else "limited_declared_relation_only"})
    save(HERE / "transfer_results.json", {"rows": rows, "input_sha256": sha(HERE / "transfer_inputs.json"),
       "core_sha256": packet["core_sha256"], "adapter_sha256": sha(Path(__file__)), "formal_independent_positive_normal": [0, 0],
       "new_defects": 0, "new_model_calls": 0, "new_builds": 0, "new_kernel_runs": 0,
       "counts_by_basis": {basis: dict(Counter(r["evaluator"]["relation_at_observation"] for r in rows if r["basis"] == basis)) for basis in ("source_projection", "archived_runtime")}})
    print(json.dumps({basis: dict(Counter(r["evaluator"]["relation_at_observation"] for r in rows if r["basis"] == basis)) for basis in ("source_projection", "archived_runtime")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--prepare", action="store_true"); args = parser.parse_args()
    prepare() if args.prepare else execute()
