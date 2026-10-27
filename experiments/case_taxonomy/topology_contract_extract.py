"""Extract narrowly scoped topology/sysfs facts from a historical Linux tree.

This is a source-evidence extractor for the existing C contract evaluator, not
a kernel preprocessor or an authority on the intended meaning of a topology ID.
Unknown conditions and unfamiliar interface shapes remain unknown.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Callable


SUPPORTED_ARCHES = frozenset({"x86", "arm64", "riscv", "s390"})
SUPPORTED_FAMILIES = frozenset({"die", "cluster", "book", "drawer"})
BOOK_DRAWER_ARCHES = frozenset({"s390", "x86"})
Truth = bool | None
Source = Callable[[str], str]


def tri_and(left: Truth, right: Truth) -> Truth:
    if left is False or right is False:
        return False
    if left is None or right is None:
        return None
    return True


def tri_or(left: Truth, right: Truth) -> Truth:
    if left is True or right is True:
        return True
    if left is None or right is None:
        return None
    return False


def tri_not(value: Truth) -> Truth:
    return None if value is None else not value


class ConditionParser:
    """Small #if subset; never guess at an expression outside this grammar."""

    TOKEN = re.compile(r"\s*(defined|[A-Za-z_]\w*|&&|\|\||!|\(|\)|0|1)")

    def __init__(self, expression: str, symbols: dict[str, Truth]):
        self.symbols = symbols
        self.tokens: list[str] = []
        offset = 0
        while offset < len(expression):
            match = self.TOKEN.match(expression, offset)
            if match is None:
                raise ValueError("unsupported preprocessor expression")
            self.tokens.append(match.group(1))
            offset = match.end()
        self.pos = 0

    def pop(self, expected: str | None = None) -> str:
        if self.pos >= len(self.tokens):
            raise ValueError("truncated preprocessor expression")
        token = self.tokens[self.pos]
        self.pos += 1
        if expected is not None and token != expected:
            raise ValueError("unsupported preprocessor expression")
        return token

    def peek(self) -> str | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def atom(self) -> Truth:
        token = self.pop()
        if token == "!":
            return tri_not(self.atom())
        if token == "(":
            value = self.disjunction()
            self.pop(")")
            return value
        if token == "defined":
            if self.peek() == "(":
                self.pop("(")
                name = self.pop()
                self.pop(")")
            else:
                name = self.pop()
            if not re.fullmatch(r"[A-Za-z_]\w*", name):
                raise ValueError("unsupported defined() argument")
            return self.symbols.get(name)
        if token in {"0", "1"}:
            return token == "1"
        if re.fullmatch(r"[A-Za-z_]\w*", token):
            return self.symbols.get(token)
        raise ValueError("unsupported preprocessor expression")

    def conjunction(self) -> Truth:
        value = self.atom()
        while self.peek() == "&&":
            self.pop("&&")
            value = tri_and(value, self.atom())
        return value

    def disjunction(self) -> Truth:
        value = self.conjunction()
        while self.peek() == "||":
            self.pop("||")
            value = tri_or(value, self.conjunction())
        return value

    def parse(self) -> Truth:
        value = self.disjunction()
        if self.peek() is not None:
            raise ValueError("unsupported preprocessor expression")
        return value


def condition(expression: str, symbols: dict[str, Truth]) -> Truth:
    try:
        return ConditionParser(expression, symbols).parse()
    except ValueError:
        return None


def include_guard(source: str) -> str | None:
    lines = source.splitlines()
    for index, line in enumerate(lines[:35]):
        found = re.fullmatch(r"\s*#\s*ifndef\s+([A-Za-z_]\w*)\s*", line)
        if found and any(
            re.fullmatch(rf"\s*#\s*define\s+{found.group(1)}\s*", later)
            for later in lines[index + 1 : index + 5]
        ):
            return found.group(1)
    return None


