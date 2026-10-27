"""Die-specific archived evidence projection, not a new relation checker.

Path classification alone does not certify native implementation: the caller
must independently review the exact macro body/source identity. No kernel is
run and no legacy expected/pass labels are read by these functions.
"""
from copy import deepcopy
from pathlib import PurePosixPath
import re

ID_MACRO, MASK_MACRO, FLAG = "topology_die_id", "topology_die_cpumask", "TOPOLOGY_DIE_SYSFS"
ATTRS = ("dev_attr_die_id", "bin_attr_die_cpus", "bin_attr_die_cpus_list")
FILES = ("die_id", "die_cpus", "die_cpus_list")


def _text(value): return isinstance(value, str) and bool(value.strip())
def _positive(value): return type(value) is int and value > 0


def _tree(prefix):
    if not _text(prefix) or "\\" in prefix: return None
    path = PurePosixPath(prefix)
    if not path.is_absolute() or ".." in path.parts or str(path) != prefix.rstrip("/") or str(path) == "/": return None
    return str(path)


def _array(text, name, kind, tree):
    if not isinstance(text, str): raise ValueError("array_text_missing:" + name)
    markers = []
    def marker(match):
        path = match[2]
        if not path.startswith(tree + "/") or ".." in PurePosixPath(path).parts: raise ValueError("array_line_marker_outside_tree")
        markers.append(match[0]); return " " * len(match[0])
    visible = re.sub(r'(?m)^# (\d+) "([^"\r\n]+)"(?: \d+)*[ \t]*\r?$', marker, text)
    if any(token in visible for token in ('"', "'", "/*", "//", "#")): raise ValueError("unsupported_array_comment_literal_or_directive:" + name)
    match = re.fullmatch(r"\s*static\s+struct\s+" + kind + r"\s*\*\s*" + name + r"\s*\[\s*\]\s*=\s*\{(.*?)\};\s*", visible, re.S)
    if not match: raise ValueError("array_not_unique_complete_definition:" + name)
    parts = [part.strip() for part in match[1].split(",")]
    if parts and not parts[-1]: parts.pop()
    if not parts or not re.fullmatch(r"\(\(\s*void\s*\*\s*\)\s*0\s*\)", parts[-1]): raise ValueError("array_final_null_missing:" + name)
    entries = []
    for part in parts[:-1]:
        item = re.fullmatch(r"&([A-Za-z_]\w*)" + (r"\.attr" if name == "default_attrs" else ""), part)
        if not item: raise ValueError("unsupported_array_initializer:" + name)
        entries.append(item[1])
    die = [entry for entry in entries if entry in ATTRS]
    if len(die) != len(set(die)): raise ValueError("duplicate_die_array_reference:" + name)
    allowed = {ATTRS[0]} if name == "default_attrs" else set(ATTRS[1:])
    if not set(die) <= allowed: raise ValueError("die_reference_in_wrong_array:" + name)
    return {"text": text, "members": entries, "die_references": die, "line_markers": markers}


