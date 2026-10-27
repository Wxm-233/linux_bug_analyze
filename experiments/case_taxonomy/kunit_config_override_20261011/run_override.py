"""Six real historical merge/subset calls on frozen synthetic configurations."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fragment(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    matches = [n for n in tree.body if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == "QEMU_ARCH" for t in n.targets)]
    assert len(matches) == 1
    call = matches[0].value
    assert isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "QemuArchParams"
    values = [kw.value for kw in call.keywords if kw.arg == "kconfig"]
    assert len(values) == 1 and isinstance(values[0], ast.Constant) and isinstance(values[0].value, str)
    return values[0].value


def pairs(config):
    return sorted([entry.name, entry.value] for entry in config.as_entries())


def main():
    assert not (HERE / "observations.json").exists(), "do not rerun first observations"
    freeze = json.loads((HERE / "execution_pre.json").read_text(encoding="utf-8"))
    for name, expected in freeze["files"].items():
        assert sha((HERE / name).read_bytes()) == expected, name
    source = HERE / "../kunit_config_binding_20261011/raw/03_kunit_config.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    imports = []
    for node in tree.body:
        assert isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign, ast.ClassDef, ast.FunctionDef))
        if isinstance(node, ast.Import):
            imports.extend(n.name for n in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module)
    assert imports == ["dataclasses", "re", "typing"]
    spec = importlib.util.spec_from_file_location("saved_kunit_config_override_20261011", source)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    inputs = json.loads((HERE / "inputs_pre.json").read_text(encoding="utf-8"))
    assert len(inputs["rows"]) == 6
    rows = []
    for item in inputs["rows"]:
        provider = HERE / item["provider"]
        assert sha(provider.read_bytes()) == item["provider_sha256"]
        text = fragment(provider)
        assert text == item["architecture_request_text"]
        arch = module.parse_from_string(text)
        base = module.parse_from_string(item["user_request_text"])
        generated = module.parse_from_string(item["synthetic_generated_text"])
        original = pairs(arch)
        user = pairs(base)
        # Diagnostic only: historical make_arch_config does not call this method.
        conflicts = sorted([a.name, a.value, b.value] for a, b in arch.conflicting_options(base))
        arch.merge_in_entries(base)
        final = pairs(arch)
        final_dict = dict(final)
        original_dict = dict(original)
        changed = [[name, original_dict.get(name), value] for name, value in final
                   if original_dict.get(name) != value]
        satisfied = arch.is_subset_of(generated)
        rows.append({"id": item["id"], "provider_role": item["provider_role"],
                     "original_arch_pairs": original, "user_pairs": user,
                     "original_arch_CPU_BIG_ENDIAN": original_dict.get("CPU_BIG_ENDIAN"),
                     "user_CPU_BIG_ENDIAN": dict(user)["CPU_BIG_ENDIAN"],
                     "pre_merge_conflicts": conflicts,
                     "final_request_pairs": final,
                     "final_request_CPU_BIG_ENDIAN": final_dict["CPU_BIG_ENDIAN"],
                     "changed_or_added_entries": changed,
                     "synthetic_generated_pairs": pairs(generated),
                     "request_satisfied": satisfied,
                     "review_override_legality_candidate": bool(conflicts),
                     "historical_make_arch_config_conflict_gate_executed": False,
                     "environment_required_CPU_BIG_ENDIAN": None,
                     "override_legality": "unknown",
                     "policy_violation": None,
                     "actual_generated_kernel_config": "unknown",
                     "Kconfig_reachability_or_runtime_certified": False})
    out = {"classification": "informed_synthetic_merge_and_request_matching",
           "rows": rows, "offline_runner_executions": 1, "parse_calls": 18,
           "merge_calls": 6, "subset_calls": 6, "diagnostic_conflict_calls": 6,
           "new_Git_commands": 0, "kernel_builds_or_runs": 0, "external_model_calls": 0,
           "new_confirmed_cases": 0, "independent_positive_cases": 0}
    (HERE / "observations.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
