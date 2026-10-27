"""Search prior local study records, never C/H source, patches or new retrievals."""
from pathlib import Path
import hashlib
import json
import subprocess

OUT = Path(__file__).resolve().parent
STAGE = OUT.parent
BASE = STAGE.parent

def main():
    pool_path = STAGE / 'metadata_pool.json'
    pool = json.loads(pool_path.read_text(encoding='utf-8'))['records']
    pattern = '|'.join(r['commit'][:8] for r in pool)
    args = ['rg', '--hidden', '--no-ignore', '-g', '*.md', '-g', '*.json', '-g', '*.tsv', '-g', '!encoded_count_support_20261009/**']
    paths = subprocess.run(args[:1] + ['--files'] + args[1:] + ['.'], cwd=BASE, capture_output=True, check=True)
    files = []
    for line in paths.stdout.decode('utf-8').splitlines():
        path = BASE / line
        assert STAGE not in path.resolve().parents
        files.append({'path': path.relative_to(BASE).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    match = subprocess.run(args + ['--json', '-n', '-i', pattern, '.'], cwd=BASE, capture_output=True)
    assert match.returncode in (0, 1)
    hits = []
    for line in match.stdout.decode('utf-8').splitlines():
        item = json.loads(line)
        if item['type'] != 'match':
            continue
        data = item['data']
        path = Path(data['path']['text']).as_posix()
        text = data['lines']['text'].rstrip('\r\n')
        for record in pool:
            if record['commit'][:8].lower() in text.lower():
                hits.append({'commit': record['commit'], 'pool_order': record['pool_order'], 'path': path, 'line': data['line_number'], 'text': text})
    result = {'metadata_pool_sha256': hashlib.sha256(pool_path.read_bytes()).hexdigest(), 'scope': 'All prior case_taxonomy .md/.json/.tsv files enumerated using rg --files --hidden --no-ignore, excluding complete encoded_count_support_20261009 stage; no C/H/patch/native outputs/analysis_out read.', 'enumeration_argv': args[:1] + ['--files'] + args[1:] + ['.'], 'search_argv': args + ['--json', '-n', '-i', pattern, '.'], 'cwd': str(BASE), 'searched_files': files, 'matching_references': hits}
    (OUT / 'scope_search.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for record in pool:
        paths = sorted({h['path'] for h in hits if h['commit'] == record['commit']})
        print(json.dumps({'commit': record['commit'][:12], 'files': paths, 'count': len(paths)}, ensure_ascii=False))
    print(json.dumps({'searched_files': len(files), 'hit_records': len(hits)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