def project_static(pp, tree_prefix, source_arch):
    result = {"status": "insufficient", "listed_any": None, "listed_all": None, "count": None,
              "id_native": None, "mask_native": None, "evidence": {}, "unknowns": [],
              "source_evidence_only": True, "actual_registration_proved": False,
              "origin_classification_only": True, "native_interpretation_requires_provider_review": True, "no_physical_truth": True}
    tree = _tree(tree_prefix)
    if tree is None or not _text(source_arch) or not re.fullmatch(r"[A-Za-z0-9_]+", source_arch):
        result["unknowns"].append("unsupported_tree_or_source_arch"); return result
    if not isinstance(pp, dict) or not isinstance(pp.get("macro_definitions"), dict):
        result["unknowns"].append("macro_record_missing"); return result
    definitions, chosen = pp["macro_definitions"], {}
    expected = tree + "/arch/" + source_arch + "/include/asm/topology.h"
    fallback = tree + "/include/linux/topology.h"
    result["evidence"]["macro_sources"] = {name: deepcopy(definitions.get(name)) for name in (ID_MACRO, MASK_MACRO)}
    for name, output in [(ID_MACRO, "id_native"), (MASK_MACRO, "mask_native")]:
        rows = definitions.get(name)
        if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
            result["unknowns"].append("missing_or_ambiguous_macro_definition:" + name); continue
        row = rows[0]
        if (not _positive(row.get("source_line")) or not _positive(row.get("preprocessed_line"))
                or not isinstance(row.get("definition"), str) or not re.fullmatch(r"#define\s+" + name + r"\([^\r\n]*\)\s+[^\r\n]+", row["definition"])):
            result["unknowns"].append("unsupported_macro_record:" + name); continue
        if row.get("file") not in {expected, fallback}:
            result["unknowns"].append("macro_origin_outside_selected_headers:" + name); continue
        result[output] = row["file"] == expected
        chosen[name] = row
    flags = definitions.get(FLAG, [])
    result["evidence"]["sysfs_flag"] = deepcopy(flags)
    if flags:
        valid = (isinstance(flags, list) and len(flags) == 1 and isinstance(flags[0], dict)
                 and flags[0].get("file") == fallback and _positive(flags[0].get("preprocessed_line"))
                 and _positive(flags[0].get("source_line")) and isinstance(flags[0].get("definition"), str)
                 and re.fullmatch(r"#define\s+" + FLAG + r"\s*", flags[0]["definition"]) is not None
                 and result["id_native"] is True and result["mask_native"] is True
                 and all(chosen[name]["preprocessed_line"] < flags[0]["preprocessed_line"] for name in (ID_MACRO, MASK_MACRO)))
        if not valid:
            result["unknowns"].append("opt_in_definition_or_before_fallback_origin_order_not_established")
            result["id_native"] = result["mask_native"] = None
    elif not isinstance(flags, list):
        result["unknowns"].append("malformed_sysfs_flag_record")
        result["id_native"] = result["mask_native"] = None
    try:
        arrays, declared, projected = pp.get("arrays"), pp.get("declarations"), {}
        if not isinstance(arrays, dict) or not isinstance(declared, dict): raise ValueError("array_or_declaration_record_missing")
        for name, kind in [("default_attrs", "attribute"), ("bin_attrs", "bin_attribute")]:
            row = arrays.get(name)
            if not isinstance(row, dict): raise ValueError("array_record_missing:" + name)
            projected[name] = _array(row.get("text"), name, kind, tree)
            if row.get("die_references") != projected[name]["die_references"]: raise ValueError("array_reference_summary_disagrees:" + name)
        present = [item for row in projected.values() for item in row["die_references"]]
        if any(type(declared.get(name)) is not bool or declared[name] != (name in present) for name in ATTRS): raise ValueError("declarations_disagree_with_trio_references")
        result.update(listed_any=bool(present), listed_all=len(present) == 3, count=len(present))
        result["evidence"]["arrays"] = projected
        result["evidence"]["declared_booleans"] = deepcopy(declared)
        if len(present) not in {0, 3}: result["unknowns"].append("partial_attribute_trio_not_complete_publication_evidence")
    except (ValueError, TypeError, KeyError) as exc:
        result["unknowns"].append(str(exc))
        result["listed_any"] = result["listed_all"] = result["count"] = None
        result["evidence"]["unaccepted_arrays"] = deepcopy(pp.get("arrays"))
    result["status"] = "supported" if not result["unknowns"] else "insufficient"
    return result


def _cpu_list(raw):
    if not isinstance(raw, str) or not re.fullmatch(r"\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*", raw.strip()): raise ValueError("invalid_cpu_list")
    values = set()
    for part in raw.strip().split(","):
        bounds = list(map(int, part.split("-"))); low, high = bounds[0], bounds[-1]
        if low > high or high > 4096: raise ValueError("cpu_range_outside_probe_scope")
        values.update(range(low, high + 1))
    return values


def _okay(event):
    return (isinstance(event, dict) and event.get("status") == "ok" and type(event.get("errno")) is int and event["errno"] == 0
            and event.get("truncated") is False and isinstance(event.get("raw"), str))


def _missing(event):
    return (isinstance(event, dict) and event.get("status") == "open_error" and type(event.get("errno")) is int and event["errno"] == 2
            and event.get("truncated") is False and event.get("raw") == "")


