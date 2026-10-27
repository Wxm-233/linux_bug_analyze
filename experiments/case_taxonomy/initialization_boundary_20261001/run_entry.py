"""Preserve reviewed historical HCI init entry conditions in a bounded projection.

The complete __hci_init, hci_init3_req and hci_init4_req texts are kept. Request
synchronization, other setup helpers, controller responses and queues are stubs.
This is development verification of source conditions, not a kernel execution.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PARENT = "cef456cd354ef485f12d57000c455e83e416a2b6"
FIX = "727ea61a5028f8ac96f75ab34cb1b56e63fd9227"
VARIANTS = {"parent": PARENT, "fix": FIX}
CORE = "net/bluetooth/hci_core.c"
HEADER = "include/net/bluetooth/hci.h"
CORE_HEADER = "include/net/bluetooth/hci_core.h"
EVENT = "net/bluetooth/hci_event.c"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def function(source: str, name: str) -> str:
    match = re.search(r"(?:static\s+)?[^\n]+\b" + re.escape(name) + r"\([^;]*?\n\{", source)
    if not match:
        raise ValueError(f"function absent: {name}")
    brace = source.index("{", match.start())
    level = 0
    for pos in range(brace, len(source)):
        if source[pos] == "{":
            level += 1
        elif source[pos] == "}":
            level -= 1
            if level == 0:
                return source[match.start():pos + 1]
    raise ValueError("unbalanced reviewed function")


def structure(source: str, name: str) -> str:
    match = re.search(r"struct " + name + r"\s*\{.*?\n\}(?:\s+__packed)?;", source, re.S)
    if not match:
        raise ValueError(f"structure absent: {name}")
    return match.group()


def define(source: str, name: str) -> str:
    found = re.findall(r"^#define[ \t]+" + re.escape(name) + r"(?:[ \t]|\().*(?:\\\n[^\n]*)*", source, re.M)
    if len(found) != 1:
        raise ValueError(f"macro absent/nonunique: {name}")
    return found[0]


def evidence(record: dict, label: str, text: str) -> dict:
    if record["text"].count(text) != 1:
        raise ValueError(f"excerpt nonunique: {record['path']}:{label}")
    line = record["text"][:record["text"].index(text)].count("\n") + 1
    return {"label": label, "revision": record["revision"], "path": record["path"],
            "blob": record["blob"], "source_sha256": record["source_sha256"],
            "start_line": line, "end_line": line + text.count("\n"), "text": text}


def build_variant(linux_dir: Path, out: Path, label: str, revision: str, commands: list) -> dict:
    sources = {}
    for path in (CORE, HEADER, CORE_HEADER, EVENT):
        argv = ["git", "show", f"{revision}:{path}"]
        result = subprocess.run(argv, cwd=linux_dir, capture_output=True, check=True)
        commands.append({"argv": argv, "cwd": str(linux_dir), "returncode": result.returncode,
            "stdout_sha256": sha(result.stdout), "stdout_saved_as": "exact selected excerpts in source_evidence.json", "stderr": result.stderr.decode()})
        blob_args = ["git", "rev-parse", f"{revision}:{path}"]
        blob = subprocess.run(blob_args, cwd=linux_dir, capture_output=True, text=True, check=True)
        commands.append({"argv": blob_args, "cwd": str(linux_dir), "returncode": blob.returncode,
                         "stdout": blob.stdout, "stderr": blob.stderr})
        sources[path] = {"revision": revision, "path": path, "blob": blob.stdout.strip(),
                         "source_sha256": sha(result.stdout), "text": result.stdout.decode()}
    excerpts = []
    functions = {}
    for name in ("__hci_init", "hci_init3_req", "hci_init4_req"):
        text = function(sources[CORE]["text"], name)
        excerpts.append(evidence(sources[CORE], name, text))
        functions[name] = text
    reader = function(sources[EVENT]["text"], "hci_cc_le_write_def_data_len")
    excerpts.append(evidence(sources[EVENT], "actual_local_completion_reader", reader))
    combined = "\n".join(functions.values())
    constants = set(re.findall(r"\bHCI_[A-Z0-9_]+\b", combined))
    # These enum flags are passed only to explicitly false-returning helper
    # stubs; arbitrary numeric IDs do not model the real flag namespace.
    synthetic_flag_ids = {"HCI_SETUP", "HCI_CONFIG", "HCI_SSP_ENABLED", "HCI_QUIRK_BROKEN_STORED_LINK_KEY"}
    macro_names = constants - synthetic_flag_ids
    macro_names.update(("HCI_PRIMARY", "HCI_AMP", "LMP_LE", "LMP_SYNC_TRAIN", "LMP_NO_BREDR"))
    macros = []
    for name in sorted(macro_names):
        owning_header = CORE_HEADER if name == "HCI_MAX_PAGES" else HEADER
        text = define(sources[owning_header]["text"], name)
        excerpts.append(evidence(sources[owning_header], name, text))
        macros.append(text)
    for name in ("lmp_le_capable", "lmp_sync_train_capable", "lmp_bredr_capable"):
        text = define(sources[CORE_HEADER]["text"], name)
        excerpts.append(evidence(sources[CORE_HEADER], name, text))
        macros.append(text)
    structs = []
    for name in ("hci_cp_read_stored_link_key", "hci_cp_read_local_ext_features", "hci_cp_delete_stored_link_key",
                 "hci_cp_le_write_def_data_len", "hci_cp_le_set_default_phy"):
        text = structure(sources[HEADER]["text"], name)
        structs.append(text)
        excerpts.append(evidence(sources[HEADER], name, text))
    defaults = []
    allocation = function(sources[CORE]["text"], "hci_alloc_dev")
    for field in ("le_max_tx_len", "le_max_tx_time"):
        matches = re.findall(r"^[ \t]*hdev->" + field + r"\s*=\s*0x[0-9a-fA-F]+;", allocation, re.M)
        if len(matches) != 1:
            raise ValueError("historical allocation default absent")
        defaults.append(matches[0].strip())
        excerpts.append(evidence(sources[CORE], "historical_default_" + field, matches[0]))
    c_source = C_TEMPLATE.replace("@VARIANT@", label).replace("@MACROS@", "\n".join(macros))
    c_source = c_source.replace("@STRUCTS@", "\n".join(structs))
    c_source = c_source.replace("@ORIGINAL_FUNCTIONS@", functions["hci_init3_req"] + "\n" + functions["hci_init4_req"])
    c_source = c_source.replace("@ORIGINAL_ENTRY@", functions["__hci_init"]).replace("@ORIGINAL_READER@", reader)
    c_source = c_source.replace("@DEFAULTS@", "\n".join(defaults))
    c_path = out / f"entry_{label}.c"
    c_path.write_text(c_source, encoding="utf-8")
    return {"variant": label, "revision": revision, "source_path": str(c_path), "generated_c_sha256": sha(c_path.read_bytes()),
            "excerpts": excerpts, "synthetic_flag_ids": sorted(synthetic_flag_ids)}


C_TEMPLATE = r'''/* Full reviewed entry/init3/init4/reader texts surrounded by explicit stubs.
 * This is request construction in a user-mode fixture, not kernel/controller execution. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <stddef.h>
#include <errno.h>
typedef uint8_t u8;
typedef uint8_t __u8;
typedef uint16_t __u16;
typedef uint16_t __le16;
#define __packed __attribute__((packed))
#define BT_DBG(...) do {} while(0)
#define msecs_to_jiffies(n) (n) /* no real clock/timer */
@MACROS@
/* Synthetic IDs used only by helpers that always return false. */
#define HCI_SETUP 1
#define HCI_CONFIG 2
#define HCI_SSP_ENABLED 3
#define HCI_QUIRK_BROKEN_STORED_LINK_KEY 4
typedef struct { __u8 b[6]; } bdaddr_t;
static const bdaddr_t zero_address={{0}};
#define BDADDR_ANY (&zero_address)
static void bacpy(bdaddr_t *dst, const bdaddr_t *src) { memcpy(dst,src,sizeof(*dst)); }
@STRUCTS@
_Static_assert(sizeof(struct hci_cp_le_write_def_data_len)==4,"payload width");
struct hci_dev {
    __u8 dev_type;
    __u8 features[HCI_MAX_PAGES][8],le_features[8],commands[64],max_page;
    unsigned long quirks;
    __u8 le_tx_def_phys,le_rx_def_phys;
    __u16 le_max_tx_len,le_max_tx_time,le_def_tx_len,le_def_tx_time;
    char name[16];
};
struct hci_request { struct hci_dev *hdev; };
struct sk_buff { unsigned char *data; };
struct trace {
    int early_error;
    unsigned stages[4],stage_count,opcodes[64],opcode_count,target_count;
    struct hci_cp_le_write_def_data_len sent;
    unsigned helper_stub_calls;
};
static struct trace *active;
static __u16 le16_to_cpu(__le16 value) {
#if __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
    return __builtin_bswap16(value);
#else
    return value;
#endif
}
static inline __le16 cpu_to_le16(__u16 value) { return le16_to_cpu(value); }
static void hci_req_add(struct hci_request *req, unsigned opcode, size_t length, const void *parameter) {
    (void)req;
    assert(active->opcode_count<64);
    active->opcodes[active->opcode_count++]=opcode;
    if(opcode==HCI_OP_LE_WRITE_DEF_DATA_LEN) {
        assert(length==sizeof(active->sent) && parameter!=NULL);
        memcpy(&active->sent,parameter,length);
        ++active->target_count;
    }
}
/* False/no-op setup helpers; immutable fixture capabilities and defaults. */
static int test_bit(unsigned n,const unsigned long *p) { (void)n;(void)p;++active->helper_stub_calls;return 0; }
static int hci_dev_test_flag(struct hci_dev *hdev,unsigned f) { (void)hdev;(void)f;++active->helper_stub_calls;return 0; }
static int bredr_sc_enabled(struct hci_dev *hdev) { (void)hdev;++active->helper_stub_calls;return 0; }
static int use_ext_scan(struct hci_dev *hdev) { (void)hdev;++active->helper_stub_calls;return 0; }
static int use_ext_conn(struct hci_dev *hdev) { (void)hdev;++active->helper_stub_calls;return 0; }
static int ext_adv_capable(struct hci_dev *hdev) { (void)hdev;++active->helper_stub_calls;return 0; }
static void hci_setup_event_mask(struct hci_request *req) { (void)req;++active->helper_stub_calls; }
static void hci_setup_link_policy(struct hci_request *req) { (void)req;++active->helper_stub_calls; }
static void hci_set_le_support(struct hci_request *req) { (void)req;++active->helper_stub_calls; }
static void hci_set_event_mask_page_2(struct hci_request *req) { (void)req;++active->helper_stub_calls; }
static void hci_debugfs_create_basic(struct hci_dev *hdev) { (void)hdev;++active->helper_stub_calls; }
static void hci_debugfs_create_common(struct hci_dev *hdev) { (void)hdev;++active->helper_stub_calls; }
static void hci_debugfs_create_bredr(struct hci_dev *hdev) { (void)hdev;++active->helper_stub_calls; }
static void hci_debugfs_create_le(struct hci_dev *hdev) { (void)hdev;++active->helper_stub_calls; }
static int hci_init1_req(struct hci_request *req,unsigned long opt) { (void)req;(void)opt;return 0; }
static int hci_init2_req(struct hci_request *req,unsigned long opt) { (void)req;(void)opt;return 0; }
@ORIGINAL_FUNCTIONS@
static int __hci_req_sync(struct hci_dev *hdev,int (*callback)(struct hci_request *,unsigned long),
                          unsigned long opt,unsigned timeout,void *status) {
    (void)timeout;(void)status;
    unsigned stage=callback==hci_init1_req?1:callback==hci_init2_req?2:callback==hci_init3_req?3:4;
    assert(active->stage_count<4);
    active->stages[active->stage_count++]=stage;
    /* Error injection is before the stage-1 stub callback, not a real timeout. */
    if(stage==1 && active->early_error) return -EIO;
    struct hci_request req={hdev};
    return callback(&req,opt);
}
@ORIGINAL_ENTRY@
static void *hci_sent_cmd_data(struct hci_dev *hdev,unsigned opcode) {
    (void)hdev;
    return opcode==HCI_OP_LE_WRITE_DEF_DATA_LEN && active->target_count?&active->sent:NULL;
}
@ORIGINAL_READER@
static void emit(int primary,int le,int extension,int error,int result,struct hci_dev *hdev) {
    printf("{\"kind\":\"row\",\"variant\":\"@VARIANT@\",\"primary\":%d,\"lmp_le_capability\":%d,\"extension\":%d,\"early_error\":%d,\"result\":%d,\"stages\":[",primary,le,extension,error,result);
    for(unsigned i=0;i<active->stage_count;++i) printf("%s%u",i?",":"",active->stages[i]);
    printf("],\"add_attempt_opcodes\":[");
    for(unsigned i=0;i<active->opcode_count;++i) printf("%s%u",i?",":"",active->opcodes[i]);
    printf("],\"target_add_attempt_count\":%u,\"simulated_target_copy_count\":%u,\"helper_stub_calls\":%u,\"host_values\":[%u,%u],\"reader_values\":[%u,%u],\"payload_hex\":",active->target_count,active->target_count,active->helper_stub_calls,hdev->le_max_tx_len,hdev->le_max_tx_time,hdev->le_def_tx_len,hdev->le_def_tx_time);
    if(active->target_count) {
        putchar('"');
        unsigned char *p=(void *)&active->sent;
        for(size_t i=0;i<sizeof(active->sent);++i) printf("%02x",(unsigned)p[i]);
        putchar('"');
    } else printf("null");
    puts("}");
}
int main(void) {
    __u16 marker=0x0102;unsigned char bytes[2];memcpy(bytes,&marker,2);
    const char *host_order=bytes[0]==1 && bytes[1]==2?"big":bytes[0]==2 && bytes[1]==1?"little":"unknown";
    assert(strcmp(host_order,"unknown")!=0);
#if __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
    assert(strcmp(host_order,"big")==0);
#else
    assert(strcmp(host_order,"little")==0);
#endif
    printf("{\"kind\":\"meta\",\"variant\":\"@VARIANT@\",\"actual_host_order\":\"%s\",\"payload_bytes\":%zu,\"primary_constant\":%u,\"other_constant\":%u,\"le_mask\":%u,\"extension_mask\":%u}\n",host_order,sizeof(struct hci_cp_le_write_def_data_len),HCI_PRIMARY,HCI_AMP,LMP_LE,HCI_LE_DATA_LEN_EXT);
    for(int primary=0;primary<=1;++primary)
        for(int le=0;le<=1;++le)
            for(int extension=0;extension<=1;++extension)
                for(int error=0;error<=1;++error) {
                    struct trace t={.early_error=error};active=&t;
                    struct hci_dev dev={0};struct hci_dev *hdev=&dev;
                    hdev->dev_type=primary?HCI_PRIMARY:HCI_AMP;
                    hdev->features[0][4]=le?LMP_LE:0;
                    hdev->le_features[0]=extension?HCI_LE_DATA_LEN_EXT:0;
                    hdev->le_def_tx_len=51;hdev->le_def_tx_time=801;
@DEFAULTS@
                    int result=__hci_init(hdev);
                    if(active->target_count) {
                        unsigned char success=0;struct sk_buff skb={&success};
                        hci_cc_le_write_def_data_len(hdev,&skb);
                    }
                    emit(primary,le,extension,error,result,hdev);
                }
    return 0;
}
'''


def analyze(stdout: str, variant: str, expected_host_order: str) -> dict:
    lines = [json.loads(line) for line in stdout.splitlines()]
    meta, rows = lines[0], lines[1:]
    assert meta == {"kind": "meta", "variant": variant, "actual_host_order": expected_host_order,
                    "payload_bytes": 4, "primary_constant": 0, "other_constant": 1, "le_mask": 64, "extension_mask": 32}
    if len(rows) != 16:
        raise ValueError("expected 16 configurations per version and target")
    expected_keys = set(itertools.product((0, 1), repeat=4))
    seen = set()
    for row in rows:
        key = tuple(row[n] for n in ("primary", "lmp_le_capability", "extension", "early_error"))
        assert key in expected_keys and key not in seen
        seen.add(key)
        primary, le, extension, error = key
        expected_stages = [1] if error else [1, 2, 3, 4] if primary else [1, 2]
        assert row["stages"] == expected_stages
        assert row["result"] == (-5 if error else 0)
        expected_queued = bool(primary and extension and not error)
        assert row["target_add_attempt_count"] == row["simulated_target_copy_count"] == int(expected_queued)
        assert row["add_attempt_opcodes"].count(0x2024) == int(expected_queued)
        assert row["add_attempt_opcodes"].count(0x202F) == int(bool(primary and le and extension and not error))
        assert row["host_values"] == [27, 328]
        row["fixture_state"] = "inconsistent_LE_off_with_DATA_LEN_EXT_on; real-device reachability unproved" if not le and extension else "bounded capability fixture; real-device reachability unproved"
        row["applicability"] = "applicable_at_simulated_target_add_copy" if expected_queued else "not_applicable"
        row["unproved"] = ["actual configured controller and feature discovery", "kernel request synchronization and responses",
                           "full initialization side effects", "real controller/device execution"]
        if expected_queued:
            actual = bytes.fromhex(row["payload_hex"])
            needed = (27).to_bytes(2, "little") + (328).to_bytes(2, "little")
            produced_order = expected_host_order if variant == "parent" else "little"
            expected_produced = (27).to_bytes(2, produced_order) + (328).to_bytes(2, produced_order)
            expected_reader = [int.from_bytes(actual[:2], "little"), int.from_bytes(actual[2:], "little")]
            assert actual == expected_produced
            assert row["reader_values"] == expected_reader
            row["expected_schema_payload_hex"] = needed.hex()
            row["payload_matches_source_contract"] = actual == needed
            row["local_reader_matches_host_values"] = expected_reader == [27, 328]
            row["projection_verdict"] = "conditional_numeric_match" if actual == needed else "conditional_representation_mismatch"
        else:
            assert row["payload_hex"] is None and row["reader_values"] == [51, 801]
            row["expected_schema_payload_hex"] = None
            row["payload_matches_source_contract"] = None
            row["local_reader_matches_host_values"] = None
            row["projection_verdict"] = "not_applicable; target add not attempted, byte check not executed"
    assert seen == expected_keys
    applicable = [r for r in rows if r["target_add_attempt_count"]]
    return {"metadata": meta, "rows": rows, "summary": {"configurations": 16, "configurations_with_target_add_attempt": len(applicable),
            "not_applicable": 16 - len(applicable), "byte_mismatch_at_mock_copy": sum(not r["payload_matches_source_contract"] for r in applicable),
            "inconsistent_fixtures_with_target_add_attempt": sum(r["lmp_le_capability"] == 0 for r in applicable),
            "note": "Each grid cell is a bounded source-condition projection, not a new case or hardware run."}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linux-dir", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    runner_sha_before = sha(Path(__file__).read_bytes())
    commands = []
    variants = {label: build_variant(args.linux_dir, out, label, revision, commands)
                for label, revision in VARIANTS.items()}
    source_path = out / "source_evidence.json"
    source_path.write_text(json.dumps({"schema": "historical-init-entry-source-v1", "variants": variants},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    generated_sha_before = {label: sha((out / f"entry_{label}.c").read_bytes()) for label in variants}

    def run(argv: list[str]) -> subprocess.CompletedProcess:
        result = subprocess.run(argv, capture_output=True, text=True)
        commands.append({"argv": argv, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode != 0:
            raise RuntimeError(f"command failed: {argv}: {result.stderr}")
        return result

    versions = {name: run([name, "--version"]).stdout.splitlines()[0]
                for name in ("gcc", "s390x-linux-gnu-gcc", "qemu-s390x")}
    targets = {}
    with tempfile.TemporaryDirectory(prefix="hci-initialization-entry-") as temp_name:
        for target, compiler, launcher, order in (("x86_64", "gcc", [], "little"),
                ("s390x", "s390x-linux-gnu-gcc", ["qemu-s390x"], "big")):
            targets[target] = {}
            for variant in variants:
                binary = Path(temp_name) / (target + "-" + variant)
                run([compiler, "-static", "-std=gnu11", "-O2", "-Wall", "-Wextra", "-Werror",
                     "-Wno-unused-parameter", str(out / f"entry_{variant}.c"), "-o", str(binary)])
                result = analyze(run(launcher + [str(binary)]).stdout, variant, order)
                result["executable_sha256"] = sha(binary.read_bytes())
                targets[target][variant] = result
    runner_sha_after = sha(Path(__file__).read_bytes())
    generated_sha_after = {label: sha((out / f"entry_{label}.c").read_bytes()) for label in variants}
    assert runner_sha_before == runner_sha_after and generated_sha_before == generated_sha_after
    report = {"schema": "historical-hci-initialization-boundary-v1", "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Already read development example. Complete historical entry/init3/init4/reader texts in a stubbed user-mode fixture.",
        "matrix": {"device_type": ["HCI_PRIMARY", "HCI_AMP"], "LMP_LE_capability": [False, True],
                   "DATA_LEN_EXT": [False, True], "early_request_error": ["success", "stage1 -EIO"],
                   "versions": VARIANTS, "targets": ["x86_64", "s390x"], "total_cells": 64},
        "original_functions_preserved": ["__hci_init", "hci_init3_req", "hci_init4_req", "hci_cc_le_write_def_data_len"],
        "fixed_fixture_flags": {"HCI_LE_ENABLED_config_flag": False, "HCI_SETUP": False, "HCI_CONFIG": False,
            "HCI_SSP_ENABLED": False, "all_flags_via_hci_dev_test_flag": False,
            "note": "LMP_LE is a hardware capability bit, not the HCI_LE_ENABLED configuration flag."},
        "observation_point": {"stage": "hci_req_add entry before queue execution", "target_opcode": "HCI_OP_LE_WRITE_DEF_DATA_LEN",
            "expected_payload_size": 4, "parameter_copy": "memcpy into captured struct after asserting exact opcode/size; raw copy preserves pre-copy bytes",
            "contract_check_location": "Python after runtime exits; C only asserts opcode/layout/size and copies bytes. No semantic contract check or queue blocking runs in C.",
            "target_count_semantics": "Original builder add attempts and successful mock copies only; actual kernel enqueue not proved.",
            "layout_unknown_policy": "This fixture asserts 4-byte target layout; assertion failure stops experiment, no normal verdict."},
        "stub_assumptions": ["hci_init1_req and hci_init2_req always return success without real commands",
            "__hci_req_sync invokes stage callbacks directly; stage1 injected error occurs before the stub callback; no timeout, queue execution or controller response",
            "hci_req_add logs opcode and memcpy-copies the target command only; it does not execute commands",
            "commands[]/max_page are zero, quirk field zero, other helpers false/no-op; all setup helper invocations counted per row",
            "capability flags remain immutable; default max values 27/328 taken from historical allocation are not overwritten by simulated init3 responses",
            "hci_sent_cmd_data returns captured target parameters and successful status is injected only after a target was queued",
            "minimal hci_dev/sk_buff/request and bdaddr types replace real kernel types; timer, debugfs, flags, extended helpers are explicitly stubbed",
            "synthetic enum IDs are passed only to false-returning flag stubs, not claimed to be real kernel bit indices"],
        "critical_boundary": "init4 target checks DATA_LEN_EXT only. LE-off/feature-on still attempts target add in primary successful fixture; no real-device reachability inferred.",
        "commands": commands, "tool_versions": versions, "targets": targets,
        "source_evidence_sha256": sha(source_path.read_bytes()), "runner_sha256": runner_sha_after,
        "run_integrity": {"runner_sha_before": runner_sha_before, "runner_sha_after": runner_sha_after,
            "generated_sha_before": generated_sha_before, "generated_sha_after": generated_sha_after},
        "generated_c_sha256": {label: variants[label]["generated_c_sha256"] for label in variants},
        "limits": ["No original historical kernel, real controller or hardware execution", "No full feature/configured-state/response reachability proof",
            "Real hci_req_add_ev req.err/ENOMEM rejection, sync stage4 errors and outer ret==0/UNCONFIGURED/USER_CHANNEL entry conditions are not covered",
            "Not-applicable rows have no byte verdict; inconsistent fixtures are not new bugs", "No independent held-out cases or detection accuracy estimate"]}
    (out / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({t: {v: r["summary"] for v, r in entries.items()} for t, entries in targets.items()}))


if __name__ == "__main__":
    main()
