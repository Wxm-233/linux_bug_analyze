"""Labelling aid (criteria.md section 2): for every candidate, the commits between its snapshot and the end version
df2908090cda that touch the flagged function (git log -L), with subject and whether the function still exists at the
end. WSL (git); no model. Input candidates_la.json (amendment 1); output: evidence_la.json."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import subprocess

HERE = Path(__file__).resolve().parent
REPO, END = '/root/repos/linux', 'df2908090cda'


def git(*a):
    return subprocess.run(['git', '-C', REPO, *a], capture_output=True).stdout.decode('utf-8', 'replace')


def one(c):
    log = git('log', '--format=@@%h %cs %s', '-s', f'-L:{c["name"]}:{c["path"]}', f'{c["snapshot"]}..{END}')
    commits = [l[2:] for l in log.splitlines() if l.startswith('@@')]
    if not commits:  # renamed or moved: fall back to commits on the file that mention the name in the diff
        log = git('log', '--format=@@%h %cs %s', f'-G\\b{c["name"]}\\b', f'{c["snapshot"]}..{END}', '--', c['path'])
        commits = ['(file) ' + l[2:] for l in log.splitlines() if l.startswith('@@')]
    at_end = bool(git('grep', '-n', f'\\b{c["name"]}\\b', END, '--', c['path']).strip())
    return {'cand': c['cand'], 'name': c['name'], 'snapshot': c['snapshot'], 'commits': commits, 'name_at_end': at_end}


def main():
    rows = json.loads((HERE / 'candidates_la.json').read_text(encoding='utf-8'))['rows']
    with ThreadPoolExecutor(8) as ex:
        out = list(ex.map(one, rows))
    (HERE / 'evidence_la.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    for r in out:
        print(r['cand'], r['snapshot'], r['name'], 'end' if r['name_at_end'] else 'GONE', len(r['commits']))
        for c in r['commits'][:12]:
            print('    ', c[:110])


if __name__ == '__main__':
    main()
