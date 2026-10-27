"""Bounded post-unseal manual evidence only: four files per fixed revision."""
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE = HERE.parents[1]
REVISIONS = {"parent": "ea58aae8458480d6391c404e62f1a4b30462b9c3",
             "fixed": "1cfa6d4e5bd9bfb15d165d8d843163363929ba1b"}
FILES = ("drivers/net/wireless/ath/ath12k/hal.c",
         "drivers/net/wireless/ath/ath12k/hal_rx.c",
         "include/linux/bitfield.h",
         "drivers/net/wireless/ath/ath12k/Kconfig")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


commands = []


def git(*args):
    argv = ["wsl", "-d", "Ubuntu", "--", "git", "-C", "/root/repos/linux", *args]
    result = subprocess.run(argv, capture_output=True, check=False)
    number = len(commands) + 1
    output_dir = HERE / "commands"
    output_dir.mkdir(exist_ok=True)
    entry = {"argv": argv, "returncode": result.returncode}
    for stream in ("stdout", "stderr"):
        raw = getattr(result, stream)
        path = output_dir / f"{number:03d}.{stream}.bin"
        path.write_bytes(raw)
        entry[stream] = path.relative_to(STAGE).as_posix()
        entry[stream + "_sha256"] = sha(raw)
    commands.append(entry)
    save_json(HERE / "commands_extra.json", commands)
    if result.returncode:
        raise RuntimeError(argv)
    return result.stdout


manifest = []
for label, revision in REVISIONS.items():
    for source in FILES:
        blob = git("rev-parse", "--verify", revision + ":" + source).decode("ascii").strip()
        assert re.fullmatch(r"[0-9a-f]{40}", blob)
        raw = git("show", revision + ":" + source)
        assert hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest() == blob
        path = HERE / "sources" / label / source
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        manifest.append({"role": "producer", "label": label, "revision": revision,
                         "source_path": source, "saved_path": path.relative_to(STAGE).as_posix(),
                         "sha256": sha(raw), "blob_sha1": blob, "bytes": len(raw)})
        save_json(HERE / "source_manifest_extra.json", manifest)
print(json.dumps({"source_records": len(manifest), "files_per_revision": len(FILES),
                  "local_git_readonly_commands": len(commands)}))
