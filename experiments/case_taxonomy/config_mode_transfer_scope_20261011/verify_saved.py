"""Root verification of saved evidence only; never repeat retrieval/detection."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[3]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify():
    freeze = load(HERE / "freeze_pre.json")
    for name, expected in {**freeze["files"], **freeze["reused_files"]}.items():
        assert sha((HERE / name).read_bytes()) == expected, name
    retrieval = load(HERE / "retrieval_manifest.json")
    metadata = load(HERE / "metadata.json")
    pre = load(HERE / "source_paths_pre.json")
    receipts = load(HERE / "raw/receipts.json")
    assert len(receipts) == 2 and retrieval["Git_commands"] == 2
    for rec in receipts:
        assert rec["returncode"] == 0 and rec["exception"] is None
        for stream in ["stdin", "stdout", "stderr"]:
            data = (HERE / "raw" / (rec["label"] + "." + stream + ".bin")).read_bytes()
            assert sha(data) == rec[stream + "_sha256"]
        assert rec["stdout_bytes"] <= rec["output_limit_bytes"]
    assert pre["metadata_sha256"] == sha((HERE / "metadata.json").read_bytes())
    request = "".join(t["revision"] + ":" + t["path"] + "\n" for t in pre["targets"]).encode()
    assert request == (HERE / "raw/02_objects.stdin.bin").read_bytes()
    assert sha(request) == pre["request_sha256"]
    records = []
    for raw in (HERE / "raw/01_metadata.stdout.bin").read_bytes().split(b"\x1e")[1:]:
        h, p, d, s, files = raw.split(b"\0", 4)
        records.append((h.decode(), p.decode(), d.decode(), s.decode(),
                        [v.strip().decode() for v in files.splitlines() if v.strip()]))
    assert len(records) == 2
    for observed, record in zip(records, metadata["records"]):
        assert observed == (record["commit"], record["parent"], record["committer_date"],
                            record["subject"], record["changed_paths"])
        assert len(record["parent"].split()) == 1
    assert metadata["records"][0]["selected_path"] == "tools/testing/kunit/qemu_configs/powerpc.py"
    assert metadata["records"][1]["selected_path"] is None
    assert len(metadata["records"][1]["changed_paths"]) == 7
    assert all(Path(p).name != "Kconfig" for p in metadata["records"][1]["changed_paths"])
    batch = (HERE / "raw/02_objects.stdout.bin").read_bytes()
    pos = 0
    assert len(retrieval["sources"]) == len(pre["targets"]) == 2
    for obj, target in zip(retrieval["sources"], pre["targets"]):
        assert all(obj[k] == v for k, v in target.items())
        end = batch.index(b"\n", pos)
        blob, typ, size = batch[pos:end].decode().split()
        pos = end + 1
        data = batch[pos:pos + int(size)]
        pos += int(size)
        assert batch[pos:pos + 1] == b"\n"
        pos += 1
        assert typ == "blob" and blob == obj["blob"]
        assert hashlib.sha1(b"blob " + size.encode() + b"\0" + data).hexdigest() == blob
        assert data == (HERE / obj["saved"]).read_bytes()
        assert len(data) == obj["bytes"] and sha(data) == obj["sha256"]
    assert pos == len(batch)
    old = (HERE / retrieval["sources"][0]["saved"]).read_bytes().splitlines(keepends=True)
    new = (HERE / retrieval["sources"][1]["saved"]).read_bytes().splitlines(keepends=True)
    assert new[5] == b"CONFIG_CPU_BIG_ENDIAN=y\n" and new[:5] + new[6:] == old
    result = load(HERE / "scope_results.json")
    assert result["candidate_template_executions"] == retrieval["candidate_template_CLI_executions"] == 0
    assert all(i["candidate_count"] is None and not i["candidate_template_executed"] for i in result["inputs"])
    stages = {}
    for name in ["config_mode_candidates_20261011", "config_mode_projection_20261011", "config_contract_20261010"]:
        base = HERE.parent / name
        previous = load(base / "completion_manifest.json")
        for path, expected in previous["files"].items():
            assert sha((base / path).read_bytes()) == expected, name + "/" + path
        stages[name] = len(previous["files"])
    protection = load(WORKSPACE / "日志/目录整理-2026-10-10.json")
    counts = {}
    for group in ["protected_experiment_files", "source_code", "current_reports"]:
        for path, expected in protection[group].items():
            assert sha((WORKSPACE / path).read_bytes()) == expected, path
        counts[group] = len(protection[group])
    out = {"status": "PASS", "saved_blobs": 2, "one_line_addition_verified": True,
           "candidate_template_executions": 0, "prior_seals": stages, "historical_protection": counts,
           "scope": "saved evidence, not rerun or independent defect detection"}
    (HERE / "root_verification.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    verify()
