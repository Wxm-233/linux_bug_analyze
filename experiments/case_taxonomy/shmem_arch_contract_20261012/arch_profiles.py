"""Generate real historical configs and execute header-derived geometry probes.

No historical kernel is booted. ARM64 expressions run under qemu-aarch64.
The Linux source archive and build directories stay in a WSL cache, not Git.
"""
from __future__ import annotations

import json
import argparse
import hashlib
import shutil
import subprocess
from pathlib import Path

FIX = "9fd154ba926b34c833b7bfc4c14ee2e931b3d743"
REPO = Path("/root/repos/linux")
WORK = Path("/root/.cache/linux-bug-analyze/shmem-contract-20261012")
OUT = Path(__file__).resolve().parent / "profiles"
PROFILES = (
    ("x86_64_4k", "x86_64", "x86", "gcc", 12),
    ("arm64_4k", "arm64", "arm64", "aarch64-linux-gnu-gcc", 12),
    ("arm64_64k", "arm64", "arm64", "aarch64-linux-gnu-gcc", 16),
)
KEYS = ("PAGE_SHIFT", "PMD_SHIFT", "HPAGE_PMD_SHIFT", "HPAGE_PMD_ORDER",
        "XA_CHUNK_SHIFT", "MAX_XAS_ORDER", "MAX_PAGECACHE_ORDER")
RECORDS: list[dict] = []


def run(args: list[str], log: Path, cwd: Path | None = None) -> str:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(result.stdout + result.stderr)
    RECORDS.append({"argv": args, "cwd": str(cwd) if cwd else None,
                    "exit_code": result.returncode, "log": str(log)})
    (OUT / "commands.json").write_text(json.dumps(RECORDS, indent=2) + "\n")
    if result.returncode:
        raise RuntimeError(f"Failed: {args}; see {log}\n{result.stderr[-2000:]}")
    return result.stdout


