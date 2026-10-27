"""Save one gate-development test execution and its unchanged source hashes."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE/'root_test_run.json')
    args = parser.parse_args()
    files = [HERE/'authority_gate.py', HERE/'authority_gate_test.py']
    started = {path.name: sha(path) for path in files}
    result_path = args.output
    if result_path.exists():
        raise RuntimeError('preserve previous test evidence; choose a separate runner/output for a new attempt')
    argv = [sys.executable, str(files[1])]
    process = subprocess.run(argv, capture_output=True, text=True)
    unchanged = all(sha(path) == started[path.name] for path in files)
    record = dict(saved_at_utc=datetime.now(timezone.utc).isoformat(),
        argv=argv, returncode=process.returncode, stdout=process.stdout, stderr=process.stderr,
        tested_files=started, code_unchanged_during_test=unchanged,
        scope='Evidence binding and refusal tests; no new defect or external semantic truth established.')
    with result_path.open('x', encoding='utf-8') as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    if process.returncode or not unchanged:
        raise RuntimeError('development test failed or code changed; see saved evidence')
    print(process.stderr.strip())
    print('gate code unchanged during root tests')


if __name__ == '__main__':
    main()
