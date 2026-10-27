"""Behavior checks for the bounded historical topology/sysfs extractor."""

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "experiments" / "case_taxonomy"


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


extractor = load_module("topology_contract_extract", "topology_contract_extract.py")
evaluator = load_module("contract_check_pilot_v1", "contract_check_pilot_v1.py")


def sources(*, guarded: bool, arch: str = "s390") -> dict[str, str]:
    def wrap(lines: str) -> str:
        return "#ifdef TOPOLOGY_CLUSTER_SYSFS\n" + lines + "#endif\n" if guarded else lines

    declarations = wrap(
        "define_id_show_func(cluster_id);\n"
        "static DEVICE_ATTR_RO(cluster_id);\n"
        "define_siblings_read_func(cluster_cpus, cluster_cpumask);\n"
        "static BIN_ATTR_RO(cluster_cpus, 0);\n"
        "static BIN_ATTR_RO(cluster_cpus_list, 0);\n"
    )
    array_id = wrap("&dev_attr_cluster_id.attr,\n")
    array_map = wrap("&bin_attr_cluster_cpus,\n&bin_attr_cluster_cpus_list,\n")
    driver = (
        declarations + "static struct bin_attribute *bin_attrs[] = {\n" + array_map + "};\n"
        "static struct attribute *default_attrs[] = {\n" + array_id + "};\n"
        "static const struct attribute_group topology_attr_group = {\n"
        ".attrs = default_attrs,\n.bin_attrs = bin_attrs,\n};\n"
        "return sysfs_create_group(&dev->kobj, &topology_attr_group);\n"
    )
    header = (
        "#ifndef _LINUX_TOPOLOGY_H\n#define _LINUX_TOPOLOGY_H\n"
        "#include <linux/arch_topology.h>\n#include <asm/topology.h>\n"
        "#if defined(topology_cluster_id) && defined(topology_cluster_cpumask)\n"
        "#define TOPOLOGY_CLUSTER_SYSFS\n#endif\n"
        "#ifndef topology_cluster_id\n#define topology_cluster_id(cpu) (-1)\n#endif\n"
        "#ifndef topology_cluster_cpumask\n"
        "#define topology_cluster_cpumask(cpu) cpumask_of(cpu)\n#endif\n#endif\n"
    )
    generic = (
        "#ifndef _LINUX_ARCH_TOPOLOGY_H\n#define _LINUX_ARCH_TOPOLOGY_H\n"
        "#ifdef CONFIG_GENERIC_ARCH_TOPOLOGY\n"
        "#define topology_cluster_id(cpu) cpu_topology[cpu].cluster_id\n"
        "#define topology_cluster_cpumask(cpu) &cpu_topology[cpu].cluster_sibling\n"
        "#endif\n#endif\n"
    )
    arch_header = (
        "#ifndef _ASM_TOPOLOGY_H\n#define _ASM_TOPOLOGY_H\n"
        "#ifdef CONFIG_SMP\n"
        "#define topology_cluster_id(cpu) per_cpu(cpu_l2c_id, cpu)\n"
        "#define topology_cluster_cpumask(cpu) cpu_clustergroup_mask(cpu)\n"
        "#endif\n#endif\n"
    ) if arch == "x86" else "#ifndef _ASM_TOPOLOGY_H\n#define _ASM_TOPOLOGY_H\n#endif\n"
    selection = "select GENERIC_ARCH_TOPOLOGY\n" if arch == "arm64" else (
        "select GENERIC_ARCH_TOPOLOGY if SMP\n" if arch == "riscv" else "")
    return {
        "drivers/base/Makefile": "obj-y := cpu.o topology.o cacheinfo.o\n",
        "drivers/base/Kconfig": "config GENERIC_ARCH_TOPOLOGY\n\tbool\n",
        f"arch/{arch}/Kconfig": "config " + {"arm64": "ARM64", "riscv": "RISCV"}.get(arch, "ARCH")
        + "\n\tbool\n\t" + selection,
        "drivers/base/topology.c": driver,
        "include/linux/topology.h": header,
        "include/linux/arch_topology.h": generic,
        f"arch/{arch}/include/asm/topology.h": arch_header,
    }


def extract_fixture(files: dict[str, str], arch: str, *, smp: bool,
                    sysfs: bool = True, family: str = "cluster",
                    sched_topology: bool | None = None) -> dict:
    paths = [path for path in files if path.startswith(f"arch/{arch}/")]
    return extractor.extract(files.__getitem__, paths,
                             "1234567890abcdef", arch, smp, sysfs, family,
                             sched_topology)


