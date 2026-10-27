"""Save local type/conversion definitions; this performs no compilation or value tests."""
import json
import re
from pathlib import Path
from run_pwm import Git, HERE, REVISIONS, hashes, now, sha, write_json

SOURCES = (
    "include/uapi/linux/types.h",
    "include/uapi/asm-generic/int-ll64.h",
    "include/linux/compiler_attributes.h",
    "include/linux/byteorder/generic.h",
    "include/uapi/linux/byteorder/big_endian.h",
    "include/uapi/linux/byteorder/little_endian.h",
    "arch/arm/include/uapi/asm/byteorder.h",
    "arch/arm64/include/uapi/asm/byteorder.h",
)
before = hashes()
before["export_type_contract.py"] = {"sha256": sha(Path(__file__).read_bytes())}
write_json(HERE / "type_contract_hashes_before.json", {"recorded_at_utc": now(), "files": before})
git = Git("type_contract")
manifest = []
for label, revision in REVISIONS.items():
    for source in SOURCES:
        blob = git.run("rev-parse", "--verify", f"{revision}:{source}").decode("ascii").strip()
        assert re.fullmatch(r"[0-9a-f]{40}", blob)
        raw = git.run("show", f"{revision}:{source}")
        destination = HERE / "source" / label / source
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        manifest.append({"revision_label": label, "revision": revision,
                         "source_path": source, "available": True,
                         "blob_oid": blob, "sha256": sha(raw), "bytes": len(raw),
                         "line_count": len(raw.splitlines()),
                         "saved_path": str(destination.relative_to(HERE))})
        write_json(HERE / "type_contract_manifest.json", manifest)
after = hashes()
after["export_type_contract.py"] = {"sha256": sha(Path(__file__).read_bytes())}
write_json(HERE / "type_contract_hashes_after.json", {
    "recorded_at_utc": now(), "files": after, "unchanged": before == after})
assert before == after
print(json.dumps({"sources": len(manifest), "commands": len(git.commands), "unchanged": True}))
