"""Generate conditional reduced-TU field checks from verified source evidence.

The producer is taken from the source assignment. An independent schema decoder
and expected-byte calculation check its copied bytes. This never establishes an
external protocol or hardware defect, and never generates a kernel patch.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

import structured_hci_single_revision as structured

VERSION = "contract-assertion-generator-v1.0"
MAX_FIELDS = 32


def _refuse(reason: str, site=None) -> dict:
    return {"version": VERSION, "status": "refused", "programs": [],
            "rejections": [{"site": site, "reason": reason}],
            "scope": "conditional reduced translation-unit projection, not a hardware/configuration/protocol verdict"}


def _verify_report(report: dict, files: dict[str, str]) -> dict:
    if not isinstance(report, dict) or not isinstance(files, dict):
        raise ValueError("report and files must be mappings")
    if any(not isinstance(path, str) or not isinstance(value, str) for path, value in files.items()):
        raise ValueError("files must map paths to source strings")
    source_path, revision = report.get("source_file"), report.get("revision")
    if not isinstance(source_path, str) or not isinstance(revision, str):
        raise ValueError("report source/revision missing")
    normalized = copy.deepcopy(report)
    for item in normalized.get("files_read", []):
        if "git_blob" in item:
            if item.get("path") not in files:
                raise ValueError("blob path absent from supplied files")
            contents = files[item["path"]].encode("utf-8")
            blob = hashlib.sha1(b"blob " + str(len(contents)).encode("ascii") + b"\0" + contents).hexdigest()
            if item.pop("git_blob") != blob:
                raise ValueError("Git blob does not match supplied source bytes")
    rebuilt = structured.analyze_files(source_path, files, revision)
    if normalized != rebuilt:
        raise ValueError("report does not reproduce from supplied source/header evidence")
    return rebuilt


def _payload(struct_name: str, files: dict[str, str]) -> dict:
    # A copied declaration cannot preserve surrounding packing state. Refuse
    # pragma contexts rather than letting compiler offsets certify a different
    # layout in the projected translation unit.
    for source in files.values():
        clean = structured.mask_comments_and_literals(source)
        if re.search(r"^\s*#\s*pragma\b|\b(?:_Pragma|__pragma)\s*\(", clean, re.M):
            raise ValueError("pragma/packing context in bounded files is unsupported by declaration projection")
    candidates = []
    for path, source in files.items():
        clean = structured.mask_comments_and_literals(source)
        for found in re.finditer(rf"\bstruct\s+{re.escape(struct_name)}\s*\{{", clean):
            opening = found.end() - 1
            closing = structured.closing_delimiter(clean, opening, "{", "}")
            if closing is None:
                raise ValueError("unterminated payload structure")
            suffix = re.match(r"\s*(?:(__packed)\s*)?;", clean[closing + 1:])
            if not suffix:
                raise ValueError("payload layout suffix is outside plain/__packed grammar")
            if suffix.group(1) and "__packed" in structured.scalar.macro_names(files):
                raise ValueError("__packed is defined in bounded files; actual layout semantics not proven")
            end = closing + 1 + suffix.end()
            body = clean[opening + 1:closing]
            field_pattern = re.compile(rf"\s*__(le|be)(16|32|64)\s+({structured.IDENT})\s*;")
            offset, fields = 0, []
            while offset < len(body) and body[offset:].strip():
                field = field_pattern.match(body, offset)
                if not field:
                    raise ValueError("payload is not completely composed of direct endian fixed-width scalar fields")
                fields.append({"name": field.group(3), "endian": field.group(1), "bits": int(field.group(2)),
                               "type": f"__{field.group(1)}{field.group(2)}"})
                offset = field.end()
            if not 1 <= len(fields) <= MAX_FIELDS or len({item["name"] for item in fields}) != len(fields):
                raise ValueError("empty, excessive or duplicate payload fields")
            if structured.scalar.conditional_at(source, found.start()) or re.search(r"^\s*#", body, re.M):
                raise ValueError("conditional/unknown payload structure layout")
            candidates.append({"text": source[found.start():end], "fields": fields,
                               "packed": bool(suffix.group(1)),
                               "evidence": structured.scalar.evidence(path, source, found.start(), end)})
    if len(candidates) != 1:
        raise ValueError("payload structure absent or ambiguous")
    return candidates[0]


def build_plan(report: dict, files: dict[str, str]) -> dict:
    """Revalidate evidence and return zero or more complete payload programs.

    programs contain validation inputs for emit_c's independent revalidation.
    Callers may persist a compact manifest separately; those inputs are never
    emitted into C and must not be treated as hidden authoritative provenance.
    """
    try:
        checked = _verify_report(report, files)
    except (ValueError, TypeError, KeyError, FileNotFoundError) as error:
        return _refuse(str(error))
    groups: dict[str, list[dict]] = {}
    for finding in checked["findings"]:
        key = json.dumps({key: finding[key] for key in ("function", "variable", "struct", "call")}, sort_keys=True)
        groups.setdefault(key, []).append(finding)
    programs, rejections = [], []
    for key, findings in groups.items():
        first = findings[0]
        site = {"function": first["function"], "variable": first["variable"], "struct": first["struct"], "call": first["call"]}
        try:
            payload = _payload(first["struct"], files)
            expected_names = {item["name"] for item in payload["fields"]}
            if len(findings) != len(expected_names) or {item["field"] for item in findings} != expected_names:
                raise ValueError("payload field evidence incomplete/duplicated; no partial-payload test generated")
            if any(item["status"] not in {"candidate", "matched_conversion"} or not item["source_member"] for item in findings):
                raise ValueError("all payload fields need proven bounded producer/source/copy evidence")
            by_name = {item["field"]: item for item in findings}
            fields, source_members = [], set()
            for schema in payload["fields"]:
                item = by_name[schema["name"]]
                member = item["source_member"]
                if item["target_declaration"]["type"] != schema["type"] or member["declaration"]["type"] not in {f"u{schema['bits']}", f"__u{schema['bits']}"}:
                    raise ValueError("schema/source declaration width or representation disagreement")
                pair = (member["pointer"], member["field"])
                if pair in source_members:
                    raise ValueError("repeated source-member mapping unsupported for independent field probes")
                source_members.add(pair)
                original = item["assignment"]["text"]
                source_expression = rf"{re.escape(member['pointer'])}\s*->\s*{re.escape(member['field'])}"
                expression = source_expression if item["status"] == "candidate" else rf"cpu_to_{schema['endian']}{schema['bits']}\s*\(\s*{source_expression}\s*\)"
                if not re.fullmatch(rf"{re.escape(first['variable'])}\s*\.\s*{re.escape(schema['name'])}\s*=\s*{expression}\s*;", original):
                    raise ValueError("original assignment is outside supported verified grammar")
                fields.append(dict(schema, source_struct=member["struct"], source_pointer=member["pointer"],
                    source_field=member["field"], source_type=member["declaration"]["type"],
                    source_declaration=member["declaration"]["evidence"], original_assignment=original,
                    producer_status=item["status"], assignment_evidence=item["assignment"]))
            sources = {(item["source_pointer"], item["source_struct"]) for item in fields}
            if len(sources) > 8 or len({pointer for pointer, _ in sources}) != len(sources):
                raise ValueError("too many or conflicting source pointer bindings")
            if first["struct"] in {struct_name for _, struct_name in sources}:
                raise ValueError("projected source tag conflicts with complete payload tag")
            projected_types = {}
            for field in fields:
                source_key = (field["source_struct"], field["source_field"])
                if source_key in projected_types and projected_types[source_key] != field["source_type"]:
                    raise ValueError("conflicting projected source field declarations")
                projected_types[source_key] = field["source_type"]
            identifier_set = set(re.findall(structured.IDENT, "\n".join(files.values())))
            prefix = "ca_"
            while any(name.startswith(prefix) for name in identifier_set):
                prefix += "x_"
            program_id = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
            program = {"version": VERSION, "id": program_id, "source_revision": checked["revision"],
                "source_file": checked["source_file"], "function": first["function"], "variable": first["variable"],
                "call_evidence": first["call"], "payload_struct": first["struct"], "payload_declaration": payload,
                "fields": fields, "generated_identifier_prefix": prefix,
                "compiler_binding_contract": {"actual_function": prefix + "produce_actual",
                    "target_object": first["variable"], "target_struct": first["struct"],
                    "target_fields": {field["name"]: field["type"] for field in fields},
                    "source_pointers": [{"pointer": pointer, "struct": struct_name,
                        "fields": {field["source_field"]: field["source_type"] for field in fields
                                   if field["source_pointer"] == pointer}} for pointer, struct_name in sorted(sources)],
                    "scope": "compiler binding in generated reduced projection only, never original full kernel translation unit"},
                "variants": ["actual", "reference"] + ["partial_" + item["name"] for item in fields],
                "test_values": {str(bits): [int(a, 16), int(b, 16), 0] for bits, a, b in
                    [(16, "1234", "ab37"), (32, "12345678", "c4b39a17"), (64, "0123456789abcdef", "d6a57c3f1298b40e")]},
                "oracle": "decode_schema(original_producer(value)) == value AND copied field bytes equal independent schema bytes",
                "assumptions": ["source field test values are injected as host numeric inputs; actual source initialization/value provenance remains unproven",
                    "same-version payload endian annotations are a conditional local schema, not proof of external controller/opcode authority",
                    "source structures are projections of referenced declared fields; their original layout and source pointer path are not executed",
                    "complete payload declaration is copied from source with plain or __packed layout; GCC offsetof/sizeof determine projected payload layout",
                    "projected source objects and payload storage are zero-initialized synthetically; every declared payload field is then overwritten by its verified assignment, and padding bytes are not a correctness oracle",
                    "__le/__be typedef stubs preserve width and erase sparse bitwise qualifiers; conversion stubs implement normal endian operations for the actual compiler target",
                    "payload command transport is reduced to memcpy based on the separately proven same-revision copy chain; no complete kernel translation unit/configuration/hardware execution",
                    "reference and per-field incomplete repair variants are synthetic controls, not claimed upstream edits"],
                "validated_inputs": {"report": copy.deepcopy(report), "files": copy.deepcopy(files)}}
            programs.append(program)
        except (ValueError, KeyError, TypeError) as error:
            rejections.append({"site": site, "reason": str(error)})
    if not programs and not rejections:
        rejections.append({"site": None, "reason": "no supported structure payload evidence; zero sites is out of scope"})
    return {"version": VERSION, "status": "generated" if programs else "refused", "programs": programs,
            "rejections": rejections, "scope": "conditional reduced translation-unit projection, not a hardware/configuration/protocol verdict"}


def emit_c(program: dict) -> str:
    """Emit only a program that exactly rebuilds from its validated inputs."""
    try:
        inputs = program["validated_inputs"]
        rebuilt = build_plan(inputs["report"], inputs["files"])
        matches = [item for item in rebuilt["programs"] if item["id"] == program["id"]]
        if len(matches) != 1 or matches[0] != program:
            raise ValueError("program was modified or fails source evidence revalidation")
    except (KeyError, TypeError) as error:
        raise ValueError("missing validated program inputs") from error
    fields, prefix = program["fields"], program["generated_identifier_prefix"]
    tag, variable = program["payload_struct"], program["variable"]
    lines = ["/* Conditional source projection; see plan assumptions. */", "#include <stdint.h>", "#include <stddef.h>",
        "#include <stdio.h>", "#include <inttypes.h>", "#include <string.h>", "#define __packed __attribute__((packed))"]
    for bits in (16, 32, 64):
        lines.append(f"typedef uint{bits}_t u{bits}, __u{bits}, __le{bits}, __be{bits};")
        for endian in ("le", "be"):
            correct = "__ORDER_LITTLE_ENDIAN__" if endian == "le" else "__ORDER_BIG_ENDIAN__"
            lines += [f"static inline uint{bits}_t cpu_to_{endian}{bits}(uint{bits}_t x) {{",
                f"#if __BYTE_ORDER__ == {correct}", "return x;", "#else", f"return __builtin_bswap{bits}(x);", "#endif", "}"]
    lines += ["#if __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__ && __BYTE_ORDER__ != __ORDER_BIG_ENDIAN__",
              '#error "unsupported compiler target byte order"', "#endif", program["payload_declaration"]["text"]]
    source_structs: dict[str, dict[str, str]] = {}
    for field in fields:
        existing = source_structs.setdefault(field["source_struct"], {})
        existing[field["source_field"]] = field["source_type"]
    for struct_name, members in source_structs.items():
        lines.append(f"struct {struct_name} {{ " + " ".join(f"{kind} {name};" for name, kind in members.items()) + " };")
    for field in fields:
        lines += [f'_Static_assert(sizeof(((struct {tag} *)0)->{field["name"]}) == {field["bits"] // 8}, "payload field width");',
                  f'_Static_assert(sizeof(((struct {field["source_struct"]} *)0)->{field["source_field"]}) == {field["bits"] // 8}, "source field width");']
    sources = sorted({(field["source_pointer"], field["source_struct"]) for field in fields})
    signature = ", ".join(f"struct {struct_name} *{pointer}" for pointer, struct_name in sources)
    source_args = ", ".join(pointer for pointer, _ in sources)
    lines += [f"static struct {tag} {prefix}produce_actual({signature}) {{", f"struct {tag} {variable};",
              f"memset(&{variable}, 0, sizeof({variable}));"]
    lines += [field["original_assignment"] for field in fields]
    lines += [f"return {variable};", "}",
              f"static struct {tag} {prefix}produce(int {prefix}variant, {signature}) {{", f"struct {tag} {variable};",
              f"if ({prefix}variant == 0) return {prefix}produce_actual({source_args});",
              f"memset(&{variable}, 0, sizeof({variable}));", f"switch ({prefix}variant) {{", "case 1:"]
    for field in fields:
        lines.append(f"{variable}.{field['name']} = cpu_to_{field['endian']}{field['bits']}({field['source_pointer']}->{field['source_field']});")
    lines += ["break;"]
    for index, omitted in enumerate(fields):
        lines.append(f"case {index + 2}:")
        for field in fields:
            value = f"{field['source_pointer']}->{field['source_field']}"
            if field is not omitted:
                value = f"cpu_to_{field['endian']}{field['bits']}({value})"
            lines.append(f"{variable}.{field['name']} = {value};")
        lines.append("break;")
    lines += ["}", f"return {variable};", "}",
        f"static uint64_t {prefix}decode(const unsigned char *p, size_t n, int big) {{",
        "uint64_t x = 0; for (size_t j = 0; j < n; ++j) x |= ((uint64_t)p[j]) << (8 * (big ? n - 1 - j : j)); return x;", "}",
        f"static void {prefix}hex(const unsigned char *p, size_t n) {{ for (size_t j = 0; j < n; ++j) printf(\"%02x\", (unsigned)p[j]); }}",
        "int main(void) {", f"const char *{prefix}endian = __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__ ? \"big\" : \"little\";",
        f'printf("{{\\"kind\\":\\"layout\\",\\"program\\":\\"{program["id"]}\\",\\"host_endian\\":\\"%s\\",\\"size\\":%zu}}\\n", {prefix}endian, sizeof(struct {tag}));',
        f"const char *{prefix}variants[] = {{ " + ", ".join('"' + name + '"' for name in program["variants"]) + " };",
        f"for (int {prefix}active = 0; {prefix}active < {len(fields)}; ++{prefix}active) {{",
        f"for (int {prefix}sample = 0; {prefix}sample < 3; ++{prefix}sample) {{", f"uint64_t {prefix}value = 0;"]
    for index, field in enumerate(fields):
        values = program["test_values"][str(field["bits"])]
        lines.append(f"if ({prefix}active == {index}) {{ const uint64_t {prefix}samples[] = {{" + ",".join(f"UINT64_C({value})" for value in values) + f"}}; {prefix}value = {prefix}samples[{prefix}sample]; }}")
    for index, (pointer, struct_name) in enumerate(sources):
        lines.append(f"struct {struct_name} {prefix}source_{index} = {{0}}; struct {struct_name} *{pointer} = &{prefix}source_{index};")
    for index, field in enumerate(fields):
        lines.append(f"if ({prefix}active == {index}) {field['source_pointer']}->{field['source_field']} = ({field['source_type']}){prefix}value;")
    lines += [f"for (int {prefix}variant = 0; {prefix}variant < {len(fields) + 2}; ++{prefix}variant) {{",
        f"struct {tag} {prefix}output = {prefix}produce({prefix}variant, {source_args});",
        f"unsigned char {prefix}bytes[sizeof({prefix}output)]; memcpy({prefix}bytes, &{prefix}output, sizeof({prefix}output));"]
    for field in fields:
        name, bits, big = field["name"], field["bits"], 1 if field["endian"] == "be" else 0
        lines += ["{", f"const size_t {prefix}offset = offsetof(struct {tag}, {name}), {prefix}width = {bits // 8};",
            f"const uint64_t {prefix}expected_value = (uint64_t){field['source_pointer']}->{field['source_field']};",
            f"uint64_t {prefix}decoded = {prefix}decode({prefix}bytes + {prefix}offset, {prefix}width, {big});",
            f"unsigned char {prefix}expected[8] = {{0}};",
            f"for (size_t {prefix}j = 0; {prefix}j < {prefix}width; ++{prefix}j) {prefix}expected[{prefix}j] = (unsigned char)({prefix}expected_value >> (8 * ({big} ? {prefix}width - 1 - {prefix}j : {prefix}j)));",
            f"int {prefix}ok = {prefix}decoded == {prefix}expected_value && !memcmp({prefix}bytes + {prefix}offset, {prefix}expected, {prefix}width);",
            f'printf("{{\\"kind\\":\\"field_check\\",\\"program\\":\\"{program["id"]}\\",\\"host_endian\\":\\"%s\\",\\"variant\\":\\"%s\\",\\"case_field\\":\\"%s\\",\\"case_index\\":%d,\\"value\\":%" PRIu64 ",\\"field\\":\\"{name}\\",\\"offset\\":%zu,\\"width\\":%zu,\\"expected_value\\":%" PRIu64 ",\\"decoded\\":%" PRIu64 ",\\"actual_bytes\\":\\"", {prefix}endian, {prefix}variants[{prefix}variant],',
            "(const char *[]) { " + ", ".join('"' + item["name"] + '"' for item in fields) + f" }}[{prefix}active], {prefix}sample, {prefix}value, {prefix}offset, {prefix}width, {prefix}expected_value, {prefix}decoded);",
            f"{prefix}hex({prefix}bytes + {prefix}offset, {prefix}width); printf(\"\\\",\\\"expected_bytes\\\":\\\"\"); {prefix}hex({prefix}expected, {prefix}width);",
            f'printf("\\",\\"pass\\":%s}}\\n", {prefix}ok ? "true" : "false");', "}"]
    lines += ["}", "}", "}", "return 0;", "}"]
    return "\n".join(lines) + "\n"
