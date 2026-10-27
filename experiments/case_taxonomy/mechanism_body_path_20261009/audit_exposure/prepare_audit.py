from pathlib import Path
import hashlib, json, subprocess

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
ROOT = STAGE.parent

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

pool = json.loads((STAGE / 'metadata_pool.json').read_text(encoding='utf-8'))
inventory_argv = ['rg', '--files', '--hidden', '--no-ignore', str(ROOT)]
p = subprocess.run(inventory_argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
assert p.returncode == 0, p.returncode
(HERE / 'inventory.stdout').write_bytes(p.stdout)
(HERE / 'inventory.stderr').write_bytes(p.stderr)
files = []
for raw in p.stdout.decode('utf-8').splitlines():
    f = Path(raw).resolve()
    if f.suffix.lower() in {'.md', '.json', '.tsv'} and not f.is_relative_to(STAGE):
        files.append(f)
files.sort(key=lambda f: f.relative_to(ROOT).as_posix())
fingerprints = [{'path': f.relative_to(ROOT).as_posix(), 'sha256': sha(f)} for f in files]
save('scope_search.json', {'inventory_argv': inventory_argv, 'inventory_exit_code': p.returncode,
    'metadata_pool_sha256': sha(STAGE / 'metadata_pool.json'), 'search_extensions': ['.md', '.json', '.tsv'],
    'excluded_entire_stage': STAGE.name, 'searched_file_count': len(files), 'searched_files': fingerprints,
    'inventory_stdout_sha256': sha(HERE / 'inventory.stdout'), 'inventory_stderr_sha256': sha(HERE / 'inventory.stderr')})
patterns = []
for r in pool['records']:
    patterns.extend([r['commit'], r['commit'][:12]])
(HERE / 'patterns.txt').write_text('\n'.join(patterns) + '\n', encoding='utf-8')
matches = []
receipts = []
for batch in range(0, len(files), 50):
    argv = ['rg', '--json', '--fixed-strings', '--no-heading', '--no-ignore', '--hidden', '-f', str(HERE / 'patterns.txt'), *map(str, files[batch:batch+50])]
    r = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert r.returncode in (0, 1), r.returncode
    name = f'rg_{batch//50:03}'
    (HERE / (name + '.stdout.jsonl')).write_bytes(r.stdout)
    (HERE / (name + '.stderr')).write_bytes(r.stderr)
    receipts.append({'argv': argv, 'exit_code': r.returncode, 'stdout_sha256': sha(HERE / (name + '.stdout.jsonl')), 'stderr_sha256': sha(HERE / (name + '.stderr'))})
    for line in r.stdout.decode('utf-8').splitlines():
        item = json.loads(line)
        if item['type'] != 'match':
            continue
        d = item['data']
        path = Path(d['path']['text']).resolve()
        assert path in files
        txt = d['lines']['text'].rstrip('\r\n')
        for row in pool['records']:
            if row['commit'] in txt or row['commit'][:12] in txt:
                matches.append({'commit': row['commit'], 'path': path.relative_to(ROOT).as_posix(), 'line': d['line_number'], 'text': txt})
save('search_receipts.json', receipts)
save('matches.json', matches)
summary = []
for row in pool['records']:
    mm = [m for m in matches if m['commit'] == row['commit']]
    summary.append({'commit': row['commit'], 'title': row['subject'], 'count': len(mm), 'references': [{'path': m['path'], 'line': m['line'], 'text': m['text'][:300]} for m in mm]})
save('match_summary.json', summary)
print(json.dumps({'pool_sha256': sha(STAGE/'metadata_pool.json'), 'files': len(files), 'matches': len(matches), 'records': len(summary)}, ensure_ascii=False))
