"""Collect four configured API definitions and bounded original comments."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from linux_bug_analyze.preprocessed_evidence import extract_definitions


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main():
    rows = []
    for variant in ("old", "fixed"):
        profile = variant + "_s390"
        prior = read(HERE.parent / "provider_consumer_binding_20261017" / (profile + ".json"))
        source = Path("/root/.cache/linux-bug-analyze/s390-contract-20261013") / variant / "linux"
        artifacts = {a["path"]: a["sha256"] for a in prior["selected_artifacts"]}
        build = source.parent.parent / profile / "build"
        checked = []
        for relative in ("arch/s390/kernel/topology.i", ".config", "include/generated/autoconf.h"):
            path = build / relative
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if artifacts.get(str(path)) != actual:
                raise ValueError("Changed registered input: " + str(path))
            checked.append({"path": str(path), "sha256": actual})
        names = ("cpumask_clear", "cpumask_set_cpu", "cpumask_test_cpu", "cpumask_copy")
        raw = (build / "arch/s390/kernel/topology.i").read_bytes().decode()
        definitions = extract_definitions(raw, {n: str(source / "include/linux/cpumask.h") for n in names})
        original = subprocess.run(["git", "-C", "/root/repos/linux", "show", prior["revision"] + ":include/linux/cpumask.h"],
                                  capture_output=True, check=True).stdout
        if (source / "include/linux/cpumask.h").read_bytes() != original:
            raise ValueError("Selected API header differs from original Git")
        lines = original.decode().splitlines()
        comments = {}
        for name, definition in definitions.items():
            start = definition["name_location"]["line"] - 1
            lower = max(0, start - 16)
            comments[name] = {"start_line": lower + 1, "end_line": start + 1,
                              "text": "\n".join(lines[lower:start + 1]) + "\n",
                              "scope": "bounded source context, including the API comment where present"}
        widths = {}
        for name, call in (("cpumask_clear", "bitmap_zero"), ("cpumask_copy", "bitmap_copy")):
            # Literal argument in these selected configured definitions only.
            matches = re.findall(r"\b" + call + r"\([^;]*,\s*([0-9]+|\(\(\s*unsigned\s+int\s*\)\s*[0-9]+\s*\))\s*\);", definitions[name]["text"])
            if len(matches) != 1:
                raise ValueError("Configured logical bit length is not a supported unique constant")
            numbers = re.findall(r"[0-9]+", matches[0])
            widths[name] = int(numbers[0])
            if not 0 < widths[name] <= 65536:
                raise ValueError("Configured bit length outside the supported range")
        if widths["cpumask_clear"] != widths["cpumask_copy"]:
            raise ValueError("Logical domains differ")
        rows.append({"profile": profile, "revision": prior["revision"], "effective_config": prior["effective_config"],
                     "bound_inputs": checked, "definitions": definitions, "original_comments": comments,
                     "original_header_sha256": hashlib.sha256(original).hexdigest(),
                     "logical_bit_arguments": widths,
                     "dependency_boundary": ["bitmap_zero", "bitmap_copy", "set_bit", "test_bit", "cpumask_check"],
                     "lower_primitive_semantics": "reviewed API assumptions, not recursively proved",
                     "actual_target_legality": "unknown", "runtime_effects_proved": False})
    output = {"schema": "configured-cpumask-primitive-evidence-v1", "date": "2026-10-17", "profiles": rows,
              "new_model_requests": 0, "new_builds": 0, "new_kernel_runs": 0}
    (HERE / "primitive_evidence.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"profiles": [{"profile": r["profile"], "definitions": len(r["definitions"]),
                                   "logical_bit_arguments": r["logical_bit_arguments"]} for r in rows]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