def active_lines(source: str, symbols: dict[str, Truth]) -> list[tuple[int, str, Truth]]:
    """Return active state for each non-directive line, including unknown."""
    symbols = dict(symbols)
    guard = include_guard(source)
    if guard:
        symbols[guard] = False
    stack: list[dict[str, Truth]] = []
    active: Truth = True
    output: list[tuple[int, str, Truth]] = []
    for lineno, line in enumerate(source.splitlines(), 1):
        stripped = line.strip()
        directive = re.match(r"#\s*(if|ifdef|ifndef|elif|else|endif|define|undef)\b(.*)", stripped)
        if not directive:
            output.append((lineno, line, active))
            continue
        kind, rest = directive.group(1), directive.group(2).strip()
        if kind in {"if", "ifdef", "ifndef"}:
            if kind == "if":
                branch = condition(rest, symbols)
            else:
                name = rest.split()[0] if rest else ""
                branch = symbols.get(name)
                if kind == "ifndef":
                    branch = tri_not(branch)
            stack.append({"outer": active, "seen": branch})
            active = tri_and(active, branch)
        elif kind == "elif":
            if not stack:
                raise ValueError(f"unmatched #elif at {lineno}")
            frame = stack[-1]
            branch = condition(rest, symbols)
            active = tri_and(frame["outer"], tri_and(tri_not(frame["seen"]), branch))
            frame["seen"] = tri_or(frame["seen"], branch)
        elif kind == "else":
            if not stack:
                raise ValueError(f"unmatched #else at {lineno}")
            frame = stack[-1]
            active = tri_and(frame["outer"], tri_not(frame["seen"]))
            frame["seen"] = True
        elif kind == "endif":
            if not stack:
                raise ValueError(f"unmatched #endif at {lineno}")
            active = stack.pop()["outer"]
        else:
            match = re.match(r"([A-Za-z_]\w*)", rest)
            if match:
                name = match.group(1)
                old = symbols.get(name)
                value = kind == "define"
                if active is True:
                    symbols[name] = value
                elif active is None and old != value:
                    symbols[name] = None
            output.append((lineno, line, active))
    if stack:
        raise ValueError("unclosed preprocessor condition")
    return output


def at(revision: str, path: str, lineno: int | None = None) -> str:
    return f"{revision}:{path}" + (f":{lineno}" if lineno is not None else "")


def target_state(source: str, symbols: dict[str, Truth], pattern: str) -> tuple[Truth, list[int]]:
    matches = [(line, state) for line, text, state in active_lines(source, symbols)
               if re.search(pattern, text)]
    if len(matches) != 1:
        return None, [line for line, _ in matches]
    return matches[0][1], [matches[0][0]]


def macro_state(source: str, symbols: dict[str, Truth], name: str) -> tuple[Truth, list[int]]:
    value: Truth = False
    refs: list[int] = []
    for line, text, active in active_lines(source, symbols):
        match = re.match(rf"\s*#\s*(define|undef)\s+{re.escape(name)}\b", text)
        if match is None:
            continue
        refs.append(line)
        new_value = match.group(1) == "define"
        if active is True:
            value = new_value
        elif active is None and value != new_value:
            value = None
    return value, refs


def topology_build_rule(source: str) -> tuple[Truth, list[int]]:
    """Recognize one unconditional obj-y assignment, including continuations."""
    matches: list[tuple[int, Truth]] = []
    current = ""
    current_lines: list[int] = []
    conditional_depth = 0
    for lineno, line in enumerate(source.splitlines(), 1):
        stripped = line.strip()
        if re.match(r"^(ifeq|ifneq|ifdef|ifndef)\b", stripped):
            conditional_depth += 1
        elif re.match(r"^endif\b", stripped):
            conditional_depth = max(0, conditional_depth - 1)
        if not current_lines:
            current_lines = [lineno]
        else:
            current_lines.append(lineno)
        continuation = line.rstrip().endswith("\\")
        current += line.rstrip().removesuffix("\\") + " "
        if continuation:
            continue
        if re.search(r"\btopology\.o\b", current):
            unconditional = (conditional_depth == 0 and
                             re.match(r"^\s*obj-y\s*(?::=|\+=|=)", current) is not None)
            source_line = next((i for i in current_lines if
                                re.search(r"\btopology\.o\b", source.splitlines()[i - 1])),
                               current_lines[0])
            matches.append((source_line, unconditional))
        current = ""
        current_lines = []
    if len(matches) != 1:
        return None, [line for line, _ in matches]
    return (True if matches[0][1] else None), [matches[0][0]]


