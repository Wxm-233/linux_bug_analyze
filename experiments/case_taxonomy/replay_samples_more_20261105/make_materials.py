"""Replay materials for every pair of this batch's labels.json (replay_samples_20261105/criteria.md section 5;
same code as that round's make_materials.py). Refuses to run unless labels.json matches
labels_sha256.txt. For pair <id>: replay/<id>/meta.json (base = T^, target architecture, mechanism, kind, the
reference commits and their subjects), replay/<id>/reference.diff (the reference commits restricted to the
reference architecture, or to non-arch paths when the reference is common code), replay/<id>/target_files/<path>
(T's target-architecture files as they are at T^); truth/<id>/truth.diff (T itself, kept apart from the inputs).
WSL (git); no model calls.
"""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
REPO = '/root/repos/linux'


def git(*a):
    return subprocess.run(['git', '-C', REPO, *a], capture_output=True).stdout.decode('utf-8', 'replace')


def main():
    raw = (HERE / 'labels.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != (HERE / 'labels_sha256.txt').read_text(encoding='utf-8').split()[0]:
        raise SystemExit('labels.json changed after its SHA was recorded (first line of labels_sha256.txt)')
    if (HERE / 'replay').exists():
        raise SystemExit('preserve')
    rows = [r for r in json.loads(raw.decode('utf-8')) if r['pair']]
    for r in rows:
        d, t = HERE / 'replay' / r['id'], HERE / 'truth' / r['id']
        (d / 'target_files').mkdir(parents=True)
        t.mkdir(parents=True)
        base = git('rev-parse', r['commit'] + '^').strip()
        paths = ['.', ':(exclude)arch'] if r['ref_arch'] == 'common' else [f'arch/{r["ref_arch"]}']
        ref = ''.join(git('show', '--format=commit %H%nSubject: %s%n', c, '--', *paths) for c in r['refs'])
        (d / 'reference.diff').write_text(ref, encoding='utf-8')
        files = [f for f in git('show', '--name-only', '--format=', r['commit']).split()
                 if f.startswith(f'arch/{r["target_arch"]}/')]
        for f in files:
            out = d / 'target_files' / f
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(git('show', f'{base}:{f}'), encoding='utf-8')
        meta = {k: r[k] for k in ('id', 'target_arch', 'kind', 'refs', 'ref_arch', 'mechanism', 'simple')}
        meta.update({'base': base, 'target_files': files,
                     'ref_subjects': [git('log', '-1', '--format=%s', c).strip() for c in r['refs']]})
        (d / 'meta.json').write_text(json.dumps(meta, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
        (t / 'truth.diff').write_text(git('show', '--format=commit %H%nSubject: %s%n', r['commit']), encoding='utf-8')
    print(len(rows), 'pairs written')


if __name__ == '__main__':
    main()
