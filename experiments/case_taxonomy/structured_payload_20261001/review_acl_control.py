"""Post-freeze source evidence for the fixed ACL constant-cleanup control."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent

def git(*args):
    return subprocess.run(['git', '-C', '/root/repos/linux', *args], text=True,
                          capture_output=True, check=True).stdout

def main():
    if not (HERE/'holdout/parent_manifest_pre_review.json').is_file():
        raise RuntimeError('parent not preserved')
    dest = HERE/'source_review_cc48.json'
    if dest.exists():
        raise RuntimeError('refusing to overwrite evidence')
    target = next(row for row in json.loads((HERE/'selection_pre.json').read_text())['targets']
                  if row['commit'].startswith('cc48dc0a996a'))
    files = []
    for revision in (target['old_revision'], target['commit']):
        for path in ('net/bluetooth/hci_core.c', 'include/net/bluetooth/hci.h'):
            source = git('show', revision+':'+path)
            lines = source.splitlines()
            key = 'ACL tx timeout must be longer' if path.endswith('.c') else 'HCI_IDLE_TIMEOUT'
            hits = [i for i, line in enumerate(lines) if key in line]
            if len(hits) != 1:
                raise RuntimeError('source anchor not unique')
            start = max(0, hits[0]-2)
            end = min(len(lines), hits[0]+9)
            files.append(dict(revision=revision, path=path,
                git_blob=git('rev-parse', revision+':'+path).strip(),
                source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                first_line=start+1, last_line=end, text='\n'.join(lines[start:end])))
    report = dict(reviewed_at_utc=datetime.now(timezone.utc).isoformat(), target=target,
                  files=files, interpretation='Timeout constant/units cleanup control; no triggering architecture or causal cross-architecture error shown.',
                  five_dimensions=dict(trigger_architecture='not established', subsystem='Bluetooth ACL scheduling',
                    horizontal_or_vertical='no cross-architecture causal defect established',
                    origin_side='not applicable as defect; edited code is common net/bluetooth',
                    time='2012-02-13 integration of cleanup; introduction/discovery/fix intervals not assigned'),
                  inclusion='outside confirmed core; normal/control lead only, not a detector true negative because there were zero supported sites')
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('ACL source evidence saved')

if __name__ == '__main__':
    main()