def project_runtime(events):
    result = {"status": "insufficient", "id_native": None, "mask_native": None, "foundation": {}, "cpus": [],
              "all_cpus_success": False, "all_cpus_enoent": False, "unknowns": [],
              "no_physical_truth": True, "build_identity_requires_external_binding": True}
    if not isinstance(events, list) or not events or any(not isinstance(event, dict) for event in events):
        result["unknowns"].append("malformed_event_sequence"); return result
    def rows(kind, **keys): return [event for event in events if event.get("event") == kind and all(event.get(k) == v for k, v in keys.items())]
    def one(kind, **keys):
        found = rows(kind, **keys); return found[0] if len(found) == 1 else None
    def read(path): return one("file_read", path=path)
    begin, end, selection, uname = one("probe_begin"), one("probe_end"), one("online_selection"), one("uname")
    foundation = result["foundation"]
    foundation["pid1_probe"] = bool(begin and type(begin.get("pid")) is int and begin["pid"] == 1 and begin.get("schema") == "die_sysfs_runtime_v1" and _positive(begin.get("max_cpus")))
    foundation["complete_event_interval"] = bool(begin and end and events[0] is begin and events[-1] is end and end.get("reached_end") is True
                                                 and end.get("setup_skipped", False) is False and end.get("online_parse_ok") is True and end.get("truncated") is False)
    for operation in ["open_console", "mount_proc", "mount_sysfs"]:
        row = one("setup", operation=operation)
        foundation[operation] = bool(row and type(row.get("return_code")) is int and row["return_code"] == 0)
    foundation["uname_reported"] = bool(uname and type(uname.get("return_code")) is int and uname["return_code"] == 0 and _text(uname.get("release")) and _text(uname.get("machine")))
    if uname: result["reported_identity"] = deepcopy(uname)
    selected = selection.get("selected_cpu_ids") if selection else None
    selection_valid = (selection and selection.get("parse_ok") is True and selection.get("truncated") is False and isinstance(selected, list)
                       and bool(selected) and all(type(cpu) is int and 0 <= cpu <= 4096 for cpu in selected)
                       and selected == sorted(set(selected)) and type(selection.get("online_cpu_count")) is int and selection["online_cpu_count"] == len(selected))
    foundation["selection_and_end"] = bool(selection_valid and begin and end and _positive(begin.get("max_cpus"))
                                           and len(selected) <= begin["max_cpus"] and type(end.get("observed_cpus")) is int and end["observed_cpus"] == len(selected))
    try:
        online = rows("file_read", path="/sys/devices/system/cpu/online")
        parsed = {name: _cpu_list(read("/sys/devices/system/cpu/" + name)["raw"]) if _okay(read("/sys/devices/system/cpu/" + name)) else None for name in ["present", "possible"]}
        online_set = _cpu_list(online[0]["raw"]) if len(online) == 2 and all(_okay(event) for event in online) and online[0]["raw"] == online[1]["raw"] else None
        foundation["online_readback"] = online_set is not None and selection_valid and online_set == set(selected)
        foundation["cpu_set_relationship"] = online_set is not None and parsed["present"] is not None and parsed["possible"] is not None and online_set <= parsed["present"] <= parsed["possible"]
    except (ValueError, TypeError, KeyError):
        foundation["online_readback"] = foundation["cpu_set_relationship"] = False
    command = read("/proc/cmdline")
    cases = [word for word in command["raw"].split() if word.startswith("die_case=")] if _okay(command) else []
    foundation["single_case_marker"] = len(cases) == 1 and len(cases[0]) > len("die_case=")
    if cases: result["reported_case_marker"] = cases[0]
    global_valid = all(foundation.values())
    for cpu in selected if selection_valid else []:
        base = "/sys/devices/system/cpu/cpu" + str(cpu) + "/topology"
        directory = one("directory_stat", path=base)
        controls = {name: read(base + "/" + name) for name in ["physical_package_id", "core_id", "thread_siblings_list"]}
        controls_valid = bool(directory and type(directory.get("cpu")) is int and directory["cpu"] == cpu
                              and type(directory.get("return_code")) is int and directory["return_code"] == 0 and type(directory.get("errno")) is int and directory["errno"] == 0
                              and directory.get("is_directory") is True and all(_okay(event) and type(event.get("cpu")) is int and event["cpu"] == cpu for event in controls.values()))
        if controls_valid:
            try:
                controls_valid = (all(re.fullmatch(r"-?\d+", controls[name]["raw"].strip()) for name in ["physical_package_id", "core_id"])
                                  and cpu in _cpu_list(controls["thread_siblings_list"]["raw"]))
            except (ValueError, KeyError): controls_valid = False
        found = {name: rows("file_read", path=base + "/" + name) for name in FILES}
        files = {name: items[0] if len(items) == 1 else None for name, items in found.items()}
        unique = all(event and type(event.get("cpu")) is int and event["cpu"] == cpu for event in files.values())
        success = bool(unique and all(_okay(event) for event in files.values()))
        absent = bool(unique and all(_missing(event) for event in files.values()))
        valid = global_valid and controls_valid and (success or absent)
        row = {"cpu": cpu, "status": "all_success" if valid and success else "all_enoent" if valid and absent else "insufficient",
               "listed_any": success if valid else None, "listed_all": success if valid else None, "count": 3 if valid and success else 0 if valid else None,
               "paths": [base + "/" + name for name in FILES], "files": deepcopy(files), "controls": deepcopy(controls),
               "controls_valid": bool(controls_valid), "observed_file_events": deepcopy(found)}
        if not valid: result["unknowns"].append("incomplete_controls_or_attribute_trio:cpu" + str(cpu))
        result["cpus"].append(row)
    result["unknowns"].extend("foundation_failed:" + key for key, value in foundation.items() if not value)
    result["all_cpus_success"] = bool(result["cpus"]) and all(row["status"] == "all_success" for row in result["cpus"])
    result["all_cpus_enoent"] = bool(result["cpus"]) and all(row["status"] == "all_enoent" for row in result["cpus"])
    result["status"] = "supported" if global_valid and result["cpus"] and not result["unknowns"] else "insufficient"
    return result
