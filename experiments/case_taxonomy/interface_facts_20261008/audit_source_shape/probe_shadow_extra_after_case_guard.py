"""Record the expected rejection that the first shadow harness did not catch."""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
import extractor_after_case_guard_snapshot as e

initial = json.loads((HERE / "probe_shadow_extra_output.json").read_text(encoding="utf-8"))
text = initial["text"]
raw = text.encode()
blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
s = e.Source("shadow.c", "synthetic", "shadow.c", blob, raw)
try:
    output = e.scalar_reads(s, s, "f", "p", "disk", "flags")
    exception = None
except Exception as exc:
    output = None
    exception = {"type": type(exc).__name__, "message": str(exc)}
out = {"extractor_snapshot_sha256": hashlib.sha256((HERE / "extractor_after_case_guard_snapshot.py").read_bytes()).hexdigest(),
       "text": text, "intended_boundary": initial["intended_boundary"],
       "actual_output": output, "exception": exception,
       "harness_note": "The earlier unguarded final shadow harness exited 1 on this expected ValueError; its stderr is preserved in final_execution.json."}
destination = HERE / "probe_shadow_extra_after_case_guard_output.json"
if destination.exists():
    raise SystemExit("Refusing to replace guarded shadow output")
destination.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"exception": exception}))
