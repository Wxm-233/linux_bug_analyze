"""Local Git identity and changed-path collection; never asks Git for message or patch."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess

stage = Path(__file__).resolve().parent
inner = stage.parents[2]
protocol_path = stage / 'protocol_pre.json'
protocol = json.loads(protocol_path.read_text(encoding='utf-8'))
pool_path = inner / protocol['pool']
assert hashlib.sha256(pool_path.read_bytes()).hexdigest() == protocol['pool_sha256']
pool = json.loads(pool_path.read_text(encoding='utf-8'))['samples']
assert len(pool) == protocol['pool_count']
assert len({item['hash'] for item in pool}) == len(pool)
out = stage / 'git_metadata.json'
if out.exists():
    raise SystemExit('Metadata already exists; preserve the first collection.')

def git(*args):
    proc = subprocess.run(['git', '-C', protocol['metadata_collection']['repository'], *args], capture_output=True, timeout=30)
    if proc.returncode:
        raise RuntimeError(proc.stderr.decode('utf-8', errors='replace')[:1000])
    return proc.stdout

records = []
for item in pool:
    record = {key: item[key] for key in ['hash', 'subject', 'band', 'stratum']}
    record['status'] = 'metadata_error'
    try:
        info = git('show', '-s', '--format=%H%x00%P%x00%aI%x00%cI%x00%an', item['hash']).decode('utf-8').rstrip('\n').split('\x00')
        assert len(info) == 5 and info[0] == item['hash']
        record.update(parents=info[1].split(), author_date=info[2], committer_date=info[3], author=info[4])
        if len(record['parents']) == 1:
            parts = git('diff-tree', '--no-commit-id', '--name-status', '-r', '--no-renames', '-z', record['parents'][0], item['hash']).split(b'\0')
            assert parts[-1] == b''
            parts.pop()
            assert len(parts) % 2 == 0
            record['changes'] = [{'status': parts[n].decode('ascii'), 'path': parts[n + 1].decode('utf-8', errors='surrogateescape')} for n in range(0, len(parts), 2)]
            assert all(len(change['status']) == 1 for change in record['changes'])
            record['status'] = 'single_parent_metadata'
        else:
            record['status'] = 'non_single_parent'
            record['changes'] = []
    except (RuntimeError, AssertionError, UnicodeError, subprocess.TimeoutExpired) as exc:
        record['error'] = str(exc)[:1000]
    records.append(record)

result = {
    'task': 'N1.4g',
    'collected_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'protocol_sha256': hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
    'pool_sha256': protocol['pool_sha256'],
    'records': records,
    'new_message_patch_or_source_body_reads': 0,
    'network_requests': 0,
}
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
counts = {name: sum(record['status'] == name for record in records) for name in ['single_parent_metadata', 'non_single_parent', 'metadata_error']}
print(json.dumps({'saved': str(out), 'records': len(records), 'status_counts': counts, 'protocol_sha256': result['protocol_sha256']}, ensure_ascii=False))
