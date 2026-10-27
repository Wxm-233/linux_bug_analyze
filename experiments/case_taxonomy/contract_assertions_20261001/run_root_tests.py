"""Run locked generator boundary tests and preserve exact source hashes."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
RULES = HERE.parent

def main():
    destination = HERE/'root_test_run.json'
    if destination.exists():
        raise RuntimeError('refusing to overwrite test record')
    paths = [RULES/'contract_assertion_generator.py', RULES/'contract_assertion_generator_test.py']
    hashes = {path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    command = [sys.executable,str(paths[1])]
    process = subprocess.run(command, capture_output=True, text=True)
    unchanged = all(hashlib.sha256(path.read_bytes()).hexdigest()==hashes[path.name] for path in paths)
    result = dict(saved_at_utc=datetime.now(timezone.utc).isoformat(), argv=command,
        returncode=process.returncode, stdout=process.stdout, stderr=process.stderr,
        tested_files=hashes, code_unchanged_during_test=unchanged,
        scope='Generator evidence/refusal development tests, not detection accuracy on unknown cases.')
    with destination.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(process.stderr, end='')
    raise SystemExit(process.returncode if unchanged else 2)

if __name__ == '__main__':
    main()
