"""Boundary checks for the post-read, version-aware topology extractor."""

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "experiments" / "case_taxonomy"
sys.path.insert(0, str(ROOT))
from topology_v3_versioned import build_topology, inspect_snapshot  # noqa: E402


REVISION = "1" * 40


def legacy_files() -> dict[str, str | None]:
    driver = (
        "#define define_id_show_func(name) topology_##name(cpu)\n"
        "#define define_siblings_show_func(name) topology_##name(cpu)\n"
        "#define define_one_ro_named(_name, _func) "
        "static SYSDEV_ATTR(_name, 0444, _func, NULL)\n"
        "#define define_one_ro(_name) static SYSDEV_ATTR(_name, 0444, show_##_name, NULL)\n"
        "#ifdef CONFIG_SCHED_BOOK\n"
        "define_id_show_func(book_id);\n"
        "define_one_ro(book_id);\n"
        "define_siblings_show_func(book_cpumask);\n"
        "define_one_ro_named(book_siblings, show_book_cpumask);\n"
        "define_one_ro_named(book_siblings_list, show_book_cpumask_list);\n"
        "#endif\n"
        "static struct attribute *default_attrs[] = {\n"
        "#ifdef CONFIG_SCHED_BOOK\n"
        "&attr_book_id.attr,\n&attr_book_siblings.attr,\n"
        "&attr_book_siblings_list.attr,\n"
        "#endif\n};\n"
        "static struct attribute_group topology_attr_group = {\n"
        ".attrs = default_attrs,\n};\n"
        "sysfs_create_group(&sys_dev->kobj, &topology_attr_group);\n"
        "device_initcall(topology_sysfs_init);\n"
    )
    return {
        "drivers/base/Makefile": "obj-$(CONFIG_SMP) += topology.o\n",
        "drivers/base/topology.c": driver,
        "include/linux/topology.h": "#include <asm/topology.h>\n",
        "include/linux/arch_topology.h": None,
        "include/asm-generic/topology.h": "/* no book override */\n",
        "arch/s390/include/asm/topology.h": (
            "#ifdef CONFIG_SCHED_TOPOLOGY\n"
            "#define topology_book_id(cpu) native_id(cpu)\n"
            "#define topology_book_cpumask(cpu) native_mask(cpu)\n"
            "#endif\n#include <asm-generic/topology.h>\n"),
        "arch/x86/include/asm/topology.h": "/* no book override */\n",
        "arch/s390/Kconfig": (
            "config SCHED_BOOK\n\tdef_bool n\n"
            "config SCHED_TOPOLOGY\n\tbool\n\tselect SCHED_BOOK\n"),
        "arch/x86/Kconfig": "config X86\n\tbool\n",
    }


class VersionedTopologyTests(unittest.TestCase):
    def test_obj_smp_build_is_profile_specific(self):
        makefile = "obj-$(CONFIG_SMP) += topology.o\n"
        self.assertEqual(build_topology(makefile, True)[:1], (True,))
        self.assertEqual(build_topology(makefile, False)[:1], (False,))
        ambiguous = makefile + "obj-y += topology.o\n"
        self.assertIsNone(build_topology(ambiguous, True)[0])

    def test_optional_arch_topology_header_does_not_crash(self):
        files = legacy_files()
        result = inspect_snapshot(files, REVISION, "s390", "book", True,
                                  True, True)
        self.assertEqual(result["status"], "normal")
        self.assertIn("absent; optional", result["facts"]["arch_topology_header"])
        self.assertEqual((result["facts"]["native_id"],
                          result["facts"]["native_map"]), (True, True))

    def test_unknown_config_abstains_and_absent_versioned_config_is_inapplicable(self):
        files = legacy_files()
        self.assertEqual(inspect_snapshot(files, REVISION, "s390", "book",
                                          True, True, None)["status"], "insufficient")
        files["arch/s390/Kconfig"] = "config SMP\n\tbool\n"
        out = inspect_snapshot(files, REVISION, "s390", "book",
                               True, True, True)
        self.assertEqual(out["status"], "not_applicable")
        self.assertIn("absent", out["reason"])

    def test_legacy_x86_kconfig_absence_is_not_a_behavior_verdict(self):
        files = legacy_files()
        out = inspect_snapshot(files, REVISION, "x86", "book", True, True, None)
        self.assertEqual(out["status"], "insufficient")
        self.assertIn("source graph", out["reason"])

    def test_missing_provider_with_export_is_hit_only_when_chain_complete(self):
        files = legacy_files()
        path = "arch/s390/include/asm/topology.h"
        files[path] = files[path].replace(
            "#define topology_book_cpumask(cpu) native_mask(cpu)\n", "")
        out = inspect_snapshot(files, REVISION, "s390", "book", True, True, True)
        self.assertEqual(out["status"], "hit")
        files["drivers/base/topology.c"] = files["drivers/base/topology.c"].replace(
            "device_initcall(topology_sysfs_init);", "/* no registration */")
        self.assertEqual(inspect_snapshot(files, REVISION, "s390", "book",
                                          True, True, True)["status"], "insufficient")

    def test_absent_consumer_and_unrecognized_shape(self):
        files = legacy_files()
        out = inspect_snapshot(files, REVISION, "s390", "drawer", True, True, True)
        self.assertEqual(out["status"], "not_applicable")
        files["drivers/base/topology.c"] = files["drivers/base/topology.c"].replace(
            "define_one_ro_named(book_siblings_list, show_book_cpumask_list);",
            "define_one_ro_named(book_siblings_list, unexpected);" )
        self.assertEqual(inspect_snapshot(files, REVISION, "s390", "book",
                                          True, True, True)["status"], "insufficient")


if __name__ == "__main__":
    unittest.main()
