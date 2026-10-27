"""Generate and run a bounded representation-domain matrix with a separate oracle.

The 32-bit same-host/host and little/little pairs project the already reviewed
Bluetooth coredump chain. Other widths/domains are synthetic mechanism controls.
There are no new cases, kernel executions, models, or discovered consumers here.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


WIDTHS = (16, 32, 64)
DOMAINS = ("host", "le", "be")
OLD = "25c150ac103a4ebeed0319994c742a90634ddf18"
FIX = "0ab905c3be8c2be368821dd2bd1f8d126064d993"
SOURCE = "net/bluetooth/coredump.c"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def input_values(width: int) -> tuple[int, int, int]:
    if width not in WIDTHS:
        raise ValueError("only 16/32/64-bit projections are supported")
    nbytes = width // 8
    # Width-generic non-palindromic byte patterns, not per-case expected bytes.
    return (int.from_bytes(bytes(range(1, nbytes + 1)), "big"),
            int.from_bytes(bytes(0xA0 + i for i in range(nbytes)), "big"), 0)


def physical_order(domain: str, actual_host_order: str) -> str:
    if domain == "host":
        return actual_host_order
    if domain not in ("le", "be"):
        raise ValueError("unsupported representation domain")
    return {"le": "little", "be": "big"}[domain]


def oracle(width: int, source_domain: str, read_domain: str,
           value: int, actual_host_order: str, actual_payload: bytes) -> dict:
    """Separate Python byte oracle, not an invocation of C encode/decode.

    Check source bytes against the declared write contract AND independently
    interpret the actual bytes according to the declared reader contract.
    """
    nbytes = width // 8
    write_order = physical_order(source_domain, actual_host_order)
    read_order = physical_order(read_domain, actual_host_order)
    expected_payload = value.to_bytes(nbytes, write_order)
    decoded_actual_bytes = int.from_bytes(actual_payload, read_order)
    expected_read_value = int.from_bytes(expected_payload, read_order)
    return {"write_order": write_order, "read_order": read_order,
            "expected_payload_hex": expected_payload.hex(),
            "payload_matches_write_contract": actual_payload == expected_payload,
            "oracle_decode_actual_payload": decoded_actual_bytes,
            "expected_read_value": expected_read_value,
            "expected_numeric_roundtrip": expected_read_value == value}


C_TEMPLATE = r'''/* Generated bounded integer/byte projection. No kernel translation unit.
 * memcpy models host scalar representation without alignment/aliasing claims.
 * Declared domains are checked by a separately implemented Python oracle. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <inttypes.h>
#include <assert.h>
_Static_assert(sizeof(uint16_t)==2 && sizeof(uint32_t)==4 && sizeof(uint64_t)==8,
               "supported integer widths");
enum domain { HOST, LE, BE };
static const char *names[] = {"host", "le", "be"};
static void write_value(unsigned width, enum domain d, uint64_t value, unsigned char *p) {
    const unsigned n=width/8;
    assert(width==16 || width==32 || width==64);
    if (d==HOST) {
        if (width==16) { uint16_t v=(uint16_t)value; memcpy(p,&v,2); }
        else if (width==32) { uint32_t v=(uint32_t)value; memcpy(p,&v,4); }
        else { uint64_t v=value; memcpy(p,&v,8); }
        return;
    }
    for (unsigned i=0;i<n;++i) {
        unsigned shift=(d==LE?i:n-1-i)*8;
        p[i]=(unsigned char)(value>>shift);
    }
}
static uint64_t read_value(unsigned width, enum domain d, const unsigned char *p) {
    const unsigned n=width/8;
    assert(width==16 || width==32 || width==64);
    if (d==HOST) {
        if (width==16) { uint16_t v; memcpy(&v,p,2); return v; }
        if (width==32) { uint32_t v; memcpy(&v,p,4); return v; }
        uint64_t v; memcpy(&v,p,8); return v;
    }
    uint64_t value=0;
    for (unsigned i=0;i<n;++i) {
        unsigned shift=(d==LE?i:n-1-i)*8;
        value |= (uint64_t)p[i]<<shift;
    }
    return value;
}
static void emit(const char *tag, unsigned width, enum domain declared_write,
                 enum domain declared_read, enum domain actual_write,
                 enum domain actual_read, uint64_t value) {
    unsigned char payload[8]={0};
    write_value(width,actual_write,value,payload);
    uint64_t actual=read_value(width,actual_read,payload);
    printf("%s,%u,%s,%s,%" PRIu64 ",%" PRIu64 ",",tag,width,
           names[declared_write],names[declared_read],value,actual);
    for (unsigned i=0;i<width/8;++i) printf("%02x",(unsigned)payload[i]);
    putchar('\n');
}
int main(void) {
    uint16_t marker=0x0102; unsigned char b[2]; memcpy(b,&marker,2);
    const char *actual_host;
    if (b[0]==2 && b[1]==1) actual_host="little";
    else if(b[0]==1 && b[1]==2) actual_host="big";
    else return 2;
#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
    assert(strcmp(actual_host,"little")==0);
#elif __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
    assert(strcmp(actual_host,"big")==0);
#else
    return 3;
#endif
    printf("META,%s,%zu,%zu,%zu\n",actual_host,sizeof(uint16_t),sizeof(uint32_t),sizeof(uint64_t));
    struct sample { unsigned width; uint64_t value; };
    const struct sample samples[] = {
@INPUTS@
    };
    for(size_t i=0;i<sizeof(samples)/sizeof(samples[0]);++i)
        for(enum domain w=HOST;w<=BE;++w)
            for(enum domain r=HOST;r<=BE;++r)
                emit("ROW",samples[i].width,w,r,w,r,samples[i].value);
    /* Deliberate common-mode bug: declared BE/BE but both implementations LE.
     * Numeric roundtrip still succeeds; independent byte/decode oracles reject. */
    emit("MUT",32,BE,BE,LE,LE,UINT64_C(@MUTATION_VALUE@));
    return 0;
}
'''


def generate_c() -> str:
    inputs = []
    for width in WIDTHS:
        for value in input_values(width):
            inputs.append(f"        {{{width}, UINT64_C({value})}},")
    return C_TEMPLATE.replace("@INPUTS@", "\n".join(inputs)).replace(
        "@MUTATION_VALUE@", str(input_values(32)[0]))


def analyze_output(stdout: str, expected_endian: str) -> dict:
    lines = [line.split(",") for line in stdout.splitlines()]
    if lines[0] != ["META", expected_endian, "2", "4", "8"]:
        raise ValueError("runtime bytes/compiler ABI do not match the intended target")
    host_order = lines[0][1]
    if len(lines) != 83:
        raise ValueError("matrix has missing/extra output rows")
    rows, mutations = [], []
    expected_keys = set(itertools.product(WIDTHS, DOMAINS, DOMAINS))
    expected_keys = {(w, producer, reader, v) for w, producer, reader in expected_keys for v in input_values(w)}
    seen = set()
    for parts in lines[1:]:
        tag, width_text, producer, reader, input_text, result_text, raw_hex = parts
        width, value, result = int(width_text), int(input_text), int(result_text)
        payload = bytes.fromhex(raw_hex)
        if len(payload) != width // 8:
            raise ValueError("payload width mismatch")
        check = oracle(width, producer, reader, value, host_order, payload)
        output = {"width": width, "producer_domain": producer, "reader_domain": reader,
            "input": value, "observed_value": result, "payload_hex": raw_hex,
            "numeric_roundtrip": result == value,
            "reader_matches_actual_bytes_oracle": result == check["oracle_decode_actual_payload"], **check,
            "evidence_level": "known-source-linked numeric projection" if width == 32 and producer == reader and producer in ("host", "le") else "synthetic conditional numeric projection",
            "input_path_scope": "zero arithmetic control; the known coredump consumer rejects zero, so successful init is not inferred" if value == 0 else "numeric input only; kernel allocation and successful init are not inferred",
            "unproved": ["actual kernel/configuration reachability", "alignment and aliasing of original pointer access",
                         "queue ordering and lifetime", "external protocol requirement"]}
        if tag == "ROW":
            key = (width, producer, reader, value)
            if key not in expected_keys or key in seen:
                raise ValueError("matrix keys changed or duplicated")
            seen.add(key)
            assert output["payload_matches_write_contract"]
            assert output["reader_matches_actual_bytes_oracle"]
            assert result == check["expected_read_value"]
            assert output["numeric_roundtrip"] == check["expected_numeric_roundtrip"]
            if producer == reader or value == 0:
                assert output["numeric_roundtrip"]
            elif check["write_order"] != check["read_order"]:
                assert not output["numeric_roundtrip"]
            else:
                assert output["numeric_roundtrip"]
            rows.append(output)
        elif tag == "MUT":
            assert width == 32 and producer == reader == "be" and value == input_values(32)[0]
            assert output["numeric_roundtrip"]
            assert not output["payload_matches_write_contract"]
            assert not output["reader_matches_actual_bytes_oracle"]
            output["evidence_level"] = "synthetic oracle mutation control"
            output["mutation"] = "declared BE/BE; encoder and decoder both replaced by LE"
            mutations.append(output)
        else:
            raise ValueError("unknown output tag")
    assert seen == expected_keys and len(mutations) == 1
    nonzero = [r for r in rows if r["input"] != 0]
    zero = [r for r in rows if r["input"] == 0]
    return {"actual_host_byte_order": host_order, "integer_bytes": {"16": 2, "32": 4, "64": 8},
        "rows": rows, "mutations": mutations,
        "summary": {"matrix_rows": len(rows), "nonzero_rows": len(nonzero), "zero_rows": len(zero),
            "nonzero_numeric_mismatch_rows": sum(not r["numeric_roundtrip"] for r in nonzero),
            "same_named_domain_nonzero_mismatch_rows": sum(not r["numeric_roundtrip"] for r in nonzero if r["producer_domain"] == r["reader_domain"]),
            "zero_numeric_mismatch_rows": sum(not r["numeric_roundtrip"] for r in zero),
            "payload_oracle_mismatches_regular_matrix": sum(not r["payload_matches_write_contract"] for r in rows),
            "reader_oracle_mismatches_regular_matrix": sum(not r["reader_matches_actual_bytes_oracle"] for r in rows),
            "deliberate_mutation_rejected_by_independent_oracle": True,
            "interpretation": "Rows are projections/controls, not defect counts or independent cases."}}


def save_source_card(linux_dir: Path, output: Path, previous_evidence: Path, commands: list) -> dict:
    previous = json.loads(previous_evidence.read_text(encoding="utf-8"))
    prior_results = json.loads(previous_evidence.with_name("results.json").read_text(encoding="utf-8"))
    if digest(previous_evidence.read_bytes()) != prior_results["source_evidence_sha256"]:
        raise ValueError("prior reviewed evidence hash does not match its results")
    selected = [r for r in previous["excerpts"] if r["label"].startswith("cd_")]
    if len(selected) != 5:
        raise ValueError("expected old producer/reader/queue and fixed producer/reader excerpts")
    versions = {}
    for revision in (OLD, FIX):
        argv = ["git", "show", f"{revision}:{SOURCE}"]
        result = subprocess.run(argv, cwd=linux_dir, capture_output=True, check=True)
        raw = result.stdout
        commands.append({"argv": argv, "cwd": str(linux_dir), "returncode": result.returncode,
            "stdout_sha256": digest(raw), "stdout_saved_as": "exact reviewed excerpts only in source_card.json",
            "stderr": result.stderr.decode()})
        blob_args = ["git", "rev-parse", f"{revision}:{SOURCE}"]
        blob = subprocess.run(blob_args, cwd=linux_dir, capture_output=True, text=True, check=True)
        commands.append({"argv": blob_args, "cwd": str(linux_dir), "returncode": blob.returncode,
                         "stdout": blob.stdout, "stderr": blob.stderr})
        versions[revision] = {"source_sha256": digest(raw), "blob": blob.stdout.strip()}
        source = raw.decode()
        for record in selected:
            if record["revision"] != revision:
                continue
            assert record["source_sha256"] == digest(raw) and record["blob"] == blob.stdout.strip()
            assert source.count(record["text"]) == 1
            assert source[:source.index(record["text"])].count("\n") + 1 == record["start_line"]
    card = {"schema": "paired-internal-domain-authority-v1", "case_fix": FIX, "case_parent": OLD,
        "scope": "Already read development example, not a new independent sample",
        "prior_evidence_path": str(previous_evidence), "prior_evidence_sha256": digest(previous_evidence.read_bytes()),
        "historical_sources_verified": versions, "source_excerpts": selected,
        "authority": {"internal": "Same-version actual reader and local producer/queue path determine interpretation for this internal payload.",
            "old_pair": "32-bit host representation written via skb_put_data and read by host u32 dereference, on the same host.",
            "fixed_pair": "Explicit little-endian put_unaligned_le32/get_unaligned_le32 pair.",
            "external": "No externally required fixed payload order has been bound; do not require LE automatically.",
            "when_conflicting": "Mark unresolved if version/mode/same-host reader cannot be established or an independently bound external contract conflicts."},
        "synthetic_dimensions": ["16-bit and 64-bit widths", "big-endian explicit representation", "all mixed domains except single-end changes of known 32-bit pair"],
        "limits": ["No real sk_buff, workqueue, kernel or device execution", "No alignment/aliasing/lifetime proof",
            "Zero is an arithmetic control only; both historical coredump consumers reject zero before successful preparation",
            "Historical case remains outside confirmed cross-architecture core without additional failure/contract evidence"]}
    path = output / "source_card.json"
    path.write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"source_card_sha256": digest(path.read_bytes())}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linux-dir", type=Path, required=True)
    parser.add_argument("--source-evidence", type=Path, default=Path(__file__).resolve().parents[2] /
        "structured_payload_20261001/compiler_probe/source_evidence.json")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    commands = []
    source_card = save_source_card(args.linux_dir, output, args.source_evidence.resolve(), commands)
    source_path = output / "domain_matrix.c"
    source_path.write_text(generate_c(), encoding="utf-8")

    def run(argv: list[str]) -> subprocess.CompletedProcess:
        process = subprocess.run(argv, capture_output=True, text=True)
        commands.append({"argv": argv, "returncode": process.returncode,
                         "stdout": process.stdout, "stderr": process.stderr})
        if process.returncode != 0:
            raise RuntimeError(f"command failed: {argv}: {process.stderr}")
        return process

    versions = {name: run([name, "--version"]).stdout.splitlines()[0]
                for name in ("gcc", "s390x-linux-gnu-gcc", "qemu-s390x")}
    targets = {}
    with tempfile.TemporaryDirectory(prefix="paired-domain-") as temp_name:
        for label, compiler, launch, expected_order in (("x86_64", "gcc", [], "little"),
                ("s390x", "s390x-linux-gnu-gcc", ["qemu-s390x"], "big")):
            binary = Path(temp_name) / label
            run([compiler, "-static", "-std=gnu11", "-O2", "-Wall", "-Wextra", "-Werror",
                 str(source_path), "-o", str(binary)])
            execution = run(launch + [str(binary)])
            targets[label] = analyze_output(execution.stdout, expected_order)
            targets[label]["executable_sha256"] = digest(binary.read_bytes())
    report = {"schema": "paired-domain-independent-oracle-matrix-v1", "created_utc": datetime.now(timezone.utc).isoformat(),
        "input_config": {"widths": WIDTHS, "domains": DOMAINS, "values": {str(w): input_values(w) for w in WIDTHS}},
        "scope": "Bounded numeric projection; known 32-bit coredump pair plus synthetic matrix; not independent held-out defects.",
        "comparison": "decode_C(payload_P_original(v)) vs v and independent actual-byte/read-domain checks; never just reference encode/decode roundtrip.",
        "tool_versions": versions, "commands": commands, "targets": targets,
        "runner_sha256": digest(Path(__file__).read_bytes()), "generated_c_sha256": digest(source_path.read_bytes()), **source_card}
    (output / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v["summary"] for k, v in targets.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
