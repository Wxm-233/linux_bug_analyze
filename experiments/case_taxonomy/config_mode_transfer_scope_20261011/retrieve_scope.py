"""One metadata query plus one batch for two predefined real scope inputs."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
REPO = "/root/repos/linux"
COMMITS = ["09ea90e5988df98ef58d61ae5af4834e64596d9e", "12b11e47f126d097839fd2f077636e2139b0151b"]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    pre = json.loads((HERE / "freeze_pre.json").read_text())
    for relative, expected in {**pre["files"], **pre["reused_files"]}.items():
        assert sha((HERE / relative).read_bytes()) == expected, relative
    rawdir = HERE / "raw"
    rawdir.mkdir(exist_ok=False)
    receipts = []

    def run(label, argv, limit, request=b""):
        failure = None
        try:
            r = subprocess.run(argv, input=request, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
            out, err, rc = r.stdout, r.stderr, r.returncode
        except subprocess.TimeoutExpired as e:
            out, err, rc = e.stdout or b"", e.stderr or b"", "timeout"
            failure = repr(e)
        except OSError as e:
            out, err, rc = b"", b"", "os_error"
            failure = repr(e)
        for stream, data in [("stdout", out), ("stderr", err), ("stdin", request)]:
            (rawdir / f"{label}.{stream}.bin").write_bytes(data)
        receipts.append({"label": label, "argv": argv, "returncode": rc, "stdout_bytes": len(out),
                         "stdout_sha256": sha(out), "stderr_sha256": sha(err), "stdin_sha256": sha(request),
                         "output_limit_bytes": limit, "exception": failure})
        save("raw/receipts.json", receipts)
        assert rc == 0 and len(out) <= limit, label
        return out

    data = run("01_metadata", ["git", "-C", REPO, "log", "--no-walk=unsorted",
               "--format=%x1e%H%x00%P%x00%cI%x00%s%x00", "--name-only", *COMMITS], 131072)
    records = []
    for record in data.split(b"\x1e")[1:]:
        fields = record.split(b"\0", 4)
        assert len(fields) == 5
        commit, parents, date, subject = [f.decode("utf-8") for f in fields[:4]]
        paths = [line.strip().decode("utf-8") for line in fields[4].splitlines() if line.strip()]
        parent_list = parents.split()
        assert commit in COMMITS and len(parent_list) == 1
        records.append({"commit": commit, "parent": parent_list[0], "committer_date": date,
                        "subject": subject, "changed_paths": paths})
    assert len(records) == 2 and {r["commit"] for r in records} == set(COMMITS)
    records = sorted(records, key=lambda item: COMMITS.index(item["commit"]))
    targets = []
    for index, record in enumerate(records):
        if index == 0:
            path = "tools/testing/kunit/qemu_configs/powerpc.py"
            eligible = path in record["changed_paths"]
        else:
            choices = sorted(p for p in record["changed_paths"] if Path(p).name == "Kconfig")
            eligible = bool(choices)
            path = choices[0] if choices else None
        record["selected_path"] = path if eligible else None
        record["selection_status"] = "fixed_scope_target_available" if eligible else "insufficient_material_target_not_in_changed_paths"
        if eligible:
            for role, revision in [("parent", record["parent"]), ("revision", record["commit"])]:
                targets.append({"commit": record["commit"], "revision": revision, "role": role, "path": path})
    save("metadata.json", {"records": records, "patch_read": False})
    # Freeze identities and deterministic target selection before obtaining any blob.
    request = "".join(t["revision"] + ":" + t["path"] + "\n" for t in targets).encode()
    save("source_paths_pre.json", {"phase": "pre_blob_retrieval", "targets": targets,
         "metadata_sha256": sha((HERE / "metadata.json").read_bytes()), "request_sha256": sha(request)})
    objects = []
    if targets:
        batch = run("02_objects", ["git", "-C", REPO, "cat-file", "--batch"], 2097152, request)
        pos = 0
        for index, target in enumerate(targets):
            end = batch.index(b"\n", pos)
            header = batch[pos:end].decode()
            pos = end + 1
            if header.endswith(" missing"):
                objects.append({**target, "status": "missing"})
                continue
            blob, typ, size_text = header.split()
            size = int(size_text)
            assert typ == "blob"
            content = batch[pos:pos + size]
            pos += size
            assert len(content) == size and batch[pos:pos + 1] == b"\n"
            pos += 1
            assert hashlib.sha1(b"blob " + str(size).encode() + b"\0" + content).hexdigest() == blob
            filename = f"{index + 1:02d}_{target['commit'][:4]}_{target['role']}_{Path(target['path']).name}"
            (rawdir / filename).write_bytes(content)
            objects.append({**target, "status": "available", "saved": "raw/" + filename,
                            "blob": blob, "sha256": sha(content), "bytes": size})
        assert pos == len(batch)
    save("retrieval_manifest.json", {"metadata_commits": 2, "Git_commands": len(receipts),
         "requested_blob_count": len(targets), "sources": objects, "patch_requests": 0,
         "candidate_template_CLI_executions": 0, "new_confirmed_cases": 0,
         "independent_positive_cases": 0, "classification": "scope_materials_not_detection_cases"})
    print(json.dumps({"commits": 2, "Git_commands": len(receipts), "source_objects": len(objects),
                     "available": sum(s["status"] == "available" for s in objects),
                     "targets": [r["selected_path"] for r in records], "candidate_template_executions": 0}))


if __name__ == "__main__":
    main()
