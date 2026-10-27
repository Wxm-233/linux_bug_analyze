"""Additional initializer source-type probes against the first saved snapshot."""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
import extractor_after_case_guard_snapshot as e

cases = []
for source_type in ("__le32", "__be32", "u64", "u32"):
    text = "struct msg { __le32 reg; };\nstatic int f(" + source_type + " reg) { struct msg msg = { .reg = cpu_to_le32(reg) }; return 0; }"
    raw = text.encode()
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    s = e.Source("synthetic.c", "synthetic", "synthetic.c", blob, raw)
    cases.append({"source_type": source_type, "text": text,
                  "intended_boundary": "normal only for matching-width native u32 source; other source types insufficient",
                  "actual_output": e.initializer_write(s, "f", "msg", "msg", "reg", "reg")})
out = {"extractor_snapshot_sha256": hashlib.sha256((HERE / "extractor_after_case_guard_snapshot.py").read_bytes()).hexdigest(),
       "cases": cases}
destination = HERE / "probe_additional_after_case_guard_output.json"
if destination.exists():
    raise SystemExit("Refusing to replace additional probe output")
destination.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps([{ "source_type": c["source_type"], "status": c["actual_output"]["status"]} for c in cases]))
