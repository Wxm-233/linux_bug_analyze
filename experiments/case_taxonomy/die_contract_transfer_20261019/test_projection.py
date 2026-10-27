"""Finite die evidence projection boundaries; no new Linux execution."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("die_projection", Path(__file__).with_name("projection.py"))
projection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(projection)
TREE = "/archived/tree"


def pp(native=True, flag=False):
    arch = TREE + "/arch/x86/include/asm/topology.h"
    common = TREE + "/include/linux/topology.h"
    definitions = {
        "topology_die_id": [{"file": arch if native else common, "source_line": 111, "preprocessed_line": 100,
                             "definition": "#define topology_die_id(cpu) " + ("(cpu_data(cpu).cpu_die_id)" if native else "((void)(cpu), -1)")}],
        "topology_die_cpumask": [{"file": arch if native else common, "source_line": 118, "preprocessed_line": 110,
                                  "definition": "#define topology_die_cpumask(cpu) " + ("(per_cpu(cpu_die_map, cpu))" if native else "cpumask_of(cpu)")}],
    }
    if flag: definitions["TOPOLOGY_DIE_SYSFS"] = [{"file": common, "source_line": 184, "preprocessed_line": 150, "definition": "#define TOPOLOGY_DIE_SYSFS "}]
    return {"macro_definitions": definitions, "arrays": {
        "default_attrs": {"text": "static struct attribute *default_attrs[] = {\n &dev_attr_physical_package_id.attr,\n &dev_attr_die_id.attr,\n ((void *)0)\n};", "die_references": ["dev_attr_die_id"]},
        "bin_attrs": {"text": "static struct bin_attribute *bin_attrs[] = {\n &bin_attr_core_cpus,\n &bin_attr_die_cpus,\n &bin_attr_die_cpus_list,\n ((void *)0)\n};", "die_references": ["bin_attr_die_cpus", "bin_attr_die_cpus_list"]}},
        "declarations": {name: True for name in projection.ATTRS}}


def read(path, raw="0\n", cpu=None, missing=False):
    event = {"event": "file_read", "path": path, "status": "open_error" if missing else "ok", "errno": 2 if missing else 0,
             "raw": "" if missing else raw, "truncated": False, "raw_byte_length": 0 if missing else len(raw), "read_limit_bytes": 16384}
    if cpu is not None: event["cpu"] = cpu
    return event


def events(missing=False):
    result = [{"event": "probe_begin", "schema": "die_sysfs_runtime_v1", "pid": 1, "max_cpus": 4},
              *[{"event": "setup", "operation": operation, "return_code": 0} for operation in ["open_console", "mount_proc", "mount_sysfs"]],
              {"event": "uname", "return_code": 0, "release": "archived-kernel", "machine": "synthetic"},
              read("/proc/cmdline", "die_case=opaque\n"),
              read("/sys/devices/system/cpu/online"), read("/sys/devices/system/cpu/present"), read("/sys/devices/system/cpu/possible", "0-3\n"),
              {"event": "online_selection", "parse_ok": True, "truncated": False, "selected_cpu_ids": [0], "online_cpu_count": 1}]
    base = "/sys/devices/system/cpu/cpu0/topology"
    result += [{"event": "directory_stat", "path": base, "cpu": 0, "return_code": 0, "errno": 0, "is_directory": True}]
    result += [read(base + "/" + name, cpu=0) for name in ["physical_package_id", "core_id", "thread_siblings_list"]]
    result += [read(base + "/" + name, cpu=0, missing=missing) for name in projection.FILES]
    result += [read("/sys/devices/system/cpu/online"), {"event": "probe_end", "reached_end": True, "online_parse_ok": True, "observed_cpus": 1, "truncated": False}]
    return result


class DieProjectionTests(unittest.TestCase):
    def test_native_origin_and_final_fallback_presence_are_distinct(self):
        native = projection.project_static(pp(True, True), TREE, "x86")
        fallback = projection.project_static(pp(False), TREE, "x86")
        self.assertEqual(native["status"], "supported", native["unknowns"])
        self.assertEqual((native["id_native"], native["mask_native"], native["count"]), (True, True, 3))
        self.assertEqual((fallback["id_native"], fallback["mask_native"], fallback["count"]), (False, False, 3))
        self.assertIs(fallback["actual_registration_proved"], False)
        self.assertTrue(native["origin_classification_only"])
        self.assertTrue(native["native_interpretation_requires_provider_review"])

    def test_missing_multiple_and_foreign_macro_sources_remain_unknown(self):
        for change in ["missing", "multiple", "foreign", "traversal"]:
            with self.subTest(change=change):
                material = pp()
                rows = material["macro_definitions"]["topology_die_id"]
                if change == "missing": material["macro_definitions"].pop("topology_die_id")
                if change == "multiple": rows.append(copy.deepcopy(rows[0]))
                if change == "foreign": rows[0]["file"] = "/different/tree/arch/x86/include/asm/topology.h"
                if change == "traversal": rows[0]["file"] = TREE + "/arch/other/../x86/include/asm/topology.h"
                result = projection.project_static(material, TREE, "x86")
                self.assertEqual(result["status"], "insufficient")
                self.assertIsNone(result["id_native"])
                self.assertEqual(result["count"], 3)

    def test_opt_in_requires_before_flag_sources_absence_does_not_negate_native(self):
        self.assertIs(projection.project_static(pp(True, False), TREE, "x86")["id_native"], True)
        material = pp(True, True)
        material["macro_definitions"]["topology_die_cpumask"][0]["preprocessed_line"] = 160
        result = projection.project_static(material, TREE, "x86")
        self.assertEqual(result["status"], "insufficient")
        self.assertIsNone(result["mask_native"])

    def test_partial_trio_is_not_whole_publication_and_summaries_must_match(self):
        material = pp()
        material["arrays"]["bin_attrs"] = {"text": "static struct bin_attribute *bin_attrs[] = { ((void *)0) };", "die_references": []}
        for name in projection.ATTRS[1:]: material["declarations"][name] = False
        result = projection.project_static(material, TREE, "x86")
        self.assertEqual((result["listed_any"], result["listed_all"], result["count"]), (True, False, 1))
        self.assertEqual(result["status"], "insufficient")
        for change in ["references", "declarations"]:
            with self.subTest(change=change):
                material = pp()
                if change == "references": material["arrays"]["default_attrs"]["die_references"] = []
                else: material["declarations"]["dev_attr_die_id"] = False
                result = projection.project_static(material, TREE, "x86")
                self.assertEqual(result["status"], "insufficient")
                self.assertIsNone(result["listed_all"])

    def test_complete_arrays_reject_unknown_literal_comment_and_wrong_type(self):
        for change in ["comment", "literal", "wrong_array", "no_null", "duplicate"]:
            with self.subTest(change=change):
                material = pp()
                text = material["arrays"]["default_attrs"]["text"]
                if change == "comment": text = text.replace("&dev_attr_die_id.attr", "/* maybe */ &dev_attr_die_id.attr")
                if change == "literal": text = text.replace("&dev_attr_die_id.attr", '"&dev_attr_die_id.attr"')
                if change == "wrong_array": text = text.replace("dev_attr_die_id", "bin_attr_die_cpus")
                if change == "no_null": text = text.replace("((void *)0)", "")
                if change == "duplicate": text = text.replace("&dev_attr_die_id.attr,", "&dev_attr_die_id.attr, &dev_attr_die_id.attr,")
                material["arrays"]["default_attrs"]["text"] = text
                self.assertIsNone(projection.project_static(material, TREE, "x86")["count"])
        material = pp()
        material["arrays"]["bin_attrs"]["text"] = material["arrays"]["bin_attrs"]["text"].replace(" ((void *)0)", '# 124 "' + TREE + '/drivers/base/topology.c"\n ((void *)0)')
        self.assertEqual(projection.project_static(material, TREE, "x86")["status"], "supported")

    def test_runtime_complete_success_and_enoent_are_separate_observations(self):
        for missing, expected, count in [(False, "all_success", 3), (True, "all_enoent", 0)]:
            with self.subTest(missing=missing):
                result = projection.project_runtime(events(missing))
                self.assertEqual(result["status"], "supported", result["unknowns"])
                self.assertEqual((result["cpus"][0]["status"], result["cpus"][0]["count"]), (expected, count))
                self.assertIsNone(result["id_native"])

    def test_runtime_partial_wrong_error_truncation_and_duplicates_are_insufficient(self):
        for change in ["partial", "permission", "wrong_errno_status", "truncated", "duplicate", "wrong_cpu"]:
            with self.subTest(change=change):
                material = events(True)
                target = next(e for e in material if e.get("path", "").endswith("/die_id"))
                if change == "partial": target.update(status="ok", errno=0, raw="0\n")
                if change == "permission": target["errno"] = 13
                if change == "wrong_errno_status": target["status"] = "read_error"
                if change == "truncated": target["truncated"] = True
                if change == "duplicate": material.insert(-1, copy.deepcopy(target))
                if change == "wrong_cpu": target["cpu"] = 1
                result = projection.project_runtime(material)
                self.assertEqual(result["status"], "insufficient")
                self.assertEqual(result["cpus"][0]["status"], "insufficient")
                self.assertIsNone(result["cpus"][0]["listed_all"])

    def test_runtime_missing_controls_probe_mount_or_online_cannot_certify_absence(self):
        for change in ["control", "pid", "end", "mount", "online", "duplicate_control"]:
            with self.subTest(change=change):
                material = events(True)
                if change == "control": material = [e for e in material if not e.get("path", "").endswith("/core_id")]
                if change == "pid": material[0]["pid"] = 2
                if change == "end": material[-1]["reached_end"] = False
                if change == "mount": next(e for e in material if e.get("operation") == "mount_sysfs")["return_code"] = -1
                if change == "online": next(e for e in material if e.get("event") == "online_selection")["selected_cpu_ids"] = [1]
                if change == "duplicate_control": material.insert(-1, copy.deepcopy(next(e for e in material if e.get("path", "").endswith("/core_id"))))
                result = projection.project_runtime(material)
                self.assertEqual(result["status"], "insufficient")
                self.assertFalse(result["all_cpus_enoent"])

    def test_runtime_never_infers_static_native_or_consumes_expected_labels(self):
        static_input = pp()
        static_before = copy.deepcopy(static_input)
        static = projection.project_static(static_input, TREE, "x86")
        material = events(True)
        for event in material: event.update(matches_contract=True, expected_native_sources=True, id_native=True)
        result = projection.project_runtime(material)
        self.assertEqual(result["status"], "supported", result["unknowns"])
        self.assertIsNone(result["id_native"])
        self.assertIsNone(result["mask_native"])
        self.assertEqual(static_input, static_before)
        self.assertIs(static["id_native"], True)

    def test_malformed_probe_limits_and_bool_in_integer_fields_fail_closed(self):
        for change in ["null_limit", "string_limit", "bool_limit", "bool_pid", "bool_count", "bool_cpu", "bool_uname_code", "bool_online_count", "float_online_count"]:
            with self.subTest(change=change):
                material = events(True)
                if change == "null_limit": material[0]["max_cpus"] = None
                if change == "string_limit": material[0]["max_cpus"] = "4"
                if change == "bool_limit": material[0]["max_cpus"] = True
                if change == "bool_pid": material[0]["pid"] = True
                if change == "bool_count": material[-1]["observed_cpus"] = True
                if change == "bool_cpu": next(e for e in material if e.get("path", "").endswith("/die_id"))["cpu"] = False
                if change == "bool_uname_code": next(e for e in material if e.get("event") == "uname")["return_code"] = False
                if change == "bool_online_count": next(e for e in material if e.get("event") == "online_selection")["online_cpu_count"] = True
                if change == "float_online_count": next(e for e in material if e.get("event") == "online_selection")["online_cpu_count"] = 1.0
                result = projection.project_runtime(material)
                self.assertEqual(result["status"], "insufficient")
                self.assertFalse(result["all_cpus_enoent"])


if __name__ == "__main__": unittest.main()
