"""Bounded original-text HCI request-copy projection, not kernel execution.

Preparation preserves source excerpts and C; formal execution never regenerates
them. The four error/allocation combinations are fixed for each version/target.
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
REQUEST = "net/bluetooth/hci_request.c"
REQUEST_HEADER = "net/bluetooth/hci_request.h"
HEADER = "include/net/bluetooth/hci.h"
CORE_HEADER = "include/net/bluetooth/hci_core.h"
BT_HEADER = "include/net/bluetooth/bluetooth.h"
SKB_HEADER = "include/linux/skbuff.h"
SOURCE_PATHS = (CORE, REQUEST, REQUEST_HEADER, HEADER, CORE_HEADER, BT_HEADER, SKB_HEADER)
ORIGINAL_FUNCTIONS = ("hci_init4_req", "hci_req_add", "hci_req_add_ev", "hci_prepare_cmd", "skb_put_data")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def function(source: str, name: str) -> str:
    pattern = r"^(?:static\s+)?(?:inline\s+)?[^\n]+\b" + re.escape(name) + r"\([^;]*?\n\{"
    found = list(re.finditer(pattern, source, re.M))
    if len(found) != 1:
        raise ValueError(f"function absent/nonunique: {name} ({len(found)})")
    match = found[0]
    brace = source.index("{", match.start())
    level = 0
    for pos in range(brace, len(source)):
        if source[pos] == "{":
            level += 1
        elif source[pos] == "}":
            level -= 1
            if level == 0:
                return source[match.start():pos + 1]
    raise ValueError(f"unbalanced function: {name}")


def structure(source: str, name: str) -> str:
    matches = re.findall(r"^struct " + re.escape(name) + r"\s*\{.*?^\}(?:\s+__packed)?;", source, re.S | re.M)
    if len(matches) != 1:
        raise ValueError(f"structure absent/nonunique: {name}")
    return matches[0]


def define(source: str, name: str) -> str:
    matches = re.findall(r"^#define[ \t]+" + re.escape(name) + r"(?:[ \t]|\().*(?:\\\n[^\n]*)*", source, re.M)
    if len(matches) != 1:
        raise ValueError(f"macro absent/nonunique: {name}")
    return matches[0]


def excerpt(record: dict, label: str, text: str) -> dict:
    if record["text"].count(text) != 1:
        raise ValueError(f"excerpt absent/nonunique: {record['path']}:{label}")
    start = record["text"][:record["text"].index(text)].count("\n") + 1
    return {"label": label, "revision": record["revision"], "path": record["path"],
            "git_blob": record["git_blob"], "source_sha256": record["source_sha256"],
            "excerpt_sha256": sha(text.encode()), "start_line": start,
            "end_line": start + text.count("\n"), "text": text}


def read_sources(linux_dir: Path, revision: str, commands: list) -> dict:
    sources = {}
    for path in SOURCE_PATHS:
        argv = ["git", "show", f"{revision}:{path}"]
        result = subprocess.run(argv, cwd=linux_dir, capture_output=True, check=True)
        commands.append({"argv": argv, "cwd": str(linux_dir), "returncode": result.returncode,
                         "stdout_sha256": sha(result.stdout), "stderr": result.stderr.decode()})
        blob_argv = ["git", "rev-parse", f"{revision}:{path}"]
        blob = subprocess.run(blob_argv, cwd=linux_dir, capture_output=True, check=True)
        blob_text = blob.stdout.decode("ascii").strip()
        if not re.fullmatch(r"[0-9a-f]{40}", blob_text):
            raise ValueError("non-SHA Git blob stdout; WSL launcher stdout is never parsed")
        commands.append({"argv": blob_argv, "cwd": str(linux_dir), "returncode": blob.returncode,
                         "stdout": blob.stdout.decode("ascii"), "stderr": blob.stderr.decode()})
        sources[path] = {"revision": revision, "path": path, "git_blob": blob_text,
                         "source_sha256": sha(result.stdout), "text": result.stdout.decode("utf-8")}
    return sources


def build_variant(sources: dict, out: Path, label: str, revision: str) -> dict:
    excerpts = []
    texts = {}
    function_owners = {"hci_init4_req": CORE, "hci_req_add": REQUEST, "hci_req_add_ev": REQUEST,
                       "hci_prepare_cmd": REQUEST, "skb_put_data": SKB_HEADER}
    for name, owner in function_owners.items():
        texts[name] = function(sources[owner]["text"], name)
        excerpts.append(excerpt(sources[owner], name, texts[name]))
    macro_owners = {"HCI_PRIMARY": HEADER, "LMP_LE": HEADER, "HCI_LE_DATA_LEN_EXT": HEADER,
                    "LMP_SYNC_TRAIN": HEADER, "HCI_COMMAND_HDR_SIZE": HEADER, "HCI_COMMAND_PKT": HEADER,
                    "HCI_REQ_START": BT_HEADER, "bt_cb": BT_HEADER,
                    "hci_skb_pkt_type": BT_HEADER, "hci_skb_opcode": BT_HEADER,
                    "lmp_sync_train_capable": CORE_HEADER}
    constants = set(re.findall(r"\bHCI_[A-Z0-9_]+\b", texts["hci_init4_req"]))
    synthetic_flag_ids = {"HCI_QUIRK_BROKEN_STORED_LINK_KEY", "HCI_SSP_ENABLED"}
    for name in constants - synthetic_flag_ids:
        macro_owners.setdefault(name, HEADER)
    macros = []
    for name, owner in sorted(macro_owners.items()):
        text = define(sources[owner]["text"], name)
        macros.append(text)
        excerpts.append(excerpt(sources[owner], name, text))
    structs = []
    for name in ("hci_command_hdr", "hci_cp_delete_stored_link_key", "hci_cp_le_write_def_data_len", "hci_cp_le_set_default_phy"):
        text = structure(sources[HEADER]["text"], name)
        structs.append(text)
        excerpts.append(excerpt(sources[HEADER], name, text))
    req_struct = structure(sources[REQUEST_HEADER]["text"], "hci_request")
    excerpts.append(excerpt(sources[REQUEST_HEADER], "hci_request", req_struct))
    defaults = []
    allocation = function(sources[CORE]["text"], "hci_alloc_dev")
    for name in ("le_max_tx_len", "le_max_tx_time"):
        found = re.findall(r"^[ \t]*hdev->" + name + r"\s*=\s*0x[0-9a-fA-F]+;", allocation, re.M)
        if len(found) != 1:
            raise ValueError(f"historical default absent/nonunique: {name}")
        defaults.append(found[0].strip())
        excerpts.append(excerpt(sources[CORE], "historical_default_" + name, found[0]))
    c_text = C_TEMPLATE.replace("@VARIANT@", label)
    c_text = c_text.replace("@MACROS@", "\n".join(macros)).replace("@STRUCTS@", "\n".join(structs))
    c_text = c_text.replace("@REQUEST_STRUCT@", req_struct).replace("@DEFAULTS@", "\n".join(defaults))
    for name, text in texts.items():
        c_text = c_text.replace("@" + name.upper() + "@", text)
    if re.search(r"@[A-Z0-9_]+@", c_text):
        raise ValueError("unreplaced C template token")
    c_path = out / f"request_copy_{label}.c"
    c_path.write_text(c_text, encoding="utf-8", newline="\n")
    for name, text in texts.items():
        if c_text.count(text) != 1:
            raise ValueError(f"original text not unique in generated C: {name}")
    return {"variant": label, "revision": revision, "generated_c": c_path.name,
            "generated_c_sha256": sha(c_path.read_bytes()), "excerpts": excerpts,
            "source_files": [{k: v for k, v in record.items() if k != "text"} for record in sources.values()],
            "original_functions_preserved": list(function_owners), "synthetic_flag_ids": sorted(synthetic_flag_ids)}


C_TEMPLATE = r'''/* Original historical init4/request functions and skb_put_data.
 * Allocator, skb storage/cb, skb_put, and queue are explicit user-mode fixtures.
 * No req_run, synchronization, response, controller, or hardware execution. */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <assert.h>
#include <errno.h>
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint8_t __u8;
typedef uint16_t __le16;
#define __packed __attribute__((packed))
#define BIT(n) (1UL << (n)) /* fixture bit operation, only HCI_REQ_START is used */
#define GFP_ATOMIC 0 /* allocator ignores flags; not the real kernel GFP value */
@MACROS@
/* Synthetic IDs go only to false-returning configuration helpers. */
#define HCI_QUIRK_BROKEN_STORED_LINK_KEY 1
#define HCI_SSP_ENABLED 2
typedef struct { u8 b[6]; } bdaddr_t;
static const bdaddr_t fixture_zero_address={{0}};
#define BDADDR_ANY (&fixture_zero_address)
static inline void bacpy(bdaddr_t *dst,const bdaddr_t *src) { memcpy(dst,src,sizeof(*dst)); }
@STRUCTS@
_Static_assert(sizeof(struct hci_command_hdr)==3,"HCI header size");
_Static_assert(offsetof(struct hci_command_hdr,opcode)==0,"header opcode offset");
_Static_assert(offsetof(struct hci_command_hdr,plen)==2,"header length offset");
_Static_assert(sizeof(struct hci_cp_le_write_def_data_len)==4,"target payload size");
_Static_assert(offsetof(struct hci_cp_le_write_def_data_len,tx_len)==0,"payload length offset");
_Static_assert(offsetof(struct hci_cp_le_write_def_data_len,tx_time)==2,"payload time offset");
struct hci_dev {
    u8 dev_type,features[3][8],le_features[8],commands[64];
    unsigned long quirks;
    u16 le_max_tx_len,le_max_tx_time;
    u8 le_tx_def_phys,le_rx_def_phys;
    char name[16];
};
/* Minimal fields for original macros; no real kernel cb/storage layout claim. */
struct bt_skb_cb { u8 pkt_type; struct {u16 opcode;u8 req_flags,req_event;} hci; };
struct sk_buff { unsigned char storage[64]; unsigned int len,capacity; unsigned char cb[64] __attribute__((aligned(8))); };
struct sk_buff_head { struct sk_buff *tail; unsigned int count; };
@REQUEST_STRUCT@
struct trace {
    int allocation_fail;
    unsigned int add_attempt_count,allocation_call_count,allocation_failure_count;
    unsigned int header_reservation_count,payload_reservation_count,payload_copy_completed_count;
    unsigned int queue_mock_enqueue_count,error_log_count,helper_stub_calls;
    unsigned int current_opcode,attempt_plen,all_add_opcodes[16],all_add_count;
    unsigned int queued_length,queued_pkt_type,queued_opcode,queued_req_flags,queued_req_event;
    unsigned char copy_header[3],copy_payload[4],queue_header[3],queue_payload[4],copy_command[7],queue_command[7];
    struct sk_buff fixture_skb;
};
static struct trace *active;
static inline __le16 cpu_to_le16(u16 value) {
#if __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
    return __builtin_bswap16(value);
#else
    return value;
#endif
}
/* Instrument the unchanged original add_ev debug call before req.err guard.
 * The exact format plus the target opcode distinguish it from prepare debug. */
static void trace_debug(const char *format,...) {
    va_list ap;va_start(ap,format);
    if(strcmp(format,"%s opcode 0x%4.4x plen %d")==0) {
        (void)va_arg(ap,const char *);
        unsigned int opcode=(unsigned int)va_arg(ap,int);
        unsigned int plen=va_arg(ap,unsigned int);
        assert(active->all_add_count<16);
        active->all_add_opcodes[active->all_add_count++]=opcode;
        active->current_opcode=opcode;
        if(opcode==HCI_OP_LE_WRITE_DEF_DATA_LEN) {++active->add_attempt_count;active->attempt_plen=plen;}
    } else if(strcmp(format,"skb len %d")==0) {
        (void)va_arg(ap,unsigned int);
        if(active->current_opcode==HCI_OP_LE_WRITE_DEF_DATA_LEN) {
            /* This original prepare debug follows the completed original
             * skb_put_data memcpy. Snapshot bytes without modifying them. */
            assert(active->fixture_skb.len==7);
            memcpy(active->copy_header,active->fixture_skb.storage,3);
            memcpy(active->copy_payload,active->fixture_skb.storage+3,4);
            memcpy(active->copy_command,active->fixture_skb.storage,7);
            ++active->payload_copy_completed_count;
        }
    } else assert(0 && "unexpected original debug format");
    va_end(ap);
}
#define BT_DBG(...) trace_debug(__VA_ARGS__)
static void bt_dev_err(struct hci_dev *hdev,const char *format,u16 opcode) {
    (void)hdev;(void)format;
    if(opcode==HCI_OP_LE_WRITE_DEF_DATA_LEN) ++active->error_log_count;
}
/* Deterministic allocator fault injection. It does not call alloc_skb. */
static struct sk_buff *bt_skb_alloc(unsigned int len,int flags) {
    (void)flags;assert(active->current_opcode==HCI_OP_LE_WRITE_DEF_DATA_LEN);assert(len==7);
    ++active->allocation_call_count;
    if(active->allocation_fail) {++active->allocation_failure_count;return NULL;}
    memset(&active->fixture_skb,0,sizeof(active->fixture_skb));
    active->fixture_skb.capacity=len;
    return &active->fixture_skb;
}
/* Contiguous bounded storage reservation. Original skb_put_data below performs
 * the payload memcpy. These counters record reservation separately from copy. */
static void *skb_put(struct sk_buff *skb,unsigned int len) {
    assert(skb==&active->fixture_skb);assert(skb->len+len<=skb->capacity);
    if(skb->len==0) {assert(len==3);++active->header_reservation_count;}
    else {assert(skb->len==3 && len==4);++active->payload_reservation_count;}
    void *result=skb->storage+skb->len;skb->len+=len;return result;
}
@SKB_PUT_DATA@
static int skb_queue_empty(const struct sk_buff_head *queue) { return queue->count==0; }
/* Local queue mock records metadata and the exact header/payload bytes. */
static void skb_queue_tail(struct sk_buff_head *queue,struct sk_buff *skb) {
    assert(skb==&active->fixture_skb);assert(skb->len==7);
    assert(hci_skb_opcode(skb)==HCI_OP_LE_WRITE_DEF_DATA_LEN);
    queue->tail=skb;++queue->count;++active->queue_mock_enqueue_count;
    active->queued_length=skb->len;active->queued_pkt_type=hci_skb_pkt_type(skb);
    active->queued_opcode=hci_skb_opcode(skb);active->queued_req_flags=bt_cb(skb)->hci.req_flags;
    active->queued_req_event=bt_cb(skb)->hci.req_event;
    memcpy(active->queue_header,skb->storage,3);memcpy(active->queue_payload,skb->storage+3,4);
    memcpy(active->queue_command,skb->storage,7);
}
@HCI_PREPARE_CMD@
@HCI_REQ_ADD_EV@
@HCI_REQ_ADD@
/* Non-target capability/configuration helpers are false/no-op stubs. */
static int test_bit(unsigned int n,const unsigned long *p) { (void)n;(void)p;++active->helper_stub_calls;return 0; }
static int hci_dev_test_flag(struct hci_dev *hdev,unsigned int flag) { (void)hdev;(void)flag;++active->helper_stub_calls;return 0; }
static int bredr_sc_enabled(struct hci_dev *hdev) { (void)hdev;++active->helper_stub_calls;return 0; }
static void hci_set_event_mask_page_2(struct hci_request *req) { (void)req;++active->helper_stub_calls; }
@HCI_INIT4_REQ@
static void hex_or_null(const unsigned char *bytes,size_t len,int present) {
    if(!present) {printf("null");return;}
    putchar('"');for(size_t i=0;i<len;++i) printf("%02x",(unsigned int)bytes[i]);putchar('"');
}
static void emit(int req_err_initial,int allocation_fail,int init4_result,const struct hci_request *req,const struct hci_dev *hdev) {
    printf("{\"kind\":\"row\",\"variant\":\"@VARIANT@\",\"req_err_initial\":%d,\"allocation_configuration\":\"%s\",\"init4_return_value\":%d,\"req_err_after\":%d,\"primary\":true,\"lmp_le_capability\":true,\"data_length_extension\":true,\"host_values\":[%u,%u],\"target_opcode\":%u,\"attempt_plen\":%u,\"add_attempt_count\":%u,\"allocation_call_count\":%u,\"allocation_failure_count\":%u,\"header_reservation_count\":%u,\"payload_reservation_count\":%u,\"payload_copy_completed_count\":%u,\"queue_mock_enqueue_count\":%u,\"mock_queue_length\":%u,\"error_log_count\":%u,\"helper_stub_calls\":%u,\"all_add_attempt_opcodes\":[",
        req_err_initial,allocation_fail?"failure":"success",init4_result,req->err,hdev->le_max_tx_len,hdev->le_max_tx_time,HCI_OP_LE_WRITE_DEF_DATA_LEN,active->attempt_plen,active->add_attempt_count,active->allocation_call_count,active->allocation_failure_count,active->header_reservation_count,active->payload_reservation_count,active->payload_copy_completed_count,active->queue_mock_enqueue_count,req->cmd_q.count,active->error_log_count,active->helper_stub_calls);
    for(unsigned int i=0;i<active->all_add_count;++i) printf("%s%u",i?",":"",active->all_add_opcodes[i]);
    printf("],\"copy_header_hex\":");hex_or_null(active->copy_header,3,active->payload_copy_completed_count);
    printf(",\"copy_payload_hex\":");hex_or_null(active->copy_payload,4,active->payload_copy_completed_count);
    printf(",\"copy_command_hex\":");hex_or_null(active->copy_command,7,active->payload_copy_completed_count);
    printf(",\"queue_mock_header_hex\":");hex_or_null(active->queue_header,3,active->queue_mock_enqueue_count);
    printf(",\"queue_mock_payload_hex\":");hex_or_null(active->queue_payload,4,active->queue_mock_enqueue_count);
    printf(",\"queue_mock_command_hex\":");hex_or_null(active->queue_command,7,active->queue_mock_enqueue_count);
    printf(",\"queued_length\":%u,\"queued_packet_type\":%u,\"queued_opcode\":%u,\"queued_req_flags\":%u,\"queued_req_event\":%u,\"req_run_executed\":false}\n",active->queued_length,active->queued_pkt_type,active->queued_opcode,active->queued_req_flags,active->queued_req_event);
}
int main(void) {
    u16 marker=0x0102;unsigned char marker_bytes[2];memcpy(marker_bytes,&marker,2);
    const char *order=marker_bytes[0]==1 && marker_bytes[1]==2?"big":marker_bytes[0]==2 && marker_bytes[1]==1?"little":"unknown";
    assert(strcmp(order,"unknown")!=0);
#if __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
    assert(strcmp(order,"big")==0);
#else
    assert(strcmp(order,"little")==0);
#endif
    printf("{\"kind\":\"meta\",\"variant\":\"@VARIANT@\",\"actual_host_order\":\"%s\",\"payload_size\":%zu,\"header_size\":%zu,\"target_opcode\":%u}\n",order,sizeof(struct hci_cp_le_write_def_data_len),sizeof(struct hci_command_hdr),HCI_OP_LE_WRITE_DEF_DATA_LEN);
    for(int error=0;error<=1;++error)
        for(int failure=0;failure<=1;++failure) {
            struct trace trace={.allocation_fail=failure};active=&trace;
            struct hci_dev device={0};struct hci_dev *hdev=&device;
            hdev->dev_type=HCI_PRIMARY;hdev->features[0][4]=LMP_LE;hdev->le_features[0]=HCI_LE_DATA_LEN_EXT;
@DEFAULTS@
            int initial_error=error?-EIO:0;
            struct hci_request request={.hdev=hdev,.err=initial_error};
            int result=hci_init4_req(&request,0);
            emit(initial_error,failure,result,&request,hdev);
        }
    return 0;
}
'''


def analyze(stdout: str, variant: str, target: str, order: str) -> dict:
    parsed = [json.loads(line) for line in stdout.splitlines()]
    meta, rows = parsed[0], parsed[1:]
    assert meta == {"kind": "meta", "variant": variant, "actual_host_order": order,
                    "payload_size": 4, "header_size": 3, "target_opcode": 0x2024}
    assert len(rows) == 4
    seen = set()
    for row in rows:
        key = (row["req_err_initial"], row["allocation_configuration"])
        assert key in set(itertools.product((0, -5), ("success", "failure"))) and key not in seen
        seen.add(key)
        error, allocation = key
        allocated = error == 0
        copied = allocated and allocation == "success"
        allocation_failed = allocated and allocation == "failure"
        assert row["variant"] == variant and row["target_opcode"] == 0x2024 and row["attempt_plen"] == 4
        assert row["primary"] and row["lmp_le_capability"] and row["data_length_extension"]
        assert row["host_values"] == [27, 328] and row["all_add_attempt_opcodes"] == [0x2024]
        assert row["init4_return_value"] == 0 and row["req_err_after"] == (error or (-12 if allocation_failed else 0))
        assert row["add_attempt_count"] == 1
        assert row["allocation_call_count"] == int(allocated)
        assert row["allocation_failure_count"] == row["error_log_count"] == int(allocation_failed)
        for name in ("header_reservation_count", "payload_reservation_count", "payload_copy_completed_count",
                     "queue_mock_enqueue_count", "mock_queue_length"):
            assert row[name] == int(copied)
        assert row["helper_stub_calls"] == 1 and row["req_run_executed"] is False
        row["target"] = target
        row["row_id"] = f"{variant}:{target}:err{error}:alloc_{allocation}"
        row["observation"] = "after_original_skb_put_data_copy_and_local_queue_mock" if copied else "no_payload_copy"
        row["source_expected_payload_hex"] = "1b004801" if copied else None
        row["payload_matches_source_contract"] = None
        row["header_matches_source_contract"] = None
        row["byte_verdict"] = None
        row["byte_check_execution"] = "not_executed"
        row["rejection_boundary"] = "req.err guard" if error else "allocator failure" if allocation_failed else None
        if copied:
            expected = (27).to_bytes(2, order if variant == "parent" else "little") + (328).to_bytes(2, order if variant == "parent" else "little")
            assert row["copy_payload_hex"] == row["queue_mock_payload_hex"] == expected.hex()
            assert row["copy_header_hex"] == row["queue_mock_header_hex"] == "242004"
            assert row["copy_command_hex"] == row["queue_mock_command_hex"] == "242004" + expected.hex()
            assert row["queued_length"] == 7 and row["queued_packet_type"] == 1 and row["queued_opcode"] == 0x2024
            assert row["queued_req_flags"] == 1 and row["queued_req_event"] == 0
            row["payload_matches_source_contract"] = expected.hex() == "1b004801"
            row["header_matches_source_contract"] = True
            row["byte_verdict"] = "conditional_numeric_match" if row["payload_matches_source_contract"] else "conditional_representation_mismatch"
            row["byte_check_execution"] = "executed_on_completed_copy"
        else:
            assert all(row[name] is None for name in ("copy_header_hex", "copy_payload_hex", "copy_command_hex", "queue_mock_header_hex", "queue_mock_payload_hex", "queue_mock_command_hex"))
            assert all(row[name] == 0 for name in ("queued_length", "queued_packet_type", "queued_opcode", "queued_req_flags", "queued_req_event"))
        row["limits"] = ["user-mode projection with deterministic allocator/storage/queue mocks",
                         "no req_run, synchronous chain, completion response, controller or hardware execution"]
    return {"metadata": meta, "rows": rows, "summary": {"rows": 4, "add_attempt_rows": 4,
            "allocation_call_rows": 2, "payload_copy_rows": 1, "queue_mock_rows": 1,
            "no_copy_rows": 3, "null_byte_verdict_rows": 3,
            "payload_mismatch_rows": sum(r["payload_matches_source_contract"] is False for r in rows)}}


def prepare(linux_dir: Path, out: Path) -> None:
    commands = []
    runner_sha = sha(Path(__file__).read_bytes())
    variants = {label: build_variant(read_sources(linux_dir, revision, commands), out, label, revision)
                for label, revision in VARIANTS.items()}
    write_json(out / "source_evidence.json", {"schema": "original-hci-request-copy-source-v1",
        "source_repository": str(linux_dir), "variants": variants, "preparation_commands": commands,
        "runner_sha256": runner_sha,
        "saved_authority_crosscheck": {"path": "../contract_authority_20261001/source_authority/raw/net/bluetooth/hci_request.c",
            "sha256": sha((out.parent / "contract_authority_20261001/source_authority/raw/net/bluetooth/hci_request.c").read_bytes()),
            "same_as_parent_git_source": sha((out.parent / "contract_authority_20261001/source_authority/raw/net/bluetooth/hci_request.c").read_bytes()) == next(r["source_sha256"] for r in variants["parent"]["source_files"] if r["path"] == REQUEST)},
        "preservation": "Each of five complete function texts appears verbatim once in generated C, including original skb_put_data memcpy.",
        "stub_boundary": "BT_DBG instrumentation; deterministic bt_skb_alloc; bounded skb_put/storage/cb; queue helpers; minimal hci_dev; false/no-op non-target helpers; no kernel execution."})
    assert runner_sha == sha(Path(__file__).read_bytes())
    print(json.dumps({"prepared_only": True, "variants": list(variants), "runner_sha256": runner_sha,
                      "generated_c_sha256": {v: x["generated_c_sha256"] for v, x in variants.items()}}))


def execute(linux_dir: Path, out: Path, protocol: Path, expected: Path) -> None:
    source_path = out / "source_evidence.json"
    evidence = json.loads(source_path.read_text(encoding="utf-8"))
    runner_before = sha(Path(__file__).read_bytes())
    c_before = {v: sha((out / x["generated_c"]).read_bytes()) for v, x in evidence["variants"].items()}
    assert evidence["runner_sha256"] == runner_before
    assert c_before == {v: x["generated_c_sha256"] for v, x in evidence["variants"].items()}
    bindings_before = {"source_evidence": sha(source_path.read_bytes()), "protocol_pre": sha(protocol.read_bytes()),
                       "independent_expected_pre": sha(expected.read_bytes())}
    commands = []
    def run(argv: list[str]) -> subprocess.CompletedProcess:
        result = subprocess.run(argv, capture_output=True, text=True)
        commands.append({"argv": argv, "cwd": str(Path.cwd()), "returncode": result.returncode,
                         "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode:
            raise RuntimeError(f"command failed: {argv}: {result.stderr}")
        return result
    versions = {name: run([name, "--version"]).stdout.splitlines()[0]
                for name in ("gcc", "s390x-linux-gnu-gcc", "qemu-s390x")}
    source_checks = []
    for variant in evidence["variants"].values():
        for source in variant["source_files"]:
            argv = ["git", "show", f"{source['revision']}:{source['path']}"]
            result = subprocess.run(argv, cwd=linux_dir, capture_output=True, check=True)
            assert sha(result.stdout) == source["source_sha256"]
            source_checks.append({"argv": argv, "cwd": str(linux_dir), "returncode": result.returncode,
                                  "stdout_sha256": sha(result.stdout), "stderr": result.stderr.decode()})
    targets = {}
    binaries = []
    with tempfile.TemporaryDirectory(prefix="hci-request-copy-") as temp_name:
        for target, compiler, launcher, order in (("x86_64", "gcc", [], "little"),
                ("s390x", "s390x-linux-gnu-gcc", ["qemu-s390x"], "big")):
            targets[target] = {}
            for variant in VARIANTS:
                binary = Path(temp_name) / f"{target}-{variant}"
                c_path = out / evidence["variants"][variant]["generated_c"]
                run([compiler, "-static", "-std=gnu11", "-O2", "-Wall", "-Wextra", "-Werror",
                     "-Wno-unused-parameter", str(c_path), "-o", str(binary)])
                binary_sha = sha(binary.read_bytes())
                result = analyze(run(launcher + [str(binary)]).stdout, variant, target, order)
                result["executable_sha256"] = binary_sha
                binaries.append({"temporary_path": str(binary), "sha256": binary_sha,
                                 "target": target, "variant": variant})
                targets[target][variant] = result
    assert all(not Path(b["temporary_path"]).exists() for b in binaries)
    runner_after = sha(Path(__file__).read_bytes())
    c_after = {v: sha((out / x["generated_c"]).read_bytes()) for v, x in evidence["variants"].items()}
    bindings_after = {"source_evidence": sha(source_path.read_bytes()), "protocol_pre": sha(protocol.read_bytes()),
                      "independent_expected_pre": sha(expected.read_bytes())}
    assert runner_before == runner_after and c_before == c_after and bindings_before == bindings_after
    all_rows = [r for variants in targets.values() for result in variants.values() for r in result["rows"]]
    assert len(all_rows) == 16 and len({r["row_id"] for r in all_rows}) == 16
    report = {"schema": "original-hci-request-copy-boundary-v1", "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Already read development example, original historical functions in a bounded user-mode fixture.",
        "matrix": {"versions": VARIANTS, "targets": ["x86_64", "s390x"], "req_err_initial": [0, -5],
                   "allocation_configuration": ["success", "failure"], "total_rows": 16},
        "fixed_capabilities": {"primary": True, "LMP_LE": True, "DATA_LEN_EXT": True,
            "commands": "all zero", "other feature bits": "all zero", "all configuration helpers": False},
        "original_functions_preserved": list(ORIGINAL_FUNCTIONS),
        "observation_point": {"target_opcode": "HCI_OP_LE_WRITE_DEF_DATA_LEN (0x2024)",
            "host_values": [27, 328], "packed_payload_size": 4, "packed_header_size": 3,
            "add_attempt": "BT_DBG macro observes unchanged original add_ev entry format and exact opcode before req.err guard",
            "allocation_call": "deterministic bt_skb_alloc stub called only by original prepare",
            "payload_reservation": "skb_put stub called by original skb_put_data; distinct from completed copy",
            "payload_copy_completed": "original prepare BT_DBG after return from original skb_put_data memcpy; exact bytes snapshot",
            "queue_mock": "original add_ev calls local skb_queue_tail mock after request metadata assignments",
            "byte_verdict": "Python after process exits, only rows with completed original payload copy; null otherwise"},
        "stub_assumptions": ["Direct invocation of original hci_init4_req with fixed primary/LMP_LE/DLE; no outer initialization entry or sync chain",
            "Minimal hci_dev fields and fixed historical defaults 27/328; no init3 responses or feature discovery",
            "Original hci_request struct and HCI packed structs/macros preserved, but sk_buff_head, skb storage and bt_skb_cb are minimal fixtures",
            "bt_skb_alloc returns a zeroed bounded local buffer or NULL; GFP_ATOMIC is a synthetic ignored token",
            "skb_put reserves contiguous fixture storage with bounds assertions; original skb_put_data performs memcpy",
            "skb_queue_empty and skb_queue_tail are local queue mocks without locks/workqueues/transport",
            "BT_DBG instruments add attempt and post-copy observation; bt_dev_err counts allocator failure logs",
            "Non-target test_bit/hci_dev_test_flag/bredr_sc_enabled return false, hci_set_event_mask_page_2 is no-op, bacpy is a local memcpy helper",
            "Synthetic quirk/configuration IDs are only passed to false-returning helpers and are not real kernel bit indices"],
        "commands": commands, "source_integrity_checks": source_checks, "tool_versions": versions, "targets": targets,
        "summary": {"total_rows": 16, "add_attempt_rows": 16, "allocation_call_rows": 8,
            "payload_copy_rows": 4, "queue_mock_rows": 4, "null_byte_verdict_rows": 12,
            "payload_mismatch_rows": sum(r["payload_matches_source_contract"] is False for r in all_rows)},
        "pre_run_bindings": {"protocol_pre_path": str(protocol), "independent_expected_pre_path": str(expected), **bindings_before},
        "run_integrity": {"runner_sha_before": runner_before, "runner_sha_after": runner_after,
            "generated_c_sha_before": c_before, "generated_c_sha_after": c_after,
            "artifact_bindings_before": bindings_before, "artifact_bindings_after": bindings_after},
        "temporary_executables": {"records": binaries, "all_removed_after_success": True},
        "limits": ["Not historical kernel execution: allocator, storage/helper state and queues remain local mocks",
            "No req_run, sync chain, completion-response reader, controller transport or hardware execution",
            "Only fixed primary+LMP_LE+DLE fixture and the four error/allocation combinations per version/architecture",
            "No independent holdout, new Linux case, hardware reachability proof or detector accuracy estimate",
            "No-copy rows have null header/payload verdicts; allocation configuration is not allocation evidence when req.err short-circuits"]}
    write_json(out / "results.json", report)
    print(json.dumps(report["summary"]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linux-dir", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--expected", type=Path)
    args = parser.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    protocol = args.protocol or out / "protocol_pre.md"
    expected = args.expected or out / "source_review/expected_matrix_pre_harness.json"
    if args.prepare_only:
        prepare(args.linux_dir, out)
    else:
        execute(args.linux_dir, out, protocol.resolve(), expected.resolve())


if __name__ == "__main__":
    main()
