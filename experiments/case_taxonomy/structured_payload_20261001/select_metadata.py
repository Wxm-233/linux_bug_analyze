"""Bounded metadata-only older HCI pool; no source or commit body output."""
from datetime import datetime, timezone
from pathlib import Path
import json
import re
import subprocess

HERE = Path(__file__).resolve().parent
REPO = '/root/repos/linux'

def git(*args):
    return subprocess.run(['git', '-C', REPO, *args], capture_output=True,
                          text=True, check=True).stdout

def main():
    output = HERE / 'metadata_pool.json'
    if output.exists():
        raise RuntimeError('refusing to replace metadata pool')
    args = ['log', '--all', '--no-merges', '--since=2010-01-01',
            '--until=2017-12-31', '--regexp-ignore-case', '--extended-regexp',
            '--grep=endian|byte.?order|cpu_to_le|conversion', '--max-count=60',
            '--format=%H%x09%cs%x09%s', '--', 'net/bluetooth/hci_core.c',
            'net/bluetooth/hci_request.c']
    records = []
    for row in git(*args).splitlines():
        bits = row.split('\t', 2)
        if len(bits) != 3 or not re.fullmatch('[0-9a-f]{40}', bits[0]):
            raise RuntimeError('unexpected metadata row')
        sha, date, subject = bits
        paths = git('diff-tree', '--no-commit-id', '--name-only', '-r', sha).splitlines()
        records.append(dict(commit=sha, date=date, subject=subject, paths=paths))
    report = dict(saved_at_utc=datetime.now(timezone.utc).isoformat(), query=args,
                  records=records, cap=60,
                  reading_scope='Only title/date/path metadata exposed; git grep may match commit bodies internally.',
                  sampling_limit='Purpose-selected bounded history, not a population sample or proof of same mechanism.')
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('metadata saved:', len(records))

if __name__ == '__main__':
    main()
