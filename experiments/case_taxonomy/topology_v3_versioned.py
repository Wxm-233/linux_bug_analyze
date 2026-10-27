"""Version-aware, bounded topology/sysfs evidence on *already read* history.

This is a development extractor.  It deliberately refuses unfamiliar Kconfig,
preprocessor and attribute shapes; it does not emulate a kernel build.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from contract_check_pilot_v1 import capability
from topology_contract_extract import (
    extract as extract_v2,
    legacy_book_drawer_guard,
    macro_state,
    target_state,
    topology_build_rule,
    tri_or,
)


DEVELOPMENT_COMMITS = (
    "f1045056c726440469d89d23c13734bcd6c0d15b",
    "a62247e1f5c13b926f535bb64ecbd7f9fdef7b21",
    "b40d8ed4e42c79f8ed1cf345eed0888f4a2f0678",
)


def _line_refs(revision: str, path: str, text: str, pattern: str) -> list[str]:
    return [f"{revision}:{path}:{i}" for i, line in enumerate(text.splitlines(), 1)
            if re.search(pattern, line)]


def build_topology(makefile: str, smp: bool) -> tuple[bool | None, list[int], str]:
    """Resolve only one obj-y or one obj-$(CONFIG_SMP) topology.o rule."""
    if makefile is None:
        return None, [], "drivers/base/Makefile missing"
    unconditional, lines = topology_build_rule(makefile)
    if unconditional is True:
        return True, lines, "obj-y"
    joined = re.sub(r"\\\s*\n\s*", " ", makefile)
    matches = list(re.finditer(
        r"(?m)^\s*obj-\$\(CONFIG_SMP\)\s*(?:\+=|:=|=)\s*[^\n]*\btopology\.o\b",
        joined))
    if len(matches) == 1 and len(lines) == 1:
        # The old Makefile rule is line-local.  Do not extrapolate through
        # surrounding make conditionals or additional topology.o rules.
        line = next((i for i, text in enumerate(makefile.splitlines(), 1)
                     if "topology.o" in text), None)
        if line is not None and not re.search(r"(?m)^\s*(?:ifeq|ifneq|ifdef|ifndef)\b",
                                               makefile[:makefile.find("topology.o")]):
            return smp, [line], "obj-$(CONFIG_SMP)"
    return None, lines, "unrecognized or ambiguous topology.o build rule"


def inspect_snapshot(files: dict[str, str | None], revision: str, arch: str,
                     family: str, smp: bool, sysfs: bool,
                     sched_topology: bool | None) -> dict:
    """Return source facts and a verdict only where every needed link resolves."""
    driver_path = "drivers/base/topology.c"
    make_path = "drivers/base/Makefile"
    header_path = "include/linux/topology.h"
    arch_path = f"arch/{arch}/include/asm/topology.h"
    config_path = "arch/s390/Kconfig"
    driver = files.get(driver_path)
    makefile = files.get(make_path)
    header = files.get(header_path)
    refs: dict[str, list[str]] = {key: [] for key in
                                   ("build", "header", "provider", "guard",
                                    "consumer", "registration", "kconfig")}
    result = {"revision": revision, "arch": arch, "family": family,
              "profile": {"smp": smp, "sysfs": sysfs,
                          "sched_topology": sched_topology},
              "status": "insufficient", "reason": "not evaluated",
              "shape": None, "facts": {}, "source_refs_by_fact": refs,
              "scope": "post-read development; source-level, not a kernel build"}

    def finish(status: str, reason: str) -> dict:
        result["status"], result["reason"] = status, reason
        return result

    if arch not in {"s390", "x86"} or family not in {"book", "drawer"}:
        return finish("insufficient", "v3 supports only book/drawer on s390/x86")
    built, build_lines, build_shape = build_topology(makefile, smp)
    refs["build"] = [f"{revision}:{make_path}:{line}" for line in build_lines]
    result["facts"].update(build_rule=build_shape, topology_object_built=built)
    if built is None:
        return finish("insufficient", build_shape)
    if not built:
        return finish("not_applicable", "topology.o is not built for this profile")
    if not sysfs:
        return finish("not_applicable", "CONFIG_SYSFS is off in this profile")
    if driver is None or header is None:
        return finish("insufficient", "topology driver or common header missing")
    refs["header"] = _line_refs(revision, header_path, header,
                                 r"#include <(?:asm/topology|linux/arch_topology)\.h>")
    if len(_line_refs(revision, header_path, header,
                      r"^\s*#include <asm/topology\.h>")) != 1:
        return finish("insufficient", "asm/topology.h inclusion not proven")
    result["facts"]["arch_topology_header"] = (
        "present" if files.get("include/linux/arch_topology.h") is not None
        else "absent; optional when common header does not include it")
    if ("#include <linux/arch_topology.h>" in header and
            files.get("include/linux/arch_topology.h") is None):
        return finish("insufficient", "included arch_topology.h missing")

    if re.search(rf"\bdefine_id_show_func\({family}_id\);", driver) is None:
        return finish("not_applicable", f"{family} attribute consumer is absent")

    if ("define_siblings_read_func" in driver and "BIN_ATTR_RO" in driver):
        # The frozen v2 implementation remains byte-for-byte unchanged.  Its
        # modern shape and C evaluator are reused only when that shape exists.
        paths = [name for name, text in files.items() if text is not None]

        def required(path: str) -> str:
            value = files.get(path)
            if value is None:
                raise FileNotFoundError(path)
            return value

        try:
            evidence = extract_v2(required, paths, revision, arch, smp, sysfs,
                                  family, sched_topology)
        except (FileNotFoundError, ValueError) as exc:
            return finish("insufficient", f"modern source chain unresolved: {exc}")
        result["shape"] = "DEVICE_ATTR+BIN_ATTR"
        result["facts"]["v2_record"] = evidence["records"][0]
        result["source_refs_by_fact"] = evidence["source_refs_by_fact"]
        status, reason = capability(evidence["records"][0])
        return finish(status, reason)

    if "SYSDEV_ATTR" in driver:
        shape = "SYSDEV_ATTR"
        sibling = f"{family}_cpumask"
        expected = (
            rf"^define_id_show_func\({family}_id\);$",
            rf"^define_one_ro\({family}_id\);$",
            rf"^define_siblings_show_func\({sibling}\);$",
            rf"^define_one_ro_named\({family}_siblings, show_{sibling}\);$",
            rf"^define_one_ro_named\({family}_siblings_list, show_{sibling}_list\);$",
        )
        arrays = (rf"&attr_{family}_id\.attr,",
                  rf"&attr_{family}_siblings\.attr,",
                  rf"&attr_{family}_siblings_list\.attr,")
    elif "DEVICE_ATTR_RO" in driver:
        shape = "DEVICE_ATTR"
        sibling = f"{family}_siblings"
        expected = (
            rf"^define_id_show_func\({family}_id\);$",
            rf"^static DEVICE_ATTR_RO\({family}_id\);$",
            rf"^define_siblings_show_func\({sibling}, {family}_cpumask\);$",
            rf"^static DEVICE_ATTR_RO\({sibling}\);$",
            rf"^static DEVICE_ATTR_RO\({sibling}_list\);$",
        )
        arrays = (rf"&dev_attr_{family}_id\.attr,",
                  rf"&dev_attr_{family}_siblings\.attr,",
                  rf"&dev_attr_{family}_siblings_list\.attr,")
    else:
        return finish("insufficient", "unknown attribute declaration generation")
    result["shape"] = shape
    if shape == "SYSDEV_ATTR":
        mapping_known = ("#define define_id_show_func(name)" in driver and
                         "#define define_siblings_show_func(name)" in driver and
                         "#define define_one_ro_named(_name, _func)" in driver and
                         "topology_##name(" in driver and
                         "SYSDEV_ATTR(_name, 0444, _func, NULL)" in driver)
    else:
        mapping_known = ("#define define_id_show_func(name)" in driver and
                         "#define define_siblings_show_func(name, mask)" in driver and
                         "topology_##name(" in driver and
                         "topology_##mask(" in driver)
    if not mapping_known:
        return finish("insufficient", f"{shape} generated show/read mapping not recognized")

    if arch == "s390":
        config = files.get(config_path)
        if config is None:
            return finish("insufficient", "s390 Kconfig missing")
        refs["kconfig"] = _line_refs(revision, config_path, config,
                                      r"config SCHED_TOPOLOGY|config SCHED_(?:BOOK|DRAWER)|select SCHED_(?:BOOK|DRAWER)")
        if (not re.search(r"(?m)^config SCHED_TOPOLOGY\s*$", config) and
                sched_topology is not None):
            return finish("not_applicable", "profile names CONFIG_SCHED_TOPOLOGY, absent in this historical s390 Kconfig")
    arch_header = files.get(arch_path)
    if arch_header is None:
        return finish("insufficient", "arch asm/topology.h resolution not proven")
    if (re.search(rf"(?m)^#\s*ifndef\s+topology_{family}_(?:id|cpumask)", header)
            or re.search(rf"(?m)^#\s*define\s+topology_{family}_(?:id|cpumask)", header)):
        return finish("insufficient", "legacy common-header fallback differs from bounded shape")

    guard_name = f"CONFIG_SCHED_{family.upper()}"
    guard, config_refs = legacy_book_drawer_guard(
        lambda path: files[path] or "", revision, arch, family, sched_topology)
    refs["kconfig"].extend(config_refs)
    if guard is None:
        return finish("insufficient", f"{guard_name} Kconfig reachability unresolved")
    if arch == "x86":
        # An absence in arch/x86/Kconfig alone is not a complete Kconfig source
        # graph.  Keep the historical x86 profile out of behavior verdicts.
        return finish("insufficient", "legacy x86 Kconfig source graph not established")
    symbols = {guard_name: guard, "CONFIG_SMP": smp,
               "CONFIG_SCHED_TOPOLOGY": sched_topology}
    states = []
    for pattern in expected + arrays:
        state, lines = target_state(driver, symbols, pattern)
        states.append(state)
        key = "consumer" if len(states) <= len(expected) else "registration"
        refs[key].extend(f"{revision}:{driver_path}:{line}" for line in lines)
        if len(lines) != 1 or state is None:
            return finish("insufficient", f"{shape} declaration/array shape unresolved: {pattern}")
    if len(set(states)) != 1:
        return finish("insufficient", "consumer declarations and attributes have different guards")
    exported = states[0]
    refs["guard"] = _line_refs(revision, driver_path, driver,
                                rf"^#ifdef {guard_name}\s*$")
    if len(refs["guard"]) != 2 or exported is not guard:
        return finish("insufficient", "attribute guard does not match resolved Kconfig symbol")
    registration = (".attrs = default_attrs" in driver and
                    "sysfs_create_group(" in driver and
                    "&topology_attr_group" in driver and
                    "device_initcall(topology_sysfs_init)" in driver and
                    ".is_visible" not in driver)
    refs["registration"].extend(_line_refs(revision, driver_path, driver,
                                           r"\.attrs = default_attrs|sysfs_create_group|device_initcall"))
    if not registration:
        return finish("insufficient", "sysfs registration chain not recognized")
    provider_symbols = {"CONFIG_SMP": smp,
                        "CONFIG_SCHED_TOPOLOGY": sched_topology}
    providers = {}
    for suffix in ("id", "cpumask"):
        name = f"topology_{family}_{suffix}"
        local_state, lines = macro_state(arch_header, provider_symbols, name)
        refs["provider"].extend(f"{revision}:{arch_path}:{line}" for line in lines)
        generic_header = files.get("include/asm-generic/topology.h")
        if "#include <asm-generic/topology.h>" in arch_header:
            if generic_header is None:
                return finish("insufficient", "included asm-generic/topology.h missing")
            generic_state, generic_lines = macro_state(generic_header, provider_symbols, name)
            refs["provider"].extend(f"{revision}:include/asm-generic/topology.h:{line}"
                                    for line in generic_lines)
            local_state = tri_or(local_state, generic_state)
        providers[suffix] = local_state
    result["facts"].update(guard=guard, exported=exported,
                           native_id=providers["id"],
                           native_map=providers["cpumask"])
    if exported:
        if providers["id"] is None or providers["cpumask"] is None:
            return finish("insufficient", "active provider macros have unresolved conditions")
        if not providers["id"] or not providers["cpumask"]:
            return finish("hit", "exported attribute lacks a paired native ID/CPU-map provider")
    return finish("normal", "bounded build, config, provider, consumer and registration chain is paired")


def from_git(repo: Path, revision: str, arch: str, family: str,
             smp: bool = True, sysfs: bool = True,
             sched_topology: bool | None = None) -> dict:
    if not re.fullmatch(r"[0-9a-fA-F]{7,40}\^?", revision):
        raise ValueError("revision must be a SHA, optionally followed by ^")
    resolved = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "--verify", f"{revision}^{{commit}}"],
        text=True).strip()
    paths = ("drivers/base/Makefile", "drivers/base/topology.c",
             "drivers/base/Kconfig", "include/linux/topology.h",
             "include/linux/arch_topology.h", "include/asm-generic/topology.h",
             "include/asm-generic/Kbuild", f"arch/{arch}/include/asm/topology.h",
             "arch/s390/Kconfig", "arch/x86/Kconfig")
    files: dict[str, str | None] = {}
    for path in paths:
        found = subprocess.run(["git", "-C", str(repo), "show", f"{resolved}:{path}"],
                               text=True, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, check=False)
        files[path] = found.stdout if found.returncode == 0 else None
    return inspect_snapshot(files, resolved, arch, family, smp, sysfs,
                            sched_topology)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linux-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = []
    for fix in DEVELOPMENT_COMMITS:
        for label, revision in (("parent", fix + "^"), ("fix", fix)):
            for family in ("book", "drawer"):
                for arch, sched in (("s390", True), ("s390", False),
                                    ("s390", None), ("x86", None)):
                    case = from_git(args.linux_dir, revision, arch, family,
                                    sched_topology=sched)
                    case["case"] = {"fix": fix, "version": label}
                    cases.append(case)
    output = {"purpose": "post-read versioned development; no new holdout",
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "frozen_v2_sha256": hashlib.sha256((Path(__file__).parent /
                  "topology_contract_extract.py").read_bytes()).hexdigest(),
              "cases": cases}
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({status: sum(c["status"] == status for c in cases)
                      for status in sorted({c["status"] for c in cases})}))


if __name__ == "__main__":
    main()
