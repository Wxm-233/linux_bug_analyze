"""Hash-guarded sync of the two user-requested Windows/WSL working notes."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
OUTER = HERE.parents[3]


def main():
    receipt_path = HERE / 'notes_sync.json'
    if receipt_path.exists():
        raise RuntimeError('preserve sync receipt')
    changes = json.loads((HERE / 'notes_update.json').read_text(encoding='utf-8'))
    payload = []
    for name, digest in changes['before_sha256'].items():
        source = OUTER / name
        assert hashlib.sha256(source.read_bytes()).hexdigest() == changes['after_sha256'][name]
        payload.append({'name': name, 'before': digest, 'after': changes['after_sha256'][name]})
    code = '''from pathlib import Path
import hashlib,json,sys
rows=json.load(sys.stdin)
root=Path('/root')
source=Path('/mnt/d/homework/software/linux_bug_analyze')
for row in rows:
 p=root/row['name']
 assert hashlib.sha256(p.read_bytes()).hexdigest()==row['before'],row['name']
 assert hashlib.sha256((source/row['name']).read_bytes()).hexdigest()==row['after'],row['name']
for row in rows:
 p=root/row['name']; p.write_bytes((source/row['name']).read_bytes())
 assert hashlib.sha256(p.read_bytes()).hexdigest()==row['after']
print(json.dumps({'status':'synced','files':rows},ensure_ascii=False))
'''
    done = subprocess.run(['wsl.exe', '-d', 'Ubuntu', '--', 'python3', '-c', code],
                          input=json.dumps(payload, ensure_ascii=False).encode('utf-8'), capture_output=True)
    if done.returncode != 0:
        raise RuntimeError(done.stderr.decode('utf-8', errors='replace'))
    result = json.loads(done.stdout.decode('utf-8'))
    receipt_path.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'files': len(result['files'])}))


if __name__ == '__main__':
    main()
