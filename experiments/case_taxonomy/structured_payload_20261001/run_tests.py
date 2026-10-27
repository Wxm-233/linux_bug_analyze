"""Root verification of new bounded rule tests; save exact result once."""
from datetime import datetime, timezone
from pathlib import Path
import json
import hashlib
import subprocess
import sys

HERE = Path(__file__).resolve().parent

def main():
    output = HERE/'root_test_run.json'
    if output.exists():
        raise RuntimeError('refusing to overwrite root test evidence')
    command = [sys.executable, str(HERE.parent/'structured_hci_single_revision_test.py')]
    result = subprocess.run(command, capture_output=True, text=True)
    report = dict(saved_at_utc=datetime.now(timezone.utc).isoformat(), argv=command,
                  returncode=result.returncode, stdout=result.stdout, stderr=result.stderr,
                  tested_files={name:hashlib.sha256((HERE.parent/name).read_bytes()).hexdigest()
                      for name in ('structured_hci_single_revision.py', 'structured_hci_single_revision_test.py')},
                  scope='New rule boundary tests on development/synthetic data; not unknown-case detection accuracy.')
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(result.stdout, end='')
    print(result.stderr, end='')
    raise SystemExit(result.returncode)

if __name__ == '__main__':
    main()
