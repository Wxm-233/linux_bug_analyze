"""Preserve the first review and rerun its same 32 inputs against final code."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
main_path = HERE.parent / "interface_fact_extractor.py"
snapshot = HERE / "extractor_final_snapshot.py"
if snapshot.exists() or (HERE / "final_execution.json").exists():
    raise SystemExit("Refusing to replace final audit artifacts")
raw = main_path.read_bytes()
snapshot.write_bytes(raw)
initial_hash = hashlib.sha256(raw).hexdigest()

entries = []
for original_name in ("probe", "probe_additional", "probe_shadow_extra"):
    original = HERE / (original_name + ".py")
    destination = HERE / (original_name + "_final.py")
    if destination.exists():
        raise SystemExit("Refusing to replace final probe")
    text = original.read_text(encoding="utf-8")
    text = text.replace('"extractor_snapshot.py"', '"extractor_final_snapshot.py"')
    text = text.replace("import extractor_snapshot as e", "import extractor_final_snapshot as e")
    text = text.replace(original_name + "_output.json", original_name + "_final_output.json")
    destination.write_text(text, encoding="utf-8")
    command = [sys.executable, "-B", str(destination)]
    completed = subprocess.run(command, text=True, encoding="utf-8", capture_output=True)
    entries.append({"command": command, "cwd": str(Path.cwd()),
                    "exit_code": completed.returncode,
                    "stdout": completed.stdout, "stderr": completed.stderr,
                    "script_sha256": hashlib.sha256(destination.read_bytes()).hexdigest()})
    if completed.returncode != 0:
        break

final_hash = hashlib.sha256(main_path.read_bytes()).hexdigest()
dependency = HERE.parent.parent / "endian_consumer_single_revision.py"
outputs = list(HERE.glob("*_final_output.json"))
out = {"initial_current_extractor_sha256": initial_hash,
       "post_run_current_extractor_sha256": final_hash,
       "extractor_unchanged_during_run": initial_hash == final_hash,
       "final_snapshot_sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
       "lexical_dependency_sha256": hashlib.sha256(dependency.read_bytes()).hexdigest(),
       "python": sys.version, "executable": sys.executable,
       "runs": entries,
       "output_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in outputs}}
(HERE / "final_execution.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"snapshot": initial_hash, "unchanged": initial_hash == final_hash,
                  "exit_codes": [x["exit_code"] for x in entries]}, indent=2))
