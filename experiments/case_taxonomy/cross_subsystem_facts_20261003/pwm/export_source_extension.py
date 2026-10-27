"""Export same-revision files located by the saved local source grep.

This is additional manual source review, separate from the legacy CLI replay.
"""
import json
import re
from pathlib import Path
from run_pwm import Git, HERE, REVISIONS, hashes, now, sha, write_json

SOURCES = (
    "Documentation/devicetree/bindings/arm/bcm/raspberrypi,bcm2835-firmware.yaml",
    "arch/arm/boot/dts/broadcom/bcm283x-rpi.dtsi",
    "arch/arm/boot/dts/broadcom/bcm2835-rpi.dtsi",
    "arch/arm/mm/Kconfig",
    "arch/arm64/Kconfig",
)
before = hashes()
before["export_source_extension.py"] = {"sha256": sha(Path(__file__).read_bytes())}
write_json(HERE / "extension_hashes_before.json", {"recorded_at_utc": now(), "files": before})
git = Git("source_extension")
manifest = []
for label, revision in REVISIONS.items():
    for source in SOURCES:
        blob = git.run("rev-parse", "--verify", f"{revision}:{source}", allow_missing=True).decode("ascii", errors="replace").strip()
        if not re.fullmatch(r"[0-9a-f]{40}", blob):
            manifest.append({"revision_label": label, "revision": revision,
                             "source_path": source, "available": False})
            continue
        raw = git.run("show", f"{revision}:{source}")
        destination = HERE / "source" / label / source
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        manifest.append({"revision_label": label, "revision": revision,
                         "source_path": source, "available": True,
                         "blob_oid": blob, "sha256": sha(raw), "bytes": len(raw),
                         "line_count": len(raw.splitlines()),
                         "saved_path": str(destination.relative_to(HERE))})
        write_json(HERE / "source_extension_manifest.json", manifest)
after = hashes()
after["export_source_extension.py"] = {"sha256": sha(Path(__file__).read_bytes())}
write_json(HERE / "extension_hashes_after.json", {
    "recorded_at_utc": now(), "files": after, "unchanged": before == after})
assert before == after
print(json.dumps({"sources": len(manifest), "commands": len(git.commands), "unchanged": True}))
