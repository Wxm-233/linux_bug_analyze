"""Local, source-only Raspberry Pi PoE PWM development replay and evidence export.

The frozen legacy producer CLI runs directly in WSL with its original Git reader.
Windows Python orchestrates source export and the direct CLI invocation.
No compiler, kernel, hardware, network, model, or new parameter grid is run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
LEGACY = HERE.parents[1]
REPO = "/root/repos/linux"
REVISIONS = {
    "parent": "d7b4408374b69dbc246c59c29e3077920b9f03eb",
    "fixed": "09f688f0718f57f9cf68ee1aa94490f641e759ba",
}
SOURCE = "drivers/pwm/pwm-raspberrypi-poe.c"
LEGACY_FILES = ("endian_producer_single_revision.py", "endian_consumer_single_revision.py")
PROTOCOL = HERE.parent / "protocol_pre.md"
SOURCES = (
    SOURCE,
    "drivers/firmware/raspberrypi.c",
    "include/soc/bcm2835/raspberrypi-firmware.h",
    "drivers/mailbox/bcm2835-mailbox.c",
    "drivers/mailbox/mailbox.c",
    "drivers/pwm/Kconfig", "drivers/firmware/Kconfig", "drivers/mailbox/Kconfig",
    "drivers/pwm/Makefile", "drivers/firmware/Makefile", "drivers/mailbox/Makefile",
    "arch/arm/mach-bcm/Kconfig", "arch/arm64/Kconfig.platforms", "arch/arm/Kconfig",
    "Documentation/devicetree/bindings/pwm/raspberrypi,firmware-poe-pwm.yaml",
    "Documentation/devicetree/bindings/firmware/raspberrypi,bcm2835-firmware.yaml",
    "arch/arm/boot/dts/bcm283x-rpi.dtsi",
    "include/dt-bindings/pwm/raspberrypi,firmware-poe-pwm.h",
)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def hashes() -> dict:
    return {
        name: {"absolute_path": str(LEGACY / name), "sha256": sha((LEGACY / name).read_bytes())}
        for name in LEGACY_FILES
    } | {"run_pwm.py": {"absolute_path": str(Path(__file__).resolve()),
                          "sha256": sha(Path(__file__).read_bytes())},
         "protocol_pre.md": {"absolute_path": str(PROTOCOL),
                             "sha256": sha(PROTOCOL.read_bytes())}}


class Git:
    def __init__(self, phase: str):
        self.phase = phase
        self.commands: list[dict] = []

    def run(self, *args: str, allow_missing: bool = False) -> bytes:
        argv = ["wsl", "-d", "Ubuntu", "--", "git", "-C", REPO, *args]
        return self.execute(argv, allow_missing=allow_missing)

    def execute(self, argv: list[str], allow_missing: bool = False) -> bytes:
        started = now()
        process = subprocess.run(argv, capture_output=True, check=False)
        index = len(self.commands) + 1
        prefix = HERE / "commands" / self.phase / f"{index:03d}"
        prefix.parent.mkdir(parents=True, exist_ok=True)
        stdout = prefix.with_suffix(".stdout.bin")
        stderr = prefix.with_suffix(".stderr.bin")
        stdout.write_bytes(process.stdout)
        stderr.write_bytes(process.stderr)
        self.commands.append({
            "argv": argv, "cwd": str(HERE), "started_at_utc": started,
            "finished_at_utc": now(), "returncode": process.returncode,
            "stdout": str(stdout.relative_to(HERE)), "stdout_sha256": sha(process.stdout),
            "stderr": str(stderr.relative_to(HERE)), "stderr_sha256": sha(process.stderr),
            "stderr_note": "WSL startup/proxy warning is retained as raw bytes, never parsed as a Git SHA.",
        })
        write_json(HERE / f"commands_{self.phase}.json", self.commands)
        if process.returncode and not allow_missing:
            raise RuntimeError(f"Local command failed: {argv!r}; see raw command outputs")
        return process.stdout


def prepare() -> None:
    before = hashes()
    write_json(HERE / "prepare_hashes_before.json", {"recorded_at_utc": now(), "files": before})
    git = Git("prepare")
    manifest = []
    for label, revision in REVISIONS.items():
        resolved = git.run("rev-parse", "--verify", revision).decode("ascii").strip()
        if resolved != revision:
            raise RuntimeError("revision did not resolve exactly")
        for source in SOURCES:
            blob_raw = git.run("rev-parse", "--verify", f"{revision}:{source}", allow_missing=True)
            blob = blob_raw.decode("ascii", errors="replace").strip()
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
            write_json(HERE / "source_manifest.json", manifest)
        git.run("grep", "-n", "-e", "raspberrypi_pwm_get_property", "-e",
                "RPI_PWM_CUR_DUTY_REG", "-e", "RPI_FIRMWARE_GET_POE_HAT_VAL", "-e",
                "raspberrypi,firmware-poe-pwm", revision, "--")
    git.run("show", "--format=fuller", "--no-ext-diff", REVISIONS["fixed"], "--", SOURCE)
    after = hashes()
    write_json(HERE / "prepare_hashes_after.json", {
        "recorded_at_utc": now(), "files": after, "unchanged": before == after})
    if before != after:
        raise RuntimeError("legacy or runner file changed during preparation")
    print(json.dumps({"phase": "prepare", "sources": len(manifest), "commands": len(git.commands),
                      "legacy_and_runner_unchanged": True}, ensure_ascii=False))


def replay() -> None:
    before = hashes()
    write_json(HERE / "replay_hashes_before.json", {"recorded_at_utc": now(), "files": before})
    git = Git("replay")

    def wsl_path(path: Path) -> str:
        resolved = path.resolve()
        return "/mnt/" + resolved.drive[0].lower() + "/" + str(resolved)[3:].replace("\\", "/")

    results = {}
    for label, revision in REVISIONS.items():
        destination = HERE / "raw" / f"{label}.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        git.execute(["wsl", "-d", "Ubuntu", "--", "python3", "-B",
                     wsl_path(LEGACY / LEGACY_FILES[0]), "--linux-dir", REPO,
                     "--revision", revision, "--source", SOURCE,
                     "--output", wsl_path(destination)])
        report = json.loads(destination.read_text(encoding="utf-8"))
        results[label] = {"raw_path": str(destination.relative_to(HERE)),
                          "sha256": sha(destination.read_bytes()), "counts": report["counts"]}
    after = hashes()
    write_json(HERE / "replay_hashes_after.json", {
        "recorded_at_utc": now(), "files": after, "unchanged": before == after})
    if before != after:
        raise RuntimeError("legacy or runner file changed during replay")
    write_json(HERE / "replay_manifest.json", {
        "completed_at_utc": now(), "experiment_status": "already-read development replay; not blind or holdout",
        "invocation": "original producer CLI directly in WSL python3 -B, original consumer Git reader; Windows Python orchestration",
        "count_unit": "assignment sites, not cases", "results": results,
        "legacy_and_runner_unchanged": True})
    print(json.dumps({"phase": "replay", "results": results,
                      "legacy_and_runner_unchanged": True}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("prepare", "replay"), required=True)
    args = parser.parse_args()
    {"prepare": prepare, "replay": replay}[args.phase]()
