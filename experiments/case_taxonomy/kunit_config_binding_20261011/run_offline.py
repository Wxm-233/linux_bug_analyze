"""Six frozen calls of historical KUnit request matching; no kernel workflow."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def provider_fragment(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assignments = [n for n in tree.body if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == "QEMU_ARCH" for t in n.targets)]
    assert len(assignments) == 1
    call = assignments[0].value
    assert isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "QemuArchParams"
    choices = [n.value for n in call.keywords if n.arg == "kconfig"]
    assert len(choices) == 1 and isinstance(choices[0], ast.Constant) and isinstance(choices[0].value, str)
    return choices[0].value


def main():
    assert not (HERE / "observations.json").exists(), "do not repeat completed first execution"
    freeze = json.loads((HERE / "execution_pre.json").read_text(encoding="utf-8"))
    for path, expected in freeze["files"].items():
        assert sha((HERE / path).read_bytes()) == expected, path
    source = HERE / "raw/03_kunit_config.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    imports = []
    for node in tree.body:
        assert isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign, ast.ClassDef, ast.FunctionDef)), type(node).__name__
        if isinstance(node, ast.Import):
            imports.extend(n.name for n in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module)
    assert imports == ["dataclasses", "re", "typing"], imports
    spec = importlib.util.spec_from_file_location("saved_kunit_config_offline_20261011", source)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    inputs = json.loads((HERE / "inputs_pre.json").read_text(encoding="utf-8"))
    assert len(inputs["records"]) == 6
    results = []
    for record in inputs["records"]:
        path = HERE / record["provider"]
        assert sha(path.read_bytes()) == record["provider_sha256"]
        fragment = provider_fragment(path)
        assert fragment == record["request_text"]
        requested = module.parse_from_string(fragment)
        # Match the actual make_arch_config merge order; this phase fixes the user base to empty.
        requested.merge_in_entries(module.parse_from_string(""))
        generated = module.parse_from_string(record["synthetic_generated_text"])
        matched = requested.is_subset_of(generated)
        request_pairs = sorted((entry.name, entry.value) for entry in requested.as_entries())
        generated_pairs = sorted((entry.name, entry.value) for entry in generated.as_entries())
        results.append({"id": record["id"], "provider_role": record["provider_role"],
                        "synthetic_output_role": record["synthetic_output_role"],
                        "request_pairs": request_pairs, "generated_pairs": generated_pairs,
                        "request_satisfied": matched,
                        "missing_or_different_requested_entries": [list(p) for p in request_pairs if p not in generated_pairs],
                        "request_contains_CPU_BIG_ENDIAN": any(p[0] == "CPU_BIG_ENDIAN" for p in request_pairs),
                        "effective_actual_kernel_configuration": "unknown",
                        "kernel_endianness_correct": None,
                        "runtime_or_Kconfig_reachability_certified": False})
    out = {"classification": "historical_function_offline_synthetic_request_matching",
           "records": results, "matching_calls": 6, "provider_AST_reads": 6,
           "user_base_configuration": "empty_in_all_six_records",
           "real_generated_configs": 0, "kernel_builds_or_boots": 0,
           "frozen_C_template_executions": 0, "new_confirmed_cases": 0,
           "independent_positive_cases": 0}
    # Raw observations are persisted before any separate oracle comparison.
    (HERE / "observations.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
