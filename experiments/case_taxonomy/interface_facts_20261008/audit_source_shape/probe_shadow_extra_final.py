"""Multi-declarator shadow probe against the first saved snapshot."""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
import extractor_final_snapshot as e

text = "struct disk { __le32 flags; }; struct host { u32 flags; };\nvoid f(struct disk *p) { { struct host *q, *p; if (p->flags & MASK) {} } }"
raw = text.encode()
blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
s = e.Source("shadow.c", "synthetic", "shadow.c", blob, raw)
out = {"extractor_snapshot_sha256": hashlib.sha256((HERE / "extractor_final_snapshot.py").read_bytes()).hexdigest(),
       "text": text, "intended_boundary": "reject inner multi-declarator shadow; host.flags must not bind to outer disk.flags",
       "actual_output": e.scalar_reads(s, s, "f", "p", "disk", "flags")}
destination = HERE / "probe_shadow_extra_final_output.json"
if destination.exists():
    raise SystemExit("Refusing to replace shadow probe output")
destination.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": [x["status"] for x in out["actual_output"]]}))