def kconfig_generic(source: Source, arch: str, paths: list[str], revision: str,
                    smp: bool) -> tuple[Truth, list[str]]:
    """Only recognize the historical hidden bool and simple arch selects."""
    config = source("drivers/base/Kconfig")
    if not re.search(r"(?m)^config GENERIC_ARCH_TOPOLOGY\n\s+bool\s*$", config):
        return None, [at(revision, "drivers/base/Kconfig")]
    selected: list[tuple[str, int, str, Truth, str | None]] = []
    for path in paths:
        if not re.search(r"(?:^|/)Kconfig[^/]*$", path):
            continue
        stack: list[Truth] = []
        active: Truth = True
        owner: str | None = None
        for lineno, line in enumerate(source(path).splitlines(), 1):
            stripped = line.strip()
            if re.match(r"^if\s+", stripped):
                stack.append(active)
                active = tri_and(active, condition(stripped[3:], {"SMP": smp}))
                continue
            if re.match(r"^endif\b", stripped):
                active = stack.pop() if stack else None
                continue
            config = re.match(r"^(?:menu)?config\s+([A-Za-z_]\w*)", stripped)
            if config:
                owner = config.group(1)
            if re.match(r"\s*select\s+GENERIC_ARCH_TOPOLOGY\b", line):
                selected.append((path, lineno, stripped, active, owner))
    refs = [at(revision, path, line) for path, line, _, _, _ in selected]
    if not selected:
        # The symbol is hidden with no default in this bounded historical tree.
        return False, refs + [at(revision, "drivers/base/Kconfig")]
    if len(selected) != 1 or selected[0][0] != f"arch/{arch}/Kconfig":
        return None, refs
    text, active, owner = selected[0][2:]
    if owner != {"arm64": "ARM64", "riscv": "RISCV"}.get(arch) or active is not True:
        return None, refs
    if text == "select GENERIC_ARCH_TOPOLOGY":
        return True, refs
    if text == "select GENERIC_ARCH_TOPOLOGY if SMP":
        return smp, refs
    return None, refs


def legacy_book_drawer_guard(source: Source, revision: str, arch: str,
                             family: str, sched_topology: Truth) -> tuple[Truth, list[str]]:
    """Resolve only the f104-era s390 select or the x86 non-selection.

    SCHED_TOPOLOGY has a default, but can be configured off. The caller must
    provide its actual value before the s390 select can be evaluated.
    """
    name = f"SCHED_{family.upper()}"
    path = "arch/s390/Kconfig"
    config = source(path)
    definition = re.search(rf"(?m)^config {name}[ \t]*\n[ \t]+def_bool n[ \t]*$", config)
    owner = re.search(r"(?ms)^config SCHED_TOPOLOGY[ \t]*\n(.*?)(?=^config |^menuconfig |\Z)", config)
    if not definition or owner is None:
        return None, [at(revision, path)]
    selects = [(i, line) for i, line in enumerate(config.splitlines(), 1)
               if re.fullmatch(rf"[ \t]*select {name}[ \t]*", line)]
    if len(selects) != 1 or selects[0][1] not in owner.group(1).splitlines():
        return None, [at(revision, path, config[:definition.start()].count("\n") + 1)]
    refs = [at(revision, path, config[:definition.start()].count("\n") + 1),
            at(revision, path, config[:owner.start()].count("\n") + 1),
            at(revision, path, selects[0][0])]
    if arch == "s390":
        return sched_topology, refs
    if arch == "x86":
        x86_path = "arch/x86/Kconfig"
        x86_config = source(x86_path)
        if re.search(rf"(?m)^\s*(?:config|menuconfig|select) {name}\b", x86_config):
            return None, refs + [at(revision, x86_path)]
        return False, refs + [at(revision, x86_path)]
    return None, refs


