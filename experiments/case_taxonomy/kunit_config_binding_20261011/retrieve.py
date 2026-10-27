"""Retrieve exactly four frozen consumer files at one fixed revision."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
COMMIT = "09ea90e5988df98ef58d61ae5af4834e64596d9e"
PATHS = ["tools/testing/kunit/" + p for p in
         ["qemu_config.py", "kunit_kernel.py", "kunit_config.py", "kunit.py"]]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    freeze = json.loads((HERE / "freeze_pre.json").read_text(encoding="utf-8"))
    for path, expected in {**freeze["files"], **freeze["reused_files"]}.items():
        assert sha((HERE / path).read_bytes()) == expected, path
    rawdir = HERE / "raw"
    rawdir.mkdir(exist_ok=False)
    request = "".join(COMMIT + ":" + p + "\n" for p in PATHS).encode()
    argv = ["git", "-C", "/root/repos/linux", "cat-file", "--batch"]
    exception = None
    try:
        r = subprocess.run(argv, input=request, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
        stdout, stderr, returncode = r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired as e:
        stdout, stderr, returncode = e.stdout or b"", e.stderr or b"", "timeout"
        exception = repr(e)
    except OSError as e:
        stdout, stderr, returncode = b"", b"", "os_error"
        exception = repr(e)
    for stream, content in [("stdin", request), ("stdout", stdout), ("stderr", stderr)]:
        (rawdir / ("01_batch." + stream + ".bin")).write_bytes(content)
    save("raw/receipt.json", {"argv": argv, "returncode": returncode,
         "stdout_bytes": len(stdout), "stdout_sha256": sha(stdout),
         "stderr_sha256": sha(stderr), "stdin_sha256": sha(request), "output_limit_bytes": 524288,
         "exception": exception})
    assert returncode == 0 and len(stdout) <= 524288
    pos = 0
    objects = []
    for index, path in enumerate(PATHS):
        end = stdout.index(b"\n", pos)
        header = stdout[pos:end].decode()
        pos = end + 1
        if header.endswith(" missing"):
            objects.append({"revision": COMMIT, "path": path, "status": "missing"})
            continue
        blob, typ, count = header.split()
        size = int(count)
        assert typ == "blob"
        content = stdout[pos:pos + size]
        pos += size
        assert len(content) == size and stdout[pos:pos + 1] == b"\n"
        pos += 1
        assert hashlib.sha1(b"blob " + str(size).encode() + b"\0" + content).hexdigest() == blob
        filename = f"raw/{index + 1:02d}_{Path(path).name}"
        (HERE / filename).write_bytes(content)
        objects.append({"revision": COMMIT, "path": path, "status": "available", "saved": filename,
                        "blob": blob, "bytes": size, "sha256": sha(content)})
    assert pos == len(stdout)
    save("retrieval_manifest.json", {"Git_commands": 1, "sources": objects, "patch_requests": 0,
         "kernel_builds_or_boots": 0, "classification": "same_version_consumers_for_informed_development"})
    print(json.dumps({"Git_commands": 1, "objects": len(objects),
                      "available": sum(o["status"] == "available" for o in objects)}))


if __name__ == "__main__":
    main()
