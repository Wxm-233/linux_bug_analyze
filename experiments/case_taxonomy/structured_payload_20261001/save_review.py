"""Unlock commit/patch reading only after verified parent preservation."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
RULES = HERE.parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def git(*args):
    return subprocess.run(['git', '-C', '/root/repos/linux', *args], capture_output=True,
                          text=True, check=True).stdout

def main():
    destination = HERE/'source_review_raw.json'
    if destination.exists():
        raise RuntimeError('refusing to overwrite source review')
    parent_path = HERE/'holdout/parent_manifest_pre_review.json'
    parent = json.loads(parent_path.read_text(encoding='utf-8'))
    if parent['freeze_sha256'] != sha(HERE/'freeze_manifest.json'):
        raise RuntimeError('freeze changed')
    for record in parent['records']:
        if sha(parent_path.parent / record['output']) != record['sha256']:
            raise RuntimeError('parent output changed')
    targets = json.loads((HERE/'selection_pre.json').read_text(encoding='utf-8'))['targets']
    records = []
    for target in targets:
        paths = [target['source_path'], 'include/net/bluetooth/hci.h',
                 'include/net/bluetooth/hci_core.h', 'net/bluetooth/hci_request.c',
                 'include/linux/skbuff.h']
        records.append(dict(target=target,
            commit_body_and_metadata=git('show', '-s', '--format=fuller', target['commit']),
            whole_commit_stat=git('show', '-s', '--format=', '--stat', target['commit']),
            bounded_path_patch=git('diff', target['old_revision'], target['commit'], '--', *paths)))
    report = dict(saved_at_utc=datetime.now(timezone.utc).isoformat(),
                  parent_manifest_sha256=sha(parent_path),
                  scope='Post-preservation commit and bounded-path patch review, never developer training before freeze.',
                  records=records)
    with destination.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print('post-parent source reviews saved:', len(records))

if __name__ == '__main__':
    main()
