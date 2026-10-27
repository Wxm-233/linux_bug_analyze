"""Replay eight already-read interface revisions using saved, hash-bound bytes."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(BASE))
import interface_fact_extractor as extract


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def source(manifest_path, revision, path):
    entries = read_json(BASE / manifest_path)
    entries = [e for e in entries if e.get("revision") == revision and
               e.get("source_path", e.get("path")) == path and e.get("available", True)]
    if len(entries) != 1:
        raise ValueError("source record absent/ambiguous: " + path)
    e = entries[0]
    # Manifest paths use three historical conventions; no filesystem escape.
    base = (BASE / manifest_path).parent
    if "manual_review" in manifest_path:
        base = BASE / "bounded_interface_holdout_20261003"
    saved = (base / e["saved_path"].replace("\\", "/")).resolve()
    saved.relative_to(BASE.resolve())
    raw = saved.read_bytes()
    if sha(raw) != e["sha256"]:
        raise ValueError("saved source digest mismatch: " + str(saved))
    blob = e.get("blob", e.get("blob_oid", e.get("blob_sha1")))
    expected_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if blob != expected_blob:
        raise ValueError("Git blob mismatch")
    return extract.Source(path, revision, saved.relative_to(BASE).as_posix(), blob, raw)


def manual(path, limits, applicability):
    raw = (BASE / path).read_bytes()
    return dict(kind="existing_human_review", path=path, sha256=sha(raw),
                semantic_status="reviewed_claims_not_machine_certified",
                applicability=applicability, unresolved=limits)


def guarded(fn, *args):
    try:
        return fn(*args)
    except (ValueError, SyntaxError) as exc:
        return extract.fail(str(exc))


def run():
    observations = []
    inventory = {}

    def load(manifest, rev, path):
        s = source(manifest, rev, path)
        inventory[s.saved_path] = dict(path=s.saved_path, revision=rev,
            source_path=path, sha256=sha(s.raw), blob_sha1=s.blob)
        return s

    old = "cross_subsystem_facts_20261003/"
    previous = "bounded_interface_holdout_20261003/"
    versions = {
        "ocfs2": ["c9dff86eb78a4b6b02b1e407993c946ccaf9bfb4^", "c9dff86eb78a4b6b02b1e407993c946ccaf9bfb4"],
        "pwm": ["d7b4408374b69dbc246c59c29e3077920b9f03eb", "09f688f0718f57f9cf68ee1aa94490f641e759ba"],
        "smb": ["fac04efc5c793dccbd07e2d59af9f90b7fc0dca4", "6d44a780635b9b3fb6e20f366ee7750a9adfa884"],
        "ath12k": ["ea58aae8458480d6391c404e62f1a4b30462b9c3", "1cfa6d4e5bd9bfb15d165d8d843163363929ba1b"],
    }
    for case, revisions in versions.items():
        for label, revision in zip(("parent", "fixed"), revisions):
            record = dict(case=case, label=label, revision=revision,
                input_role="already_read_development_query", new_confirmed_case=False,
                actual_kernel_device_execution=False)
            if case == "ocfs2":
                manifest = old + "ocfs2/source_manifest.json"
                s = load(manifest, revision, "fs/ocfs2/inode.c")
                h = load(manifest, revision, "fs/ocfs2/ocfs2_fs.h")
                args = (s, h, "ocfs2_dinode_has_extents", "di", "ocfs2_dinode")
                record["primary"] = guarded(extract.scalar_reads, *args, "i_flags")
                record["controls"] = {member: guarded(extract.scalar_reads, *args, member)
                    for member in ("i_size", "i_clusters")}
                record["mask_literals"] = guarded(extract.constant, h,
                    "OCFS2_SUPER_BLOCK_FL | OCFS2_LOCAL_ALLOC_FL | OCFS2_CHAIN_FL | OCFS2_DEALLOC_FL")
                record["human_context"] = manual(old + "ocfs2/facts.json",
                    ["actual BE mount/I/O not run", "external disk format not independently certified"],
                    "reviewed filecheck repair path: failed validation, signature/VALID and mode gates; no machine CFG proof")
                record["check_proposal"] = "convert disk field before native numeric use, or mask in its domain; zero predicates alone need no conversion"
            elif case == "pwm":
                s = load(old + "pwm/source_manifest.json", revision,
                         "drivers/pwm/pwm-raspberrypi-poe.c")
                record["primary"] = guarded(extract.initializer_write, s,
                    "raspberrypi_pwm_get_property", "raspberrypi_pwm_prop", "msg", "reg", "reg")
                record["visible_value_domain"] = guarded(extract.visible_call_domain, s,
                    "raspberrypi_pwm_get_property", 1)
                record["current_visible_value_byte_difference"] = False if (
                    record["visible_value_domain"].get("all_zero") and
                    record["primary"].get("source_parameter_unchanged_in_supported_body") and
                    record["primary"].get("status") in ("candidate", "normal")) else None
                record["control"] = guarded(extract.initializer_write, s,
                    "raspberrypi_pwm_set_property", "raspberrypi_pwm_prop", "msg", "reg", "reg")
                record["human_context"] = manual(old + "pwm/facts.json",
                    ["firmware parser/spec not observed", "board BE support unknown", "runtime call not observed"],
                    "reviewed firmware handle/DT/Kconfig gates; compile-only does not imply request reachability")
                record["check_proposal"] = "retain type lead, but do not report an actual field byte difference for the visible zero argument"
            elif case == "smb":
                s = load(previous + "source_manifest.json", revision,
                         "fs/smb/client/reparse.c")
                helper = load(previous + "consumer/manual_review/source_manifest_extra.json", revision,
                              "fs/nls/nls_base.c")
                declarations = load(previous + "source_manifest.json", revision,
                                    "fs/smb/common/smb2pdu.h")
                posix_declarations = load(previous + "source_manifest.json", revision,
                                    "fs/smb/client/cifspdu.h")
                record["primary"] = guarded(extract.api_format, s, helper,
                                             "parse_reparse_wsl_symlink")
                record["controls"] = dict(
                    flags=guarded(extract.sizeof_references, s, declarations,
                        "parse_reparse_wsl_symlink", "buf", "reparse_wsl_symlink_data_buffer", "Flags"),
                    inode_type=guarded(extract.sizeof_references, s, posix_declarations,
                        "parse_reparse_posix", "buf", "reparse_posix_data", "InodeType"))
                record["human_context"] = manual(previous + "consumer/manual_review/review.json",
                    ["full encoder dataflow remains manual", "reported compiler warning not reproduced", "external SMB spec not read"],
                    "reviewed tag/length/null/allocator conditions and local LE consumer; runtime payload unknown")
                record["check_proposal"] = "keep API format selector separate from pointer type; fixed scalar sizeof is not a field-value read"
            else:
                s = load(previous + "source_manifest.json", revision,
                         "drivers/net/wireless/ath/ath12k/dp_rx.c")
                h = load(previous + "source_manifest.json", revision,
                         "drivers/net/wireless/ath/ath12k/hal_desc.h")
                mode = load(previous + "producer/manual_review/source_manifest_extra.json", revision,
                            "drivers/net/wireless/ath/ath12k/hal.c")
                record["primary"] = guarded(extract.bitfield_read, s, h,
                    "ath12k_dp_rx_process_reo_status", "hdr", "hal_tlv_64_hdr", "tl", mode)
                record["human_context"] = manual(previous + "producer/manual_review/review.json",
                    ["external descriptor format not independently proved", "actual selected ring flags unknown", "BE device runtime not observed"],
                    "reviewed descriptor pointer/lock/nonempty-ring path; semantic mode remains unknown")
                record["check_proposal"] = "route target to read analysis; establish descriptor format and actual swap mode before declaring a mismatch"
            observations.append(record)
    return dict(schema_version=1, date="2026-10-08", kind="bounded_already_read_development",
                development_interfaces=4, revision_observations=len(observations),
                new_confirmed_cases=0, generalization_accuracy_established=False,
                model_calls=0, compilation=False, kernel_device_execution=False,
                manual_context_is_automatic_proof=False,
                source_inventory=list(inventory.values()), observations=observations)


def main():
    dependencies = [Path(__file__), HERE / "interface_fact_extractor.py",
                    BASE / "endian_consumer_single_revision.py"]
    before = {p.relative_to(BASE).as_posix(): sha(p.read_bytes()) for p in dependencies}
    result = run()
    if before != {p.relative_to(BASE).as_posix(): sha(p.read_bytes()) for p in dependencies}:
        raise SystemExit("Code changed while running; no final result written.")
    result["execution_code_sha256"] = before
    destination = HERE / "results.json"
    if destination.exists():
        raise SystemExit("Refusing to replace development output; preserve the previous run explicitly.")
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(revisions=result["revision_observations"],
                         sources=len(result["source_inventory"]),
                         new_confirmed_cases=0), ensure_ascii=False))


if __name__ == "__main__":
    main()
