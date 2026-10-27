"""Read exactly the six declared local Git sources. No fetch or expansion."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent


def main():
    plan_path = HERE / 'source_plan.json'
    plan = json.loads(plan_path.read_bytes())
    assert len(plan['files']) == 6
    rows = []
    for spec in plan['files']:
        row = dict(spec, status='collection_error')
        try:
            ref = spec['revision'] + ':' + spec['path']
            args = ['wsl.exe', '-d', 'Ubuntu', '--', 'git', '-C', '/root/repos/linux']
            identity = subprocess.run(args + ['rev-parse', ref], capture_output=True, timeout=45)
            source = subprocess.run(args + ['show', ref], capture_output=True, timeout=45)
            assert identity.returncode == source.returncode == 0
            raw = source.stdout
            blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
            assert blob == identity.stdout.decode().strip()
            row.update(status='collected', git_blob=blob, sha256=hashlib.sha256(raw).hexdigest(),
                       bytes=len(raw), text=raw.decode('utf-8'))
        except (AssertionError, UnicodeError, subprocess.TimeoutExpired) as error:
            row['error'] = type(error).__name__ + ': ' + str(error)
        rows.append(row)
    target = HERE / 'sources.json'
    with target.open('x', encoding='utf-8') as stream:
        json.dump({'plan_sha256': hashlib.sha256(plan_path.read_bytes()).hexdigest(),
                   'documents': rows, 'layer': 'unpreprocessed_exact_git_source',
                   'new_files': len(rows), 'network_requests': 0}, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'files': len(rows), 'collected': sum(x['status'] == 'collected' for x in rows),
                      'bytes': sum(x.get('bytes', 0) for x in rows)}))


if __name__ == '__main__':
    main()
