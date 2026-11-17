"""Compare checkpoint/reload merge with every existing selftest artifact."""
import gzip
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import enumerate as e
import merge_staged as staged

HERE = Path(__file__).resolve().parent
work = Path(os.environ["KBUILD"]) / "enumeration/selftest"
build = e.Build("test", HERE / "src", work, e.load_entries(work / "compile_commands.json"),
                work / e.sha256(HERE.parent / "enumerate.py"), {})
output = work / "staged_comparison"
output.mkdir(exist_ok=True)
state = staged.initialize(build)
checkpoint = output / "state.pickle"
for _ in range(3):
    staged.save(checkpoint, state)
    with checkpoint.open("rb") as stream:
        state = staged.pickle.load(stream)
    complete = staged.advance(build, state, 1)
assert complete
staged.finalize(build, state, output)
files = ["symbols_test.json", "boundary_test.jsonl.gz", "units_test.json.gz", "object_evidence_test.json.gz",
         "direct_calls_test.jsonl.gz", "result_test.json"]
for name in files:
    def content(path):
        return gzip.decompress(path.read_bytes()) if name.endswith(".gz") else path.read_bytes()
    assert content(work / name) == content(output / name), name
e.save_json(HERE / "staged_result.json", {"status": "passed", "files_identical": files,
             "checkpoint_reload_batches": 3, "merge_staged_sha256": e.sha256(HERE.parent / "merge_staged.py")})
print("STAGED MERGE PASSED: all 6 artifacts byte-identical after decompression; three checkpoint/reload batches")
