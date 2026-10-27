"""Known HCI development case only; never an independent leaveout score."""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from outbound_scalar_single_revision import analyze_revision

revisions = {"parent": "7c6ca1201e5e87513b27196138f06df9cbd09a7a",
             "fixed": "c30b93eade2ad1d77695669f25ddeb3833588d3b"}
manifest = {"role": "development replay of previously inspected source, not independent validation",
            "records": []}
for tag, revision in revisions.items():
    report = analyze_revision(Path("/root/repos/linux"), revision, "drivers/bluetooth/hci_ll.c")
    destination = HERE / f"hci_ll_{tag}_development.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest["records"].append({"revision": revision, "output": destination.name,
        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(), "counts": report["counts"]})
(HERE / "development_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(manifest, ensure_ascii=False))