def source_tree() -> Path:
    tree = WORK / "linux"
    marker = WORK / "source_revision"
    if marker.exists():
        if marker.read_text().strip() != FIX:
            raise RuntimeError("Existing cache has another revision")
        return tree
    tree.mkdir(parents=True, exist_ok=True)
    archive = subprocess.Popen(["git", "-C", str(REPO), "archive", FIX],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    extracted = subprocess.run(["tar", "-xf", "-", "-C", str(tree)],
                               stdin=archive.stdout, capture_output=True)
    archive.stdout.close()
    error = archive.stderr.read()
    rc = archive.wait()
    if rc or extracted.returncode:
        raise RuntimeError(f"archive={rc}, tar={extracted.returncode}: {error!r}")
    marker.write_text(FIX + "\n")
    return tree


def config_values(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text().splitlines():
        if line.startswith("CONFIG_") and "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
        elif line.startswith("# CONFIG_") and line.endswith(" is not set"):
            values[line[2:-11]] = "n"
    return values


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tree = source_tree()
    probe = OUT / "geometry.c"
    probe.write_text("#include <linux/pagemap.h>\n#include <linux/huge_mm.h>\n"
                     "extern int printf(const char *, ...);\nint main(void) {\n" +
                     "\n".join(f'printf("{key}=%lu\\n", (unsigned long)({key}));'
                               for key in KEYS) + "\nreturn 0;\n}\n")
    results = []
    for name, arch, srcarch, cc, shift in PROFILES:
        dest = OUT / name
        dest.mkdir(exist_ok=True)
        build = WORK / name
        base = ["make", "-C", str(tree), f"O={build}", f"ARCH={arch}"]
        if arch == "arm64":
            base += ["CROSS_COMPILE=aarch64-linux-gnu-"]
        print(f"Preparing {name}", flush=True)
        run(base + ["defconfig"], dest / "defconfig.log")
        edits = [str(tree / "scripts/config"), "--file", str(build / ".config"),
                 "--enable", "TRANSPARENT_HUGEPAGE", "--enable", "SHMEM",
                 "--enable", "TMPFS", "--disable", "PREEMPT_RT",
                 "--disable", "BASE_SMALL"]
        if arch == "arm64":
            for size in (4, 16, 64):
                edits += ["--enable" if size == 2 ** (shift - 10) else "--disable",
                          f"ARM64_{size}K_PAGES"]
            for bits in (39, 42, 47, 48, 52):
                edits += ["--enable" if bits == 48 else "--disable",
                          f"ARM64_VA_BITS_{bits}"]
        run(edits, dest / "config_edits.log")
        run(base + ["olddefconfig"], dest / "olddefconfig.log")
        values = config_values(build / ".config")
        for key in ("CONFIG_TRANSPARENT_HUGEPAGE", "CONFIG_SHMEM", "CONFIG_TMPFS",
                    "CONFIG_HAVE_ARCH_TRANSPARENT_HUGEPAGE"):
            if values.get(key) != "y":
                raise RuntimeError(f"{name}: {key} not enabled after Kconfig")
        # A hidden disabled bool may be omitted entirely from .config.
        if values.get("CONFIG_BASE_SMALL", "n") != "n":
            raise RuntimeError(f"{name}: BASE_SMALL was not kept disabled")
        if arch == "arm64" and values.get("CONFIG_ARM64_VA_BITS") != "48":
            raise RuntimeError(f"{name}: VA bits changed")
        run(base + ["-j4", "prepare"], dest / "prepare.log")
        shutil.copyfile(build / ".config", dest / "config")
        shutil.copyfile(build / "include/generated/autoconf.h", dest / "autoconf.h")
        include_paths = [tree / f"arch/{srcarch}/include",
                         build / f"arch/{srcarch}/include/generated", tree / "include",
                         build / "include", tree / f"arch/{srcarch}/include/uapi",
                         build / f"arch/{srcarch}/include/generated/uapi",
                         tree / "include/uapi", build / "include/generated/uapi"]
        binary = dest / "geometry"
        args = [cc, "-O2", "-D__KERNEL__", "-fno-stack-protector",
                "-include", str(tree / "include/linux/kconfig.h"),
                "-include", str(tree / "include/linux/compiler_types.h")]
        for path in include_paths:
            args += ["-I", str(path)]
        args += [str(probe), "-o", str(binary)]
        run(args, dest / "compile.log")
        command = (["qemu-aarch64", "-L", "/usr/aarch64-linux-gnu"]
                   if arch == "arm64" else []) + [str(binary)]
        output = run(command, dest / "geometry.stdout")
        geometry = {key: int(value) for key, value in
                    (line.split("=", 1) for line in output.splitlines())}
        if geometry["PAGE_SHIFT"] != shift:
            raise RuntimeError(f"{name}: generated PAGE_SHIFT != requested value")
        relevant = {"CONFIG_X86_64", "CONFIG_PAGE_SHIFT", "CONFIG_SHMEM", "CONFIG_TMPFS",
                    "CONFIG_HAVE_ARCH_TRANSPARENT_HUGEPAGE", "CONFIG_TRANSPARENT_HUGEPAGE",
                    "CONFIG_XARRAY_MULTI", "CONFIG_BASE_SMALL", "CONFIG_PREEMPT_RT",
                    "CONFIG_ARCH_FORCE_MAX_ORDER", "CONFIG_ARM64_4K_PAGES",
                    "CONFIG_ARM64_16K_PAGES", "CONFIG_ARM64_64K_PAGES",
                    "CONFIG_ARM64_VA_BITS", "CONFIG_ARM64_VA_BITS_48",
                    "CONFIG_PGTABLE_LEVELS"}
        chosen = {key: value for key, value in values.items() if key in relevant}
        chosen["CONFIG_BASE_SMALL"] = values.get("CONFIG_BASE_SMALL", "n")
        results.append({"profile": name, "arch": arch, "revision": FIX,
                        "configuration": chosen, "geometry": geometry,
                        "execution": "qemu-aarch64 user mode" if arch == "arm64"
                        else "native x86_64 userspace", "kernel_boot": False})
        (OUT / "results.json").write_text(json.dumps(results, indent=2) + "\n")
        print(json.dumps({"profile": name, "geometry": geometry}), flush=True)


def certify_saved() -> None:
    """Check only this experiment's configuration and directly relevant sources.

    No historical audit trees are traversed and no probes are re-executed.
    """
    stage = OUT.parent
    records = json.loads((OUT / "results.json").read_text())
    expected = {"x86_64_4k": (12, 21, 9, 9),
                "arm64_4k": (12, 21, 9, 9), "arm64_64k": (16, 29, 13, 11)}
    if len(records) != 3 or {item["profile"] for item in records} != set(expected):
        raise RuntimeError("expected three unique completed profiles")
    sources = ["init/Kconfig", "arch/Kconfig", "arch/x86/Kconfig", "arch/arm64/Kconfig",
               "arch/x86/include/asm/page_types.h", "arch/x86/include/asm/pgtable_types.h",
               "arch/arm64/include/asm/page-def.h", "arch/arm64/include/asm/pgtable-hwdef.h",
               "mm/Kconfig", "include/linux/huge_mm.h", "include/linux/pagemap.h",
               "include/linux/xarray.h", "mm/shmem.c", "lib/xarray.c"]
    identities = []
    for path in sources:
        data = (WORK / "linux" / path).read_bytes()
        actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        expected_blob = subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", f"{FIX}:{path}"], text=True).strip()
        if actual != expected_blob:
            raise RuntimeError(f"cached source changed: {path}")
        identities.append({"path": path, "git_blob": actual})
    profiles = []
    mandatory = ("CONFIG_MMU", "CONFIG_SHMEM", "CONFIG_TMPFS", "CONFIG_XARRAY_MULTI",
                 "CONFIG_HAVE_ARCH_TRANSPARENT_HUGEPAGE", "CONFIG_TRANSPARENT_HUGEPAGE",
                 "CONFIG_PGTABLE_HAS_HUGE_LEAVES")
    for record in records:
        name = record["profile"]
        geometry = record["geometry"]
        if tuple(geometry[k] for k in ("PAGE_SHIFT", "PMD_SHIFT", "HPAGE_PMD_ORDER",
                                       "MAX_PAGECACHE_ORDER")) != expected[name]:
            raise RuntimeError(f"{name}: geometry differs from independent source expectation")
        if geometry["XA_CHUNK_SHIFT"] != 6 or geometry["MAX_XAS_ORDER"] != 11:
            raise RuntimeError(f"{name}: unexpected xarray geometry")
        config = OUT / name / "config"
        raw = config.read_text().splitlines()
        values = config_values(config)
        if any(values.get(key) != "y" for key in mandatory):
            raise RuntimeError(f"{name}: necessary config not enabled")
        for key in ("CONFIG_BASE_SMALL", "CONFIG_PREEMPT_RT"):
            if values.get(key, "n") != "n":
                raise RuntimeError(f"{name}: {key} not disabled")
        selected = {key: values[key] for key in mandatory}
        selected["CONFIG_PGTABLE_LEVELS"] = values["CONFIG_PGTABLE_LEVELS"]
        if name.startswith("arm64"):
            if values.get("CONFIG_ARM64_VA_BITS") != "48":
                raise RuntimeError(f"{name}: VA48 not selected")
            granule = "CONFIG_ARM64_64K_PAGES" if name.endswith("64k") else "CONFIG_ARM64_4K_PAGES"
            if values.get(granule) != "y":
                raise RuntimeError(f"{name}: granule not selected")
            selected.update({granule: "y", "CONFIG_ARM64_VA_BITS": "48"})
        generated = OUT / name / "autoconf.h"
        if config.read_bytes() != (WORK / name / ".config").read_bytes():
            raise RuntimeError(f"{name}: config no longer matches generated build")
        if generated.read_bytes() != (WORK / name / "include/generated/autoconf.h").read_bytes():
            raise RuntimeError(f"{name}: autoconf no longer matches build")
        profiles.append({"profile": name, "geometry": geometry, "necessary_configuration": selected,
                         "disabled_bools": {key: {"effective": "n", "raw":
                             next((line for line in raw if line.startswith(key + "=") or
                                   line == "# " + key + " is not set"), "hidden/not emitted")}
                             for key in ("CONFIG_BASE_SMALL", "CONFIG_PREEMPT_RT")},
                         "config_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
                         "autoconf_sha256": hashlib.sha256(generated.read_bytes()).hexdigest()})
    harness = stage / "consumer/source/tools/testing/radix-tree"
    shim = {"map_shift": (harness / "generated/map-shift.h").read_text().strip(),
            "autoconf": (harness / "generated/autoconf.h").read_text().splitlines(),
            "kernel_page_shift": 12,
            "warning_semantics": "official tools/include/asm/bug.h WARN_ON returns predicate and writes an assertion line to stderr",
            "execution": "native x86_64 userspace; ARM64 geometry is an authenticated order input"}
    if shim["map_shift"] != "#define XA_CHUNK_SHIFT 6" or "#define CONFIG_XARRAY_MULTI 1" not in shim["autoconf"]:
        raise RuntimeError("consumer configuration differs from certified chunk/MULTI")
    consumer = json.loads((stage / "consumer/consumer_result.json").read_text())
    selection = json.loads((stage / "selection/results.json").read_text())
    geometry_hash = hashlib.sha256((OUT / "results.json").read_bytes()).hexdigest()
    if not consumer["passed"] or not selection["passed"]:
        raise RuntimeError("saved consumer or selection result failed")
    if consumer["geometry_sha256"] != geometry_hash or selection["geometry_sha256"] != geometry_hash:
        raise RuntimeError("results refer to another geometry source")
    report = {"run_id": "shmem_arch_contract_20261012", "status": "complete_partial_chain",
              "revision": FIX, "parent": consumer["parent"], "source_identity": identities,
              "profiles": profiles, "consumer_adapter": shim,
              "geometry_sha256": geometry_hash, "selection_cases": selection["cases_total"],
              "consumer_calls": len(consumer["results"]), "kernel_boot": False,
              "scope": "real Kconfig/header geometry; selection doubles and original xarray consumer in separate executables"}
    (stage / "certification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "profiles": len(profiles),
                      "selection_cases": report["selection_cases"], "consumer_calls": report["consumer_calls"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--certify-only", action="store_true")
    args = parser.parse_args()
    if args.certify_only:
        certify_saved()
    else:
        main()