def extract(source: Source, paths: list[str], revision: str, arch: str,
            smp: bool, sysfs: bool, family: str,
            sched_topology: Truth = None) -> dict:
    refs: dict[str, list[str]] = {name: [] for name in
                                   ("build", "provider_id", "provider_map", "fallback",
                                    "contract", "export", "kconfig")}
    unknown: list[str] = []
    sched_id = (f":sched-{'on' if sched_topology else 'off' if sched_topology is False else 'unknown'}"
                if family in {"book", "drawer"} else "")
    row = {"id": f"topology:{family}:{arch}:{'smp' if smp else 'up'}:"
                 f"{'sysfs' if sysfs else 'no-sysfs'}{sched_id}:{revision[:12]}",
           "rule": "C", "interface_built": None, "paired_native_contract": None,
           "guard_resolved": None, "exported": None, "native_id": None,
           "native_map": None, "source_refs": [],
           "fact_method": "restricted_topology_source_extractor_v2"}
    result = {"revision": revision, "profile": {"arch": arch, "smp": smp,
                                               "sysfs": sysfs,
                                               "sched_topology": sched_topology},
              "family": family, "records": [row], "source_refs_by_fact": refs,
              "unknown_reasons": unknown,
              "authority_provenance": {
                  "level": "implementation_contract_candidate",
                  "meaning": "consumer/provider and, where present, fallback relationship in historical Linux source; not an externally validated topology ABI or hardware meaning",
                  "source_refs": refs["contract"]}}
    if arch not in SUPPORTED_ARCHES:
        unknown.append(f"unsupported architecture: {arch}")
        return result
    if family not in SUPPORTED_FAMILIES:
        unknown.append(f"{family}: no supported native ID/CPU-map pair; runtime visibility requires a separate contract")
        if family == "ppin":
            driver = source("drivers/base/topology.c")
            refs["export"] = [at(revision, "drivers/base/topology.c", i) for i, line in
                              enumerate(driver.splitlines(), 1) if "dev_attr_ppin" in line or
                              "topology_ppin(" in line or ".is_visible" in line]
            row["source_refs"] = refs["export"]
        return result
    if family in {"book", "drawer"} and arch not in BOOK_DRAWER_ARCHES:
        unknown.append(f"{family}: only f104-era s390/x86 source shapes are supported")
        return result

    makefile = source("drivers/base/Makefile")
    build_rule, build_lines = topology_build_rule(makefile)
    refs["build"] = [at(revision, "drivers/base/Makefile", i) for i in build_lines]
    if build_rule is not True:
        unknown.append("topology.o build rule not recognized")
        return result
    row["interface_built"] = sysfs
    if not sysfs:
        row["source_refs"] = refs["build"]
        return result

    generic, config_refs = kconfig_generic(source, arch, paths, revision, smp)
    refs["kconfig"] = config_refs
    if generic is None:
        unknown.append("GENERIC_ARCH_TOPOLOGY selection not resolved")
    topology_path = "include/linux/topology.h"
    header = source(topology_path)
    fallback_id = re.search(rf"(?m)^#ifndef topology_{family}_id\s*$", header)
    fallback_map = re.search(rf"(?m)^#ifndef topology_{family}_cpumask\s*$", header)
    include_generic, generic_lines = target_state(
        header, {}, r"^\s*#\s*include\s+<linux/arch_topology\.h>\s*$")
    include_arch, arch_lines = target_state(
        header, {}, r"^\s*#\s*include\s+<asm/topology\.h>\s*$")
    refs["contract"].extend(at(revision, topology_path, i)
                            for i in generic_lines + arch_lines)
    modern_boundary = bool(fallback_id and fallback_map and
                          len(generic_lines) == len(arch_lines) == 1 and
                          include_generic is True and include_arch is True and
                          generic_lines[0] < header[:fallback_id.start()].count("\n") + 1 and
                          arch_lines[0] < header[:fallback_id.start()].count("\n") + 1)
    if modern_boundary:
        refs["fallback"] = [at(revision, topology_path, header[:match.start()].count("\n") + 1)
                            for match in (fallback_id, fallback_map)]
    legacy_boundary = (family in {"book", "drawer"} and
                       fallback_id is None and fallback_map is None and
                       len(generic_lines) == len(arch_lines) == 1 and
                       include_generic is True and include_arch is True and
                       re.search(rf"(?m)^\s*#\s*define\s+topology_{family}_(?:id|cpumask)\b", header) is None)
    boundary_known = modern_boundary or legacy_boundary
    if not boundary_known:
        unknown.append("native-provider include order or fallback boundary not recognized")

    provider_names = (f"topology_{family}_id", f"topology_{family}_cpumask")
    generic_path = "include/linux/arch_topology.h"
    arch_path = f"arch/{arch}/include/asm/topology.h"
    if arch_path not in paths:
        generic_kbuild = source("include/asm-generic/Kbuild")
        mandatory = [(i, line) for i, line in enumerate(generic_kbuild.splitlines(), 1)
                     if re.fullmatch(r"\s*mandatory-y\s*\+=\s*topology\.h\s*", line)]
        if len(mandatory) == 1:
            refs["kconfig"].append(at(revision, "include/asm-generic/Kbuild", mandatory[0][0]))
            arch_path = "include/asm-generic/topology.h"
        else:
            unknown.append("asm/topology.h is absent and asm-generic mapping is unrecognized")
            row["source_refs"] = list(dict.fromkeys(ref for group in refs.values() for ref in group))
            return result
    symbols = {"CONFIG_SMP": smp, "CONFIG_GENERIC_ARCH_TOPOLOGY": generic,
               "CONFIG_SCHED_TOPOLOGY": sched_topology}
    for name, key in zip(provider_names, ("provider_id", "provider_map")):
        states: list[Truth] = []
        for path, included in ((generic_path, include_generic), (arch_path, include_arch)):
            state, lines = macro_state(source(path), symbols, name)
            states.append(tri_and(included, state))
            refs[key].extend(at(revision, path, line) for line in lines)
            if not lines:
                refs[key].append(at(revision, path))
        row["native_id" if key == "provider_id" else "native_map"] = tri_or(*states)
        if tri_or(*states) is None:
            unknown.append(f"{name} native declaration has unresolved conditions")

    driver_path = "drivers/base/topology.c"
    driver = source(driver_path)
    guard_name = f"TOPOLOGY_{family.upper()}_SYSFS"
    guard, guard_lines = macro_state(header, symbols | {
        provider_names[0]: row["native_id"],
        provider_names[1]: row["native_map"]}, guard_name)
    refs["contract"].extend(at(revision, topology_path, i) for i in guard_lines)
    if family in {"book", "drawer"}:
        if modern_boundary:
            exact_guard = list(re.finditer(
                rf"(?m)^#if defined\({provider_names[0]}\) && defined\({provider_names[1]}\)[ \t]*\n"
                rf"#define {guard_name}[ \t]*\n#endif[ \t]*$", header))
            if len(exact_guard) != 1 or len(guard_lines) != 1:
                unknown.append("book/drawer native-pair capability guard not recognized")
                guard = None
            else:
                refs["contract"].append(
                    at(revision, topology_path,
                       header[:exact_guard[0].start()].count("\n") + 1))
        elif legacy_boundary:
            legacy_name = f"CONFIG_SCHED_{family.upper()}"
            old_guards = list(re.finditer(rf"(?m)^#ifdef {legacy_name}[ \t]*$", driver))
            if guard_lines or len(old_guards) != 3:
                unknown.append("book/drawer legacy CONFIG guard shape not recognized")
                guard = None
            else:
                refs["contract"].extend(
                    at(revision, driver_path, driver[:match.start()].count("\n") + 1)
                    for match in old_guards)
                guard, config_refs = legacy_book_drawer_guard(
                    source, revision, arch, family, sched_topology)
                refs["kconfig"].extend(config_refs)
                if guard is None:
                    unknown.append(f"{legacy_name} selection or profile not resolved")
            symbols[legacy_name] = guard
        else:
            guard = None
    if guard_lines and fallback_id and any(
        i > header[:fallback_id.start()].count("\n") + 1 for i in guard_lines
    ):
        unknown.append("capability guard occurs after generic fallback")
        guard = None
    symbols[guard_name] = guard
    sibling_name = f"{family}_siblings" if family in {"book", "drawer"} else f"{family}_cpus"
    contract_patterns = (
        rf"^define_id_show_func\({family}_id\);$",
        rf"^static DEVICE_ATTR_RO\({family}_id\);$",
        rf"^define_siblings_read_func\({sibling_name}, {family}_cpumask\);$",
        rf"^static BIN_ATTR_RO\({sibling_name}, 0\);$",
        rf"^static BIN_ATTR_RO\({sibling_name}_list, 0\);$",
    )
    contract_states: list[Truth] = []
    for pattern in contract_patterns:
        state, lines = target_state(driver, symbols, pattern)
        contract_states.append(state)
        refs["contract"].extend(at(revision, driver_path, i) for i in lines)
        if len(lines) != 1 or state is None:
            unknown.append(f"provider-consumer mapping unresolved: {pattern}")
    arrays = (rf"&dev_attr_{family}_id\.attr,",
              rf"&bin_attr_{sibling_name},",
              rf"&bin_attr_{sibling_name}_list,")
    states = []
    for pattern in arrays:
        state, lines = target_state(driver, symbols, pattern)
        states.append(state)
        refs["export"].extend(at(revision, driver_path, i) for i in lines)
        if state is None:
            unknown.append(f"attribute registration unresolved: {pattern}")
    if (".attrs = default_attrs" not in driver or ".bin_attrs = bin_attrs" not in driver
            or "sysfs_create_group(&dev->kobj, &topology_attr_group)" not in driver):
        unknown.append("topology attribute group registration not recognized")
    elif ".is_visible" in driver:
        unknown.append("runtime .is_visible callback requires separate analysis")
    elif len(set(states)) == 1 and states[0] is not None:
        row["exported"] = states[0]
        row["guard_resolved"] = True
    else:
        unknown.append("attribute family has partial or unknown export visibility")

    if (boundary_known and all(state is not None for state in contract_states) and
            row["guard_resolved"] is True and
            (row["exported"] is False or all(contract_states))):
        row["paired_native_contract"] = True
    elif row["exported"] is True and any(state is False for state in contract_states):
        unknown.append("exported attribute lacks an active read/show declaration")

    row["source_refs"] = list(dict.fromkeys(ref for group in refs.values() for ref in group))
    return result


