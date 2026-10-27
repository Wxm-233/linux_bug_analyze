"""Replay already-read v4 development inputs and a fixed GCC value/type probe."""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

import representation_producer_v4 as v4

DEVELOPMENT = (
    ("hisi_parent", "1dc39ed655750d6c679d3ada4adf4a937f2a63fc", "drivers/scsi/hisi_sas/hisi_sas_v3_hw.c"),
    ("hisi_fixed", "47e66bec3edaebd7c52d8ee981065a4c83b3072f", "drivers/scsi/hisi_sas/hisi_sas_v3_hw.c"),
    ("dw_parent", "40dfdd8d1449382cae3db2cefb1f5521ce19259b", "drivers/mmc/host/dw_mmc.c"),
    ("dw_refactor", "541fe77cc4d77799ac1b869e2183e1bdd716a1f2", "drivers/mmc/host/dw_mmc.c"),
)
EXPRESSIONS = ("1U << 17", "1U << 31", "BIT(31)", "BIT_ULL(40)",
               "~0U", "0xffffffffU + 1U", "077U + 1", "0xffffU & 255U",
               "((u16) 7) << 3", "0x80000000", "0xffffffff + 0ULL", "-7 / 3")


def gcc_probe() -> dict:
    declarations = """#include <stdio.h>
#include <limits.h>
typedef unsigned short u16;
#define BIT(n) (1UL << (n))
#define BIT_ULL(n) (1ULL << (n))
int main(void) {
"""
    lines = []
    for index, expr in enumerate(EXPRESSIONS):
        lines.append(f'printf("{index},%lld,%zu,%d\\n", (long long)({expr}), sizeof({expr}) * CHAR_BIT, _Generic(({expr}), unsigned int: 1, unsigned long: 1, unsigned long long: 1, default: 0));')
    c_source = declarations + "\n".join(lines) + "\nreturn 0;\n}\n"
    models = []
    with tempfile.TemporaryDirectory(prefix="repr_v4_gcc_") as directory:
        source = Path(directory) / "probe.c"
        source.write_text(c_source, encoding="utf-8")
        for flag, model, long_bits in (("-m32", "ILP32", 32), ("-m64", "LP64", 64)):
            executable = Path(directory) / model
            command = ["gcc", flag, "-std=gnu11", "-Wall", "-Wextra", str(source), "-o", str(executable)]
            build = subprocess.run(command, capture_output=True, text=True, check=False)
            if build.returncode:
                assertions = []
                for index, expr in enumerate(EXPRESSIONS):
                    expected = v4.Expression(expr, long_bits, {}, {}).evaluate()
                    assertions.append(f'_Static_assert((long long)({expr}) == {expected.exact}LL, "value {index}");')
                    assertions.append(f'_Static_assert(sizeof({expr}) * __CHAR_BIT__ == {expected.bits}, "width {index}");')
                    assertions.append(f'_Static_assert(_Generic(({expr}), unsigned int: 1, unsigned long: 1, unsigned long long: 1, default: 0) == {int(expected.unsigned)}, "unsigned {index}");')
                no_libc = "typedef unsigned short u16;\n#define BIT(n) (1UL << (n))\n#define BIT_ULL(n) (1ULL << (n))\n" + "\n".join(assertions) + "\n"
                assertion_file = Path(directory) / f"{model}_assert.c"
                assertion_file.write_text(no_libc, encoding="utf-8")
                assertion_command = ["gcc", flag, "-std=gnu11", "-Wall", "-Wextra", "-fsyntax-only", str(assertion_file)]
                checked = subprocess.run(assertion_command, capture_output=True, text=True, check=False)
                models.append({"model": model, "status": "compile_verified" if checked.returncode == 0 else "unavailable",
                               "all_match": checked.returncode == 0, "expressions": list(EXPRESSIONS), "assertions": len(assertions),
                               "oracle_kind": "compile-only value/width/signedness static assertions, no execution",
                               "assert_source_sha256": hashlib.sha256(no_libc.encode()).hexdigest(),
                               "runtime_build_diagnostic": build.stderr, "assert_build_diagnostic": checked.stderr})
                continue
            execution = subprocess.run([str(executable)], capture_output=True, text=True, check=True)
            observed = {int(index): (int(value), int(width), bool(int(unsigned)))
                        for index, value, width, unsigned in (line.split(",") for line in execution.stdout.splitlines())}
            cases = []
            for index, expr in enumerate(EXPRESSIONS):
                predicted = v4.Expression(expr, long_bits, {}, {}).evaluate()
                expectation = (predicted.exact, predicted.bits, predicted.unsigned)
                cases.append({"expression": expr, "expected": expectation,
                              "gcc_observed": observed[index], "match": expectation == observed[index]})
            models.append({"model": model, "status": "ok", "cases": cases,
                           "all_match": all(item["match"] for item in cases), "compile_diagnostic": build.stderr})
    return {"scope": "Fixed supported defined expressions; this does not validate all C preprocessing or undefined behavior cases.",
            "source_sha256": hashlib.sha256(c_source.encode()).hexdigest(),
            "compiler": subprocess.check_output(["gcc", "--version"], text=True).splitlines()[0], "models": models}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linux-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for name, revision, source in DEVELOPMENT:
        report = v4.analyze_revision(args.linux_dir, revision, source)
        report["evaluation_role"] = "already-read development replay, not independent holdout"
        serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        output = args.out_dir / f"representation_v4_{name}_development.json"
        output.write_text(serialized, encoding="utf-8")
        target = [item for item in report["findings"] if
                  ("hisi" in name and "CMD_HDR_FORCE_PHY_MSK" in item["rhs"]) or
                  ("dw" in name and any(mask in item["rhs"] for mask in ("IDMAC_DES0_FD", "IDMAC_DES0_LD")))]
        records.append({"name": name, "revision": revision, "source_file": source,
                        "counts": report["counts"], "output": output.name,
                        "sha256": hashlib.sha256(serialized.encode()).hexdigest(),
                        "target_sites": [{key: item.get(key) for key in ("line", "function", "rhs", "destination_type", "status", "reason")} for item in target]})
    probe = gcc_probe()
    probe_path = args.out_dir / "representation_v4_gcc_development.json"
    probe_path.write_text(json.dumps(probe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {"rule_version": v4.VERSION, "role": "already-read development only; not a generalized detection metric", "records": records,
               "gcc_probe": {"output": probe_path.name, "sha256": hashlib.sha256(probe_path.read_bytes()).hexdigest(),
                             "models": [{"model": item["model"], "status": item["status"], "all_match": item.get("all_match")} for item in probe["models"]]}}
    output = args.out_dir / "representation_v4_development_manifest.json"
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
