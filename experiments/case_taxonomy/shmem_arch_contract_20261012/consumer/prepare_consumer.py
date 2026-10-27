"""Export only the official XArray userspace harness and its dependencies.

Run in WSL. No checkout, index, or generated output in the Linux repository is
changed. All exported sources and subsequent build output stay below this file.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path, PurePosixPath

FIX = "9fd154ba926b34c833b7bfc4c14ee2e931b3d743"
PARENT = "3390916aca7af1893ed2ebcdfee1d6fdb65bb058"
REPO = Path("/root/repos/linux")
BASE = Path(__file__).resolve().parent
DEST = BASE / "source"


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(REPO), *args])


def run() -> None:
    if DEST.exists():
        raise SystemExit("source already exists; inspect/reuse it, do not overwrite")
    all_paths = set(git("ls-tree", "-r", "--name-only", FIX).decode().splitlines())
    selected = {
        path for path in all_paths
        if path.startswith(("tools/testing/radix-tree/", "tools/include/"))
        and not path.startswith(("tools/include/nolibc/", "tools/include/io_uring/"))
    }
    selected.update({
        "lib/xarray.c", "lib/test_xarray.c", "lib/radix-tree.c",
        "lib/radix-tree.h", "lib/idr.c",
        "tools/lib/find_bit.c", "tools/lib/bitmap.c", "tools/lib/slab.c",
        "include/linux/xarray.h", "include/linux/radix-tree.h",
        "include/linux/maple_tree.h", "include/linux/idr.h",
        "include/linux/kconfig.h",
    })
    records = []
    pending = sorted(selected)
    done = set()
    include = re.compile(rb'^\s*#\s*include\s+"([^"\n]+)"', re.MULTILINE)
    while pending:
        path = pending.pop()
        if path in done:
            continue
        if path not in all_paths:
            raise SystemExit(f"required source absent at fixed revision: {path}")
        blob = git("rev-parse", f"{FIX}:{path}").decode().strip()
        data = git("show", f"{FIX}:{path}")
        output = DEST / path
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)
        records.append({"path": path, "git_blob": blob,
                        "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
        done.add(path)
        for name in include.findall(data):
            candidate = str(PurePosixPath(path).parent / name.decode())
            # Resolve lexical ../ components without reading the host tree.
            pieces = []
            for piece in candidate.split("/"):
                if piece == "..":
                    pieces.pop()
                elif piece != ".":
                    pieces.append(piece)
            candidate = "/".join(pieces)
            if candidate in all_paths and candidate not in done:
                pending.append(candidate)
    harness = DEST / "tools/testing/radix-tree"
    (harness / "generated").mkdir(exist_ok=True)
    shutil.copyfile(BASE / "consumer_probe.c", harness / "consumer_probe.c")
    same_consumer = {}
    for path in ("lib/xarray.c", "include/linux/xarray.h", "tools/include/asm/bug.h"):
        old = git("rev-parse", f"{PARENT}:{path}").decode().strip()
        new = git("rev-parse", f"{FIX}:{path}").decode().strip()
        same_consumer[path] = {"parent_blob": old, "fixed_blob": new, "identical": old == new}
    report = {"fix": FIX, "parent": PARENT, "repository_head_read_only":
              git("rev-parse", "HEAD").decode().strip(),
              "source_files": sorted(records, key=lambda r: r["path"]),
              "source_files_count": len(records),
              "source_bytes": sum(r["bytes"] for r in records),
              "parent_fixed_identity": same_consumer,
              "official_environment": "tools/testing/radix-tree with system liburcu; no custom RCU shim",
              "geometry_provenance": "order9/order13 await separate real Kconfig/header authentication"}
    (BASE / "source_manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"files": len(records), "bytes": report["source_bytes"],
                      "consumer_identical": same_consumer["lib/xarray.c"]["identical"]}))


if __name__ == "__main__":
    run()