def from_git(repo: Path, revision: str, arch: str, smp: bool,
             sysfs: bool, family: str,
             sched_topology: Truth = None) -> dict:
    if not re.fullmatch(r"[0-9a-fA-F]{7,40}\^?", revision):
        raise ValueError("revision must be a commit SHA, optionally followed by ^")
    resolved = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "--verify", f"{revision}^{{commit}}"],
        text=True).strip()

    def source(path: str) -> str:
        return subprocess.check_output(
            ["git", "-C", str(repo), "show", f"{resolved}:{path}"], text=True)

    paths = subprocess.check_output(
        ["git", "-C", str(repo), "ls-tree", "-r", "--name-only", resolved,
         f"arch/{arch}"], text=True).splitlines()
    return extract(source, paths, resolved, arch, smp, sysfs, family,
                   sched_topology)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linux-dir", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--arch", required=True)
    parser.add_argument("--smp", choices=("on", "off"), required=True)
    parser.add_argument("--sysfs", choices=("on", "off"), required=True)
    parser.add_argument("--family", required=True)
    parser.add_argument("--sched-topology", choices=("on", "off", "unknown"),
                        default="unknown",
                        help="actual CONFIG_SCHED_TOPOLOGY value; required to resolve s390 book/drawer")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = from_git(args.linux_dir, args.revision, args.arch,
                       args.smp == "on", args.sysfs == "on", args.family,
                       {"on": True, "off": False, "unknown": None}[args.sched_topology])
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