def book_drawer_sources(*, family: str, guarded: bool,
                        arch: str = "s390") -> dict[str, str]:
    assert family in {"book", "drawer"}
    files = sources(guarded=True, arch=arch)
    driver = files["drivers/base/topology.c"]
    driver = driver.replace("cluster_cpus", f"{family}_siblings")
    driver = driver.replace("cluster_id", f"{family}_id")
    driver = driver.replace("cluster_cpumask", f"{family}_cpumask")
    if not guarded:
        driver = driver.replace("TOPOLOGY_CLUSTER_SYSFS", f"CONFIG_SCHED_{family.upper()}")
    else:
        driver = driver.replace("TOPOLOGY_CLUSTER_SYSFS", f"TOPOLOGY_{family.upper()}_SYSFS")
    files["drivers/base/topology.c"] = driver
    files["include/linux/arch_topology.h"] = (
        "#ifndef _LINUX_ARCH_TOPOLOGY_H\n#define _LINUX_ARCH_TOPOLOGY_H\n#endif\n")
    guard = (
        f"#if defined(topology_{family}_id) && defined(topology_{family}_cpumask)\n"
        f"#define TOPOLOGY_{family.upper()}_SYSFS\n#endif\n"
    ) if guarded else ""
    fallback = (
        f"#ifndef topology_{family}_id\n"
        f"#define topology_{family}_id(cpu) (-1)\n#endif\n"
        f"#ifndef topology_{family}_cpumask\n"
        f"#define topology_{family}_cpumask(cpu) cpumask_of(cpu)\n#endif\n"
    ) if guarded else ""
    files["include/linux/topology.h"] = (
        "#ifndef _LINUX_TOPOLOGY_H\n#define _LINUX_TOPOLOGY_H\n"
        "#include <linux/arch_topology.h>\n#include <asm/topology.h>\n"
        + guard + fallback + "#endif\n"
    )
    if arch == "s390":
        files["arch/s390/include/asm/topology.h"] = (
            "#ifndef _ASM_TOPOLOGY_H\n#define _ASM_TOPOLOGY_H\n"
            "#ifdef CONFIG_SCHED_TOPOLOGY\n"
            f"#define topology_{family}_id(cpu) cpu_topology[cpu].{family}_id\n"
            f"#define topology_{family}_cpumask(cpu) &cpu_topology[cpu].{family}_mask\n"
            "#endif\n#endif\n"
        )
    else:
        files[f"arch/{arch}/include/asm/topology.h"] = (
            "#ifndef _ASM_TOPOLOGY_H\n#define _ASM_TOPOLOGY_H\n#endif\n")
    files["arch/s390/Kconfig"] = (
        "config SCHED_BOOK\n\tdef_bool n\n"
        "config SCHED_DRAWER\n\tdef_bool n\n"
        "config SCHED_TOPOLOGY\n\tdef_bool y\n"
        "\tselect SCHED_BOOK\n\tselect SCHED_DRAWER\n"
    )
    return files


