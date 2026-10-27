"""Freeze already-read Linux parent blobs and exact source excerpts as JSON.

This tool does not infer a protocol contract or run the kernel.  The raw files
were exported with the git-archive command recorded in evidence.json.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
PARENT = "cef456cd354ef485f12d57000c455e83e416a2b6"
SELECTED = "727ea61a5028f8ac96f75ab34cb1b56e63fd9227"
SOURCES = {
    "include/net/bluetooth/hci.h": {
        "git_blob_sha1": "5bc1e30dedde5b18df908abfbfdb15c705c99ab0",
        "line_spans": [[430, 435], [1540, 1551], [1577, 1584]],
    },
    "include/net/bluetooth/hci_core.h": {
        "git_blob_sha1": "b689aceb636b115aff038902cb14119384949955",
        "line_spans": [[269, 274]],
    },
    "net/bluetooth/hci_core.c": {
        "git_blob_sha1": "04bc79359a1736b28e83f0eb88828ceefd430f25",
        "line_spans": [
            [301, 317], [415, 428], [613, 617], [760, 766],
            [789, 848], [864, 892], [3188, 3193],
        ],
    },
    "net/bluetooth/hci_event.c": {
        "git_blob_sha1": "c1d3a303d97fbda890e546755535199af0420d2e",
        "line_spans": [
            [965, 976], [1470, 1500], [1591, 1605],
            [3325, 3327], [3385, 3391], [3413, 3415],
        ],
    },
    "net/bluetooth/hci_request.c": {
        "git_blob_sha1": "7f6a581b5b7e14fa7b72db8449afc85a8d9327e2",
        "line_spans": [[285, 308], [312, 345]],
    },
}


def source_record(path: str, meta: dict) -> dict:
    raw = (HERE / "raw" / path).read_bytes()
    git_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if git_blob != meta["git_blob_sha1"]:
        raise ValueError(f"Git blob mismatch: {path}: {git_blob}")
    content = raw.decode("utf-8")
    lines = content.splitlines(keepends=True)
    excerpts = []
    for start, end in meta["line_spans"]:
        if not 1 <= start <= end <= len(lines):
            raise ValueError(f"Invalid line range: {path}:{start}-{end}")
        excerpts.append({"start": start, "end": end, "text": "".join(lines[start - 1 : end])})
    return {
        "path": path,
        "raw_file": "raw/" + path,
        "git_blob_sha1": git_blob,
        "full_file_sha256": hashlib.sha256(raw).hexdigest(),
        "line_count": len(lines),
        "full_text": content,
        "excerpts": excerpts,
    }


def main() -> None:
    data = {
        "schema": "hci_parent_source_evidence_v1",
        "selected_commit": SELECTED,
        "parent_commit": PARENT,
        "parent_committer_date": "2019-10-16T20:33:16+02:00",
        "selected_committer_date": "2019-10-16T20:37:15+02:00",
        "origin": "human_assisted_source_review",
        "git_commands": [
            f"git -C /root/repos/linux show -s --format='%H %P %cI' {SELECTED}",
            f"git -C /root/repos/linux ls-tree {PARENT} <each-listed-path>",
            f"git -C /root/repos/linux show {PARENT}:<path> | nl -ba",
            f"git -C /root/repos/linux grep -n -E 'le_max_tx_(len|time)' {PARENT} -- .",
            "git -C /root/repos/linux archive " + PARENT + " " + " ".join(SOURCES)
            + " | tar -x -C <this-directory>/raw",
        ],
        "sources": [source_record(path, meta) for path, meta in SOURCES.items()],
        "facts": [
            {
                "id": "F1-host-fields",
                "status": "source_proven",
                "claim": "le_max_tx_len and le_max_tx_time are __u16 host fields, initialized to 0x001b and 0x0148; a successful LE Read Maximum Data Length response writes le16_to_cpu values, while nonzero status returns without assignment.",
                "refs": [
                    "include/net/bluetooth/hci_core.h:271-272",
                    "net/bluetooth/hci_core.c:3188-3193",
                    "net/bluetooth/hci_event.c:1591-1605",
                ],
            },
            {
                "id": "F2-read-before-write-source-order",
                "status": "source_proven",
                "claim": "The source schedules LE feature reading in init2, LE maximum data length reading in init3 when LE and DLE conditions hold, and default data length writing in init4 on the primary-controller path.",
                "refs": [
                    "net/bluetooth/hci_core.c:301-317",
                    "net/bluetooth/hci_core.c:415-428",
                    "net/bluetooth/hci_core.c:613-617",
                    "net/bluetooth/hci_core.c:760-766",
                    "net/bluetooth/hci_core.c:789-848",
                    "net/bluetooth/hci_core.c:864-892",
                    "net/bluetooth/hci_event.c:965-976",
                ],
                "limit": "Source order does not establish a particular controller response or hardware reachability.",
            },
            {
                "id": "F3-wire-parameter-copy",
                "status": "source_proven",
                "claim": "Opcode 0x2024 has packed __le16 tx_len and tx_time parameters; init4 directly assigns __u16 host fields and hci_prepare_cmd copies parameter bytes without converting them.",
                "refs": [
                    "include/net/bluetooth/hci.h:1547-1551",
                    "net/bluetooth/hci_core.c:841-848",
                    "net/bluetooth/hci_request.c:285-308",
                    "net/bluetooth/hci_request.c:312-345",
                ],
            },
            {
                "id": "F4-external-history",
                "status": "insufficient",
                "claim": "The original Core 5.1 page is available, but its 2019 PDF text was not parsed; later SIG Core 5.4 HCI text confirms a general little-endian rule and identifies this command as present since 4.2, without proving the exact historical wording.",
                "refs": [
                    "https://www.bluetooth.com/specifications/specs/core-specification-5-1/",
                    "https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-54/out/en/host-controller-interface/host-controller-interface-functional-specification.html",
                ],
            },
        ],
        "limitations": [
            "No controller, historical kernel, packet capture, or big-endian target was run.",
            "The direct-reference grep is exact-string evidence for this parent tree, not a whole-program semantic analysis.",
            "Human/assistant review determines the authority claim; this file is reproducible evidence, not an automated contract proof.",
        ],
    }
    (HERE / "evidence.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
