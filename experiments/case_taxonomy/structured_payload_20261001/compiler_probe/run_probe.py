"""Bounded, source-linked C projection of already reviewed representation cases.

This does not compile the kernel translation unit or discover new samples.
GCC validates widths and block bindings, but its plain typedefs do not retain
Sparse's endian distinction. All target execution is user-mode arithmetic.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


HCI_PARENT = "cef456cd354ef485f12d57000c455e83e416a2b6"
HCI_FIX = "727ea61a5028f8ac96f75ab34cb1b56e63fd9227"
CD_PARENT = "25c150ac103a4ebeed0319994c742a90634ddf18"
CD_FIX = "0ab905c3be8c2be368821dd2bd1f8d126064d993"
DW_PARENT = "40dfdd8d1449382cae3db2cefb1f5521ce19259b"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def get_source(linux_dir: Path, revision: str, path: str) -> dict:
    raw = subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=linux_dir)
    blob = subprocess.check_output(["git", "rev-parse", f"{revision}:{path}"], cwd=linux_dir, text=True).strip()
    return {"revision": revision, "path": path, "blob": blob,
            "sha256": sha256(raw), "text": raw.decode()}


def excerpt(record: dict, label: str, text: str) -> dict:
    source = record["text"]
    if source.count(text) != 1:
        raise ValueError(f"nonunique source excerpt {record['path']}:{label}")
    start = source.index(text)
    line = source[:start].count("\n") + 1
    return {"label": label, "revision": record["revision"], "path": record["path"],
            "blob": record["blob"], "source_sha256": record["sha256"],
            "start_line": line, "end_line": line + text.count("\n"), "text": text}


def find_struct(source: str, name: str) -> str:
    match = re.search(r"struct " + re.escape(name) + r"\s*\{.*?\n\}(?:\s+__packed)?;", source, re.S)
    if not match:
        raise ValueError(f"structure absent: {name}")
    return match.group()


def find_function(source: str, name: str) -> str:
    match = re.search(r"(?:static\s+)?(?:inline\s+)?[^\n]+\b" + re.escape(name) + r"\([^;]*?\n\{", source)
    if not match:
        raise ValueError(f"function absent: {name}")
    brace = source.index("{", match.start())
    depth = 0
    for end in range(brace, len(source)):
        if source[end] == "{":
            depth += 1
        elif source[end] == "}":
            depth -= 1
            if depth == 0:
                return source[match.start():end + 1]
    raise ValueError("unbalanced source projection")


def field_line(source: str, name: str) -> str:
    found = re.findall(r"^[ \t]*__u16[ \t]+" + name + r";[^\n]*", source, re.M)
    if len(found) != 1:
        raise ValueError(f"nonunique host field {name}")
    return found[0]


def assignment(source: str, name: str) -> str:
    found = re.findall(r"^[ \t]*cp\." + name + r" = [^;]+;", source, re.M)
    if len(found) != 1:
        raise ValueError(f"nonunique cp assignment {name}")
    return found[0].strip()


def make_sources(linux_dir: Path, out: Path) -> dict:
    specs = [
        ("hci_old", HCI_PARENT, "net/bluetooth/hci_core.c"),
        ("hci_fix", HCI_FIX, "net/bluetooth/hci_core.c"),
        ("hci_schema", HCI_PARENT, "include/net/bluetooth/hci.h"),
        ("hci_host", HCI_PARENT, "include/net/bluetooth/hci_core.h"),
        ("hci_copy", HCI_PARENT, "net/bluetooth/hci_request.c"),
        ("skb_copy", HCI_PARENT, "include/linux/skbuff.h"),
        ("cd_old", CD_PARENT, "net/bluetooth/coredump.c"),
        ("cd_fix", CD_FIX, "net/bluetooth/coredump.c"),
        ("dw_scope", DW_PARENT, "drivers/mmc/host/dw_mmc.c"),
    ]
    records = {name: get_source(linux_dir, revision, path) for name, revision, path in specs}
    evidence = []
    schema = find_struct(records["hci_schema"]["text"], "hci_cp_le_write_def_data_len")
    evidence.append(excerpt(records["hci_schema"], "payload_schema", schema))
    host_fields = [field_line(records["hci_host"]["text"], n) for n in ("le_max_tx_len", "le_max_tx_time")]
    for field in host_fields:
        evidence.append(excerpt(records["hci_host"], "host_source_field", field))
    assignments = {}
    for key in ("hci_old", "hci_fix"):
        function = find_function(records[key]["text"], "hci_init4_req")
        assignments[key] = [assignment(function, n) for n in ("tx_len", "tx_time")]
        for line in assignments[key]:
            original = next(s for s in function.splitlines() if s.strip() == line)
            evidence.append(excerpt(records[key], key + "_assignment", original))
        call = re.search(r"hci_req_add\(req, HCI_OP_LE_WRITE_DEF_DATA_LEN,\s*sizeof\(cp\), &cp\);", function)
        if not call:
            raise ValueError("HCI sizeof(cp), &cp payload call absent")
        evidence.append(excerpt(records[key], key + "_payload_call", call.group()))
    for key, function in [("hci_copy", "hci_req_add"), ("hci_copy", "hci_prepare_cmd"),
                          ("skb_copy", "skb_put_data"), ("cd_old", "hci_devcd_init"),
                          ("cd_old", "hci_devcd_handle_pkt_init"), ("cd_old", "hci_devcd_rx"),
                          ("cd_fix", "hci_devcd_init"), ("cd_fix", "hci_devcd_handle_pkt_init")]:
        evidence.append(excerpt(records[key], key + "_" + function,
                                find_function(records[key]["text"], function)))
    dw = records["dw_scope"]
    dw_fields = {}
    for name in ("idmac_desc_64addr", "idmac_desc"):
        whole = find_struct(dw["text"], name)
        evidence.append(excerpt(dw, name + "_original", whole))
        # Only member declarations projected; preprocessor macros in this
        # historical structure are deliberately excluded from the toy TU.
        fields = re.findall(r"^[ \t]*(?:u32|__le32)\s+des\d;[^\n]*", whole, re.M)
        dw_fields[name] = "struct " + name + " {\n" + "\n".join(fields) + "\n};"
    dw_function = find_function(dw["text"], "dw_mci_idmac_init")
    evidence.append(excerpt(dw, "dw_mci_idmac_init_original", dw_function))
    for expected in ("struct idmac_desc_64addr *p;", "struct idmac_desc *p;"):
        if expected not in dw_function:
            raise ValueError("reviewed dw_mmc declaration absent")
    evidence_path = out / "source_evidence.json"
    evidence_path.write_text(json.dumps({"schema": "reviewed-source-projection-v1", "excerpts": evidence,
        "scope": "Only already reviewed fixed revision files. Line excerpts are exact; projections replace kernel surroundings."},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    runtime = RUNTIME.replace("@HCI_SCHEMA@", schema).replace("@HOST_FIELDS@", "\n".join(host_fields))
    runtime = runtime.replace("@HCI_OLD_ASSIGN@", "\n".join(assignments["hci_old"]))
    runtime = runtime.replace("@HCI_FIX_ASSIGN@", "\n".join(assignments["hci_fix"]))
    runtime = runtime.replace("@HCI_PARTIAL_ASSIGN@", assignments["hci_fix"][0] + "\n" + assignments["hci_old"][1])
    (out / "runtime_projection.c").write_text(runtime, encoding="utf-8")
    scope = SCOPE.replace("@DW_STRUCTS@", "\n".join(dw_fields.values()))
    (out / "scope_projection.c").write_text(scope, encoding="utf-8")
    wrong = scope.replace("__typeof__(p), struct idmac_desc_64addr *", "__typeof__(p), struct idmac_desc *", 1)
    if wrong == scope:
        raise ValueError("negative association projection failed")
    (out / "scope_wrong_association.c").write_text(wrong, encoding="utf-8")
    return {"historical_source_count": len(records), "source_evidence_sha256": sha256(evidence_path.read_bytes()),
            "projection_sha256": {p.name: sha256(p.read_bytes()) for p in out.glob("*.c")}}


RUNTIME = r'''/* Generated projection of exact reviewed declarations and HCI assignments.
 * Surrounding kernel/sk_buff paths are modeled, not compiled as a kernel TU. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint16_t __u16;
typedef uint16_t __le16;
#define __packed __attribute__((packed))
#define HCI_OP_LE_WRITE_DEF_DATA_LEN 0x2024
@HCI_SCHEMA@
struct hci_dev {
@HOST_FIELDS@
};
_Static_assert(sizeof(struct hci_cp_le_write_def_data_len) == 4, "HCI payload width");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct hci_dev *)0)->le_max_tx_len), __u16), "host field width");
/* GCC collapses plain typedefs; this assertion documents that endian meaning
 * is NOT a GCC type distinction without Sparse annotations. */
_Static_assert(__builtin_types_compatible_p(__u16, __le16), "plain endian typedefs collapse");
static __le16 cpu_to_le16(__u16 n) {
#if __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
    return __builtin_bswap16(n);
#else
    return n;
#endif
}
struct hci_request { unsigned char data[4]; };
static void hci_req_add(struct hci_request *req, unsigned op, size_t plen, const void *param) {
    assert(op == HCI_OP_LE_WRITE_DEF_DATA_LEN && plen == sizeof(req->data));
    memcpy(req->data, param, plen);
}
static void hci_old(struct hci_request *req, const struct hci_dev *hdev) {
    struct hci_cp_le_write_def_data_len cp;
@HCI_OLD_ASSIGN@
    hci_req_add(req, HCI_OP_LE_WRITE_DEF_DATA_LEN, sizeof(cp), &cp);
}
static void hci_fixed(struct hci_request *req, const struct hci_dev *hdev) {
    struct hci_cp_le_write_def_data_len cp;
@HCI_FIX_ASSIGN@
    hci_req_add(req, HCI_OP_LE_WRITE_DEF_DATA_LEN, sizeof(cp), &cp);
}
static void hci_partial(struct hci_request *req, const struct hci_dev *hdev) {
    struct hci_cp_le_write_def_data_len cp;
@HCI_PARTIAL_ASSIGN@
    hci_req_add(req, HCI_OP_LE_WRITE_DEF_DATA_LEN, sizeof(cp), &cp);
}
static void hex(const unsigned char *p, size_t n) {
    for (size_t i = 0; i < n; ++i) printf("%02x", (unsigned)p[i]);
}
static void put_le32(uint32_t n, unsigned char *p) {
    for (unsigned i=0; i<4; ++i) p[i]=(unsigned char)(n >> (8*i));
}
static uint32_t get_le32(const unsigned char *p) {
    uint32_t n=0;
    for (unsigned i=0; i<4; ++i) n |= (uint32_t)p[i] << (8*i);
    return n;
}
static uint32_t get_host32(const unsigned char *p) {
    /* memcpy deliberately avoids alignment/aliasing assumptions. This only
     * projects numeric representation of the old u32* consumer. */
    uint32_t n; memcpy(&n,p,sizeof(n)); return n;
}
int main(void) {
#if __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
    const char *endian="big";
#else
    const char *endian="little";
#endif
    printf("META,%s,%zu,%zu\n",endian,sizeof(uint16_t),sizeof(uint32_t));
    const struct hci_dev pairs[]={{0x001b,0x0148},{0x1234,0xabcd},{0,0}};
    for (size_t i=0;i<sizeof(pairs)/sizeof(pairs[0]);++i) {
        struct hci_request a,b,c;
        hci_old(&a,&pairs[i]); hci_fixed(&b,&pairs[i]); hci_partial(&c,&pairs[i]);
        printf("HCI,%u,%u,",(unsigned)pairs[i].le_max_tx_len,(unsigned)pairs[i].le_max_tx_time);
        hex(a.data,4); putchar(','); hex(b.data,4); putchar(','); hex(c.data,4); putchar('\n');
    }
    const uint32_t sizes[]={0x12345678,0x00100020,0};
    for(size_t i=0;i<sizeof(sizes)/sizeof(sizes[0]);++i) {
        uint32_t n=sizes[i]; unsigned char host[4],le[4];
        memcpy(host,&n,sizeof(n)); put_le32(n,le);
        printf("CD,%u,%u,%u,%u,%u,",n,get_host32(host),get_le32(le),get_le32(host),get_host32(le));
        hex(host,4); putchar(','); hex(le,4); putchar('\n');
    }
    return 0;
}
'''


SCOPE = r'''/* Exact dw_mmc member declarations; macros and host path excluded.
 * Branch root declarations preserve the reviewed original names and types. */
#include <stdint.h>
typedef uint32_t u32;
typedef uint32_t __le32;
@DW_STRUCTS@
int scope_projection(int mode) {
    if (mode == 1) {
        struct idmac_desc_64addr *p;
        struct idmac_desc_64addr object = {0};
        p = &object;
        _Static_assert(__builtin_types_compatible_p(__typeof__(p), struct idmac_desc_64addr *), "first p belongs to 64addr declaration");
        _Static_assert(sizeof(p->des0) == 4, "first p scalar width");
        p->des0 = 0;
        p->des1 = 0;
        p->des2 = 0;
        p->des3 = 0;
        return p->des0;
    } else {
        struct idmac_desc *p;
        struct idmac_desc object = {0};
        p = &object;
        _Static_assert(__builtin_types_compatible_p(__typeof__(p), struct idmac_desc *), "second p belongs to 32addr declaration");
        _Static_assert(sizeof(p->des0) == 4, "second p scalar width");
        p->des0 = 0;
        p->des1 = 0;
        return p->des0;
    }
}
/* Additional synthetic nested shadow; not present in the dw_mmc snippet. */
int nested_shadow_projection(void) {
    uint32_t p = 0;
    _Static_assert(sizeof(p)==4,"outer synthetic p");
    {
        uint16_t p = 0;
        _Static_assert(sizeof(p)==2,"inner synthetic p");
        (void)p;
    }
    return (int)p;
}
'''


def parse_runtime(stdout: str) -> dict:
    rows = [line.split(",") for line in stdout.splitlines()]
    if len(rows) != 7 or rows[0][0] != "META":
        raise ValueError("runtime output shape changed")
    result = {"host_endian": rows[0][1], "u16_bytes": int(rows[0][2]), "u32_bytes": int(rows[0][3]),
              "hci": [], "coredump": []}
    for row in rows[1:]:
        if row[0] == "HCI":
            length, time = int(row[1]), int(row[2])
            expected = length.to_bytes(2, "little").hex() + time.to_bytes(2, "little").hex()
            result["hci"].append({"tx_len": length, "tx_time": time, "old_hex": row[3],
                "full_fix_hex": row[4], "partial_fix_hex": row[5], "schema_expected_hex": expected})
        elif row[0] == "CD":
            result["coredump"].append({"input": int(row[1]), "host_write_host_read": int(row[2]),
                "le_write_le_read": int(row[3]), "host_write_le_read": int(row[4]),
                "le_write_host_read": int(row[5]), "host_hex": row[6], "le_hex": row[7]})
        else:
            raise ValueError("runtime tag changed")
    if len(result["hci"]) != 3 or len(result["coredump"]) != 3:
        raise ValueError("missing runtime controls")
    return result


def parse_scope_dump(path: Path) -> dict:
    """Recover only the first generated probe function's GCC declaration graph.

    This deliberately is not a general GCC/kernel AST reader. Original branch
    declarations are projected into a small TU whose graph shape is checked.
    """
    raw = path.read_text(encoding="utf-8").split(";; Function nested_shadow_projection")[0]
    nodes = {m.group(1): {"kind": m.group(2), "body": m.group(3)}
             for m in re.finditer(r"(?m)^@(\d+)\s+(\w+)\s+(.*?)(?=\n@|\Z)", raw, re.S)}

    def ref(node: str, label: str) -> str:
        match = re.search(re.escape(label) + r"\s*:\s*@(\d+)", nodes[node]["body"])
        if not match:
            raise ValueError(f"GCC probe graph link missing @{node}:{label}")
        return match.group(1)

    def name(node: str) -> str:
        match = re.search(r"strg:\s*(\S+)\s+lngt:", nodes[node]["body"])
        if not match:
            raise ValueError("GCC probe identifier shape changed")
        return match.group(1)

    bindings = {}
    for ident, node in nodes.items():
        if node["kind"] != "var_decl" or name(ref(ident, "name")) != "p":
            continue
        pointer = ref(ident, "type")
        record = ref(pointer, "ptd")
        bindings[ident] = {"declaration_node": "@" + ident,
            "pointer_type_node": "@" + pointer, "record_type_node": "@" + record,
            "root_struct": name(ref(record, "name")),
            "projected_source": re.search(r"srcp:\s*(\S+)", node["body"]).group(1),
            "member_stores": []}
    for ident, node in nodes.items():
        if node["kind"] != "modify_expr":
            continue
        left = ref(ident, "op 0")
        if nodes[left]["kind"] != "component_ref":
            continue
        indirect = ref(left, "op 0")
        if nodes[indirect]["kind"] != "indirect_ref":
            raise ValueError("GCC probe member root shape changed")
        decl = ref(indirect, "op 0")
        field = ref(left, "op 1")
        field_type = ref(field, "type")
        alias_decl = ref(field_type, "name")
        bindings[decl]["member_stores"].append({"store_node": "@" + ident,
            "field_decl_node": "@" + field, "member": name(ref(field, "name")),
            "type_alias_spelling": name(ref(alias_decl, "name")),
            "projected_field_source": re.search(r"srcp:\s*(\S+)", nodes[field]["body"]).group(1)})
    by_struct = {b["root_struct"]: b for b in bindings.values()}
    assert set(by_struct) == {"idmac_desc_64addr", "idmac_desc"}
    assert [f["member"] for f in by_struct["idmac_desc_64addr"]["member_stores"]] == ["des0", "des1", "des2", "des3"]
    assert all(f["type_alias_spelling"] == "u32" for f in by_struct["idmac_desc_64addr"]["member_stores"])
    assert [f["member"] for f in by_struct["idmac_desc"]["member_stores"]] == ["des0", "des1"]
    assert all(f["type_alias_spelling"] == "__le32" for f in by_struct["idmac_desc"]["member_stores"])
    return {"scope": "GCC original-tree graph for one reduced development probe, not a kernel TU parser",
            "bindings": list(bindings.values()), "distinct_same_name_declarations": len(bindings) == 2,
            "endian_alias_note": "GCC preserves typedef spelling in this dump, but plain typedefs remain compatible and assignments are not endian checked."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linux-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    out = args.output_dir.resolve()
    source_info = make_sources(args.linux_dir, out)
    commands = []

    def run(argv: list[str], expected: int = 0) -> subprocess.CompletedProcess:
        process = subprocess.run(argv, capture_output=True, text=True)
        commands.append({"argv": argv, "returncode": process.returncode,
                         "stdout": process.stdout, "stderr": process.stderr, "expected_returncode": expected})
        if (expected == 0 and process.returncode != 0) or (expected != 0 and process.returncode == 0):
            raise RuntimeError(f"unexpected command result: {argv}: {process.stderr}")
        return process

    versions = {}
    tools_available = {name: shutil.which(name) for name in ("gcc", "s390x-linux-gnu-gcc", "qemu-s390x", "sparse", "clang")}
    for name in ("gcc", "s390x-linux-gnu-gcc", "qemu-s390x"):
        if not tools_available[name]:
            raise RuntimeError(f"required installed tool absent: {name}")
        versions[name] = run([name, "--version"]).stdout.splitlines()[0]
    runs = {}
    with tempfile.TemporaryDirectory(prefix="structured-payload-probe-") as temp_name:
        temp = Path(temp_name)
        for target, compiler, launcher in (("x86_64", "gcc", []), ("s390x", "s390x-linux-gnu-gcc", ["qemu-s390x"])):
            binary = temp / ("runtime-" + target)
            run([compiler, "-static", "-std=gnu11", "-O2", "-Wall", "-Wextra", "-Werror",
                 str(out / "runtime_projection.c"), "-o", str(binary)])
            result = parse_runtime(run(launcher + [str(binary)]).stdout)
            result["executable_sha256"] = sha256(binary.read_bytes())
            runs[target] = result
        tree_dump = out / "scope_tree_original.txt"
        scope_compile = run(["gcc", "-std=gnu11", "-O0", "-Wall", "-Wextra", "-Wshadow=local",
            "-fdump-tree-original-raw=" + str(tree_dump), "-c", str(out / "scope_projection.c"),
            "-o", str(temp / "scope.o")])
        if "shadows a previous local" not in scope_compile.stderr:
            raise ValueError("synthetic shadow diagnostic not produced")
        negative = run(["gcc", "-std=gnu11", "-c", str(out / "scope_wrong_association.c"),
                        "-o", str(temp / "wrong.o")], expected=1)
        if "first p belongs to 64addr declaration" not in negative.stderr:
            raise ValueError("negative binding failure absent")
    scope_bindings = parse_scope_dump(tree_dump)
    (out / "scope_bindings.json").write_text(json.dumps(scope_bindings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    checks = []
    for target, expected_endian in (("x86_64", "little"), ("s390x", "big")):
        case = runs[target]
        assert case["host_endian"] == expected_endian and case["u16_bytes"] == 2 and case["u32_bytes"] == 4
        for h in case["hci"]:
            assert h["full_fix_hex"] == h["schema_expected_hex"]
            if h["tx_len"] == 0:
                assert h["old_hex"] == h["partial_fix_hex"] == h["full_fix_hex"]
            elif expected_endian == "little":
                assert h["old_hex"] == h["partial_fix_hex"] == h["full_fix_hex"]
            else:
                assert h["old_hex"] != h["schema_expected_hex"] and h["partial_fix_hex"] != h["schema_expected_hex"]
        for c in case["coredump"]:
            assert c["host_write_host_read"] == c["le_write_le_read"] == c["input"]
            if c["input"] == 0 or expected_endian == "little":
                assert c["host_write_le_read"] == c["le_write_host_read"] == c["input"]
            else:
                assert c["host_write_le_read"] != c["input"] and c["le_write_host_read"] != c["input"]
        nonzero_hci = [h for h in case["hci"] if h["tx_len"] != 0]
        old_mismatches = sum(h["old_hex"] != h["schema_expected_hex"] for h in nonzero_hci)
        partial_mismatches = sum(h["partial_fix_hex"] != h["schema_expected_hex"] for h in nonzero_hci)
        case["hci_nonzero_input_summary"] = {"input_pairs": 2, "old_mismatches": old_mismatches,
            "partial_fix_mismatches": partial_mismatches, "full_fix_mismatches": 0,
            "zero_control_note": "Equal zero bytes demonstrate value sensitivity only; they do not prove this path correct."}
        nonzero_cd = [c for c in case["coredump"] if c["input"] != 0]
        write_only_mismatches = sum(c["le_write_host_read"] != c["input"] for c in nonzero_cd)
        read_only_mismatches = sum(c["host_write_le_read"] != c["input"] for c in nonzero_cd)
        case["coredump_nonzero_input_summary"] = {"inputs": 2, "host_host_mismatches": 0,
            "le_le_mismatches": 0, "write_only_conversion_mismatches": write_only_mismatches,
            "read_only_conversion_mismatches": read_only_mismatches,
            "scope_note": "Numeric representation only; alignment, queue/lifetime and external format requirements remain unproved."}
        checks.append(f"{target} ({expected_endian}): HCI old mismatch {old_mismatches}/2, partial mismatch {partial_mismatches}/2, full-fix mismatch 0/2 on nonzero pairs; zero is a value-sensitivity control")
        checks.append(f"{target} ({expected_endian}): coredump host/host and le/le round trips match; write-only mismatch {write_only_mismatches}/2, read-only mismatch {read_only_mismatches}/2 on nonzero inputs")
    report = {"schema": "structured-payload-compiler-probe-v1", "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Known development examples; reduced C projection and user-mode QEMU only. No independent holdout or kernel/device execution.",
        "authority": {"hci": "Same-revision packed __le16 command schema; controller implementation/spec conformance not independently executed.",
            "coredump": "Same-host producer/consumer contract; old host/host remains numerically self-consistent. No external byte-order contract inferred."},
        "tools_available": tools_available, "tool_versions": versions, "commands": commands,
        **source_info, "scope_dump_sha256": sha256(tree_dump.read_bytes()), "runner_sha256": sha256(Path(__file__).read_bytes()),
        "compiler_type_facts": {"host_field_u16_width_checked": True, "payload_width_checked": 4,
            "plain_u16_and_le16_types_compatible": True, "endian_semantic_check_performed_by_gcc": False,
            "correct_block_binding_compile_succeeded": True, "wrong_global_name_binding_compile_rejected": True},
        "scope_bindings": scope_bindings,
        "runs": runs, "assertions": checks,
        "limits": ["GCC plain __le16/__le32 typedefs collapse to host integer types; Sparse is absent and was not installed.",
            "Block identity is checked in a reduced TU using original declarations; this does not resolve actual kernel includes or conditional compilation.",
            "coredump host reads use memcpy in the model; alignment, aliasing and original skb pointer safety are not proved.",
            "Reachability, real controller behavior, queue ordering, hardware faults and population detection accuracy are unproved."]}
    (out / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result": str(out / "results.json"), "targets": list(runs), "assertions": len(checks),
                      "gcc_scope_negative_rejected": True, "sparse_available": tools_available["sparse"] is not None}))


if __name__ == "__main__":
    main()