class TopologyContractExtractTests(unittest.TestCase):
    def status(self, result: dict) -> str:
        return evaluator.capability(result["records"][0])[0]

    def test_old_and_guarded_exports_across_arch_profiles(self):
        cases = (
            ("s390", True, "hit", "normal"),
            ("x86", False, "hit", "normal"),
            ("x86", True, "normal", "normal"),
            ("arm64", True, "normal", "normal"),
            ("riscv", True, "normal", "normal"),
            ("riscv", False, "hit", "normal"),
        )
        for arch, smp, old, fixed in cases:
            with self.subTest(arch=arch, smp=smp):
                old_result = extract_fixture(sources(guarded=False, arch=arch), arch, smp=smp)
                fixed_result = extract_fixture(sources(guarded=True, arch=arch), arch, smp=smp)
                self.assertEqual(self.status(old_result), old)
                self.assertEqual(self.status(fixed_result), fixed)
                self.assertTrue(old_result["source_refs_by_fact"]["export"])
                self.assertEqual(old_result["authority_provenance"]["level"],
                                 "implementation_contract_candidate")

    def test_unknown_provider_condition_abstains(self):
        files = sources(guarded=True, arch="x86")
        path = "arch/x86/include/asm/topology.h"
        files[path] = files[path].replace(
            "#define topology_cluster_id(cpu)",
            "#if CONFIG_UNKNOWN\n#define topology_cluster_id(cpu)").replace(
            "per_cpu(cpu_l2c_id, cpu)\n", "per_cpu(cpu_l2c_id, cpu)\n#endif\n")
        result = extract_fixture(files, "x86", smp=True)
        self.assertEqual(self.status(result), "insufficient")
        self.assertIsNone(result["records"][0]["native_id"])
        self.assertTrue(any("unresolved conditions" in item for item in result["unknown_reasons"]))

    def test_missing_arch_header_uses_explicit_asm_generic_mapping(self):
        files = sources(guarded=True, arch="riscv")
        del files["arch/riscv/include/asm/topology.h"]
        files["include/asm-generic/Kbuild"] = "mandatory-y += topology.h\n"
        files["include/asm-generic/topology.h"] = (
            "#ifndef _ASM_GENERIC_TOPOLOGY_H\n#define _ASM_GENERIC_TOPOLOGY_H\n#endif\n")
        result = extract_fixture(files, "riscv", smp=True)
        self.assertEqual(self.status(result), "normal")
        self.assertTrue(any("asm-generic/Kbuild:1" in ref for ref in
                            result["source_refs_by_fact"]["kconfig"]))
        del files["include/asm-generic/Kbuild"]
        # An absent architecture header without a known generated mapping
        # must remain unresolved, rather than assuming the generic header.
        files["include/asm-generic/Kbuild"] = "mandatory-y += another.h\n"
        self.assertEqual(self.status(extract_fixture(files, "riscv", smp=True)),
                         "insufficient")

    def test_unrecognized_kconfig_selection_abstains(self):
        files = sources(guarded=True, arch="arm64")
        files["arch/arm64/Kconfig"] = files["arch/arm64/Kconfig"].replace(
            "select GENERIC_ARCH_TOPOLOGY", "select GENERIC_ARCH_TOPOLOGY if MAYBE")
        result = extract_fixture(files, "arm64", smp=True)
        self.assertEqual(self.status(result), "insufficient")
        self.assertIn("GENERIC_ARCH_TOPOLOGY selection not resolved", result["unknown_reasons"])

    def test_unknown_outer_kconfig_condition_abstains(self):
        files = sources(guarded=True, arch="arm64")
        files["arch/arm64/Kconfig"] = files["arch/arm64/Kconfig"].replace(
            "\tselect GENERIC_ARCH_TOPOLOGY",
            "if UNKNOWN\n\tselect GENERIC_ARCH_TOPOLOGY\nendif")
        result = extract_fixture(files, "arm64", smp=True)
        self.assertEqual(self.status(result), "insufficient")

    def test_disabled_provider_include_abstains(self):
        files = sources(guarded=True, arch="arm64")
        path = "include/linux/topology.h"
        files[path] = files[path].replace(
            "#include <linux/arch_topology.h>",
            "#if 0\n#include <linux/arch_topology.h>\n#endif")
        result = extract_fixture(files, "arm64", smp=True)
        self.assertEqual(self.status(result), "insufficient")
        self.assertFalse(result["records"][0]["native_id"])

    def test_conditional_topology_object_abstains(self):
        files = sources(guarded=False, arch="s390")
        files["drivers/base/Makefile"] = (
            "obj-y := cpu.o\nobj-$(CONFIG_OPTION) += topology.o\n")
        result = extract_fixture(files, "s390", smp=True)
        self.assertEqual(self.status(result), "insufficient")
        self.assertIsNone(result["records"][0]["interface_built"])

    def test_provider_undef_is_respected(self):
        files = sources(guarded=False, arch="x86")
        path = "arch/x86/include/asm/topology.h"
        files[path] = files[path].replace(
            "#define topology_cluster_cpumask(cpu) cpu_clustergroup_mask(cpu)\n",
            "#define topology_cluster_cpumask(cpu) cpu_clustergroup_mask(cpu)\n"
            "#undef topology_cluster_id\n")
        result = extract_fixture(files, "x86", smp=True)
        self.assertEqual(self.status(result), "hit")
        self.assertFalse(result["records"][0]["native_id"])

    def test_unknown_read_function_activation_abstains(self):
        files = sources(guarded=False, arch="x86")
        path = "drivers/base/topology.c"
        files[path] = files[path].replace(
            "define_siblings_read_func(cluster_cpus, cluster_cpumask);",
            "#if CONFIG_UNKNOWN\n"
            "define_siblings_read_func(cluster_cpus, cluster_cpumask);\n#endif")
        result = extract_fixture(files, "x86", smp=True)
        self.assertEqual(self.status(result), "insufficient")
        self.assertIsNone(result["records"][0]["paired_native_contract"])

    def test_unknown_export_guard_abstains(self):
        files = sources(guarded=False, arch="s390")
        path = "drivers/base/topology.c"
        files[path] = files[path].replace(
            "&dev_attr_cluster_id.attr,", "#if CONFIG_UNKNOWN\n&dev_attr_cluster_id.attr,\n#endif")
        result = extract_fixture(files, "s390", smp=True)
        self.assertEqual(self.status(result), "insufficient")
        self.assertIsNone(result["records"][0]["exported"])

    def test_unrecognized_fallback_boundary_abstains(self):
        files = sources(guarded=False, arch="s390")
        path = "include/linux/topology.h"
        files[path] = files[path].replace(
            "#include <linux/arch_topology.h>\n",
            "#ifndef topology_cluster_id\n#define topology_cluster_id(cpu) (-1)\n#endif\n"
            "#include <linux/arch_topology.h>\n", 1)
        result = extract_fixture(files, "s390", smp=True)
        self.assertEqual(self.status(result), "insufficient")

    def test_ppin_and_nonbuilt_interface_do_not_claim_contract_hit(self):
        files = sources(guarded=True, arch="x86")
        files["drivers/base/topology.c"] += (
            "&dev_attr_ppin.attr,\n"
            "if (attr == &dev_attr_ppin.attr && !topology_ppin(dev->id)) return 0;\n"
            ".is_visible = topology_is_visible,\n")
        ppin = extract_fixture(files, "x86", smp=True, family="ppin")
        self.assertEqual(self.status(ppin), "insufficient")
        self.assertIsNone(ppin["records"][0]["paired_native_contract"])
        disabled = extract_fixture(files, "x86", smp=True, sysfs=False)
        self.assertEqual(self.status(disabled), "not_applicable")

    def test_book_drawer_legacy_and_native_pair_guards(self):
        for family in ("book", "drawer"):
            for guarded in (False, True):
                for arch in ("s390", "x86"):
                    for sched in (False, True):
                        with self.subTest(family=family, guarded=guarded,
                                          arch=arch, sched=sched):
                            files = book_drawer_sources(
                                family=family, guarded=guarded, arch=arch)
                            result = extract_fixture(files, arch, smp=True,
                                                     family=family,
                                                     sched_topology=sched)
                            self.assertEqual(self.status(result), "normal")
                            self.assertTrue(result["records"][0]["paired_native_contract"])
                            self.assertEqual(result["records"][0]["exported"],
                                             arch == "s390" and sched)
                            self.assertIn(f"{family}_siblings", files["drivers/base/topology.c"])

    def test_legacy_s390_requires_explicit_sched_topology_profile(self):
        for guarded in (False, True):
            files = book_drawer_sources(family="book", guarded=guarded)
            result = extract_fixture(files, "s390", smp=True, family="book")
            self.assertEqual(self.status(result), "insufficient")
            self.assertIsNone(result["records"][0]["exported"])

    def test_legacy_guard_can_expose_unpaired_provider(self):
        files = book_drawer_sources(family="drawer", guarded=False)
        path = "arch/s390/include/asm/topology.h"
        files[path] = files[path].replace(
            "#define topology_drawer_cpumask(cpu) &cpu_topology[cpu].drawer_mask\n", "")
        result = extract_fixture(files, "s390", smp=True, family="drawer",
                                 sched_topology=True)
        self.assertEqual(self.status(result), "hit")
        self.assertTrue(result["records"][0]["native_id"])
        self.assertFalse(result["records"][0]["native_map"])
        files = book_drawer_sources(family="drawer", guarded=True)
        files[path] = files[path].replace(
            "#define topology_drawer_cpumask(cpu) &cpu_topology[cpu].drawer_mask\n", "")
        result = extract_fixture(files, "s390", smp=True, family="drawer",
                                 sched_topology=True)
        self.assertEqual(self.status(result), "normal")
        self.assertFalse(result["records"][0]["exported"])

    def test_book_drawer_unknown_shapes_abstain(self):
        files = book_drawer_sources(family="book", guarded=True)
        path = "include/linux/topology.h"
        files[path] = files[path].replace(
            "defined(topology_book_cpumask)", "defined(topology_core_cpumask)")
        self.assertEqual(self.status(extract_fixture(
            files, "s390", smp=True, family="book", sched_topology=True)),
            "insufficient")
        files = book_drawer_sources(family="book", guarded=False)
        files["arch/s390/Kconfig"] = files["arch/s390/Kconfig"].replace(
            "\tselect SCHED_BOOK\n", "")
        self.assertEqual(self.status(extract_fixture(
            files, "s390", smp=True, family="book", sched_topology=True)),
            "insufficient")
        files = book_drawer_sources(family="book", guarded=False)
        files["drivers/base/topology.c"] = files["drivers/base/topology.c"].replace(
            "book_siblings", "book_cpus")
        self.assertEqual(self.status(extract_fixture(
            files, "s390", smp=True, family="book", sched_topology=True)),
            "insufficient")
        files = book_drawer_sources(family="book", guarded=True)
        files["include/linux/topology.h"] = files["include/linux/topology.h"].replace(
            "#ifndef topology_book_cpumask\n", "#ifdef TOPOLOGY_UNKNOWN\n")
        self.assertEqual(self.status(extract_fixture(
            files, "s390", smp=True, family="book", sched_topology=True)),
            "insufficient")


if __name__ == "__main__":
    unittest.main()
