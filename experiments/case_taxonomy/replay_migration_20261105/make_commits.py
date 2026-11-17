"""One local commit per generated test patch (criteria.md section 4 needs the patched code), built without a working
tree: the base tree is read into a temporary index; the patch goes in with `git apply --cached` (then `--recount`);
a patch that only applies at the fuzzy level (criteria_amendment2.md) is applied with `patch` in a temporary
directory holding its files, whose results are written into the index with `git hash-object -w` and
`git update-index`. No branch is created; the commits are unreferenced. WSL (git); no model calls.
Output: commits_test.json ({dir: {base, sha, level}}; sha is null when the patch does not apply at any level).
"""
from pathlib import Path
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('evaluate', HERE / 'evaluate.py')
EV = importlib.util.module_from_spec(spec)
spec.loader.exec_module(EV)
REPO = EV.REPO
IDENT = {'GIT_AUTHOR_NAME': 'replay', 'GIT_AUTHOR_EMAIL': 'replay@localhost', 'GIT_COMMITTER_NAME': 'replay',
         'GIT_COMMITTER_EMAIL': 'replay@localhost', 'GIT_AUTHOR_DATE': '2026-11-05T00:00:00+0000',
         'GIT_COMMITTER_DATE': '2026-11-05T00:00:00+0000'}


def run(*a, env=None, cwd=REPO):
    r = subprocess.run(list(a), cwd=cwd, capture_output=True, env={**os.environ, **IDENT, **(env or {})})
    return r.returncode, r.stdout.decode('utf-8', 'replace').strip()


def commit(base, patch, message):
    idx = tempfile.mktemp(prefix='replay_idx_')
    env = {'GIT_INDEX_FILE': idx}
    try:
        run('git', 'read-tree', base, env=env)
        level = None
        if run('git', 'apply', '--cached', str(patch), env=env)[0] == 0:
            level = 'strict'
        elif run('git', 'apply', '--cached', '--recount', str(patch), env=env)[0] == 0:
            level = 'recount'
        else:
            diff = patch.read_text(encoding='utf-8')
            files = EV.touched(diff)
            tree = EV.mini_tree(base, files)
            try:
                fixed = Path(tree) / 'recounted.patch'
                fixed.write_text(EV.recount(diff), encoding='utf-8', newline='\n')
                if run('patch', '-p1', '--fuzz=3', '-i', str(fixed), cwd=tree)[0] != 0:
                    return None, None
                for f in files:
                    p = Path(tree) / f
                    if p.exists():
                        _, blob = run('git', 'hash-object', '-w', str(p))
                        run('git', 'update-index', '--add', '--cacheinfo', f'100644,{blob},{f}', env=env)
                    else:
                        run('git', 'update-index', '--force-remove', f, env=env)
                level = 'fuzzy'
            finally:
                shutil.rmtree(tree)
        _, tree_sha = run('git', 'write-tree', env=env)
        _, sha = run('git', 'commit-tree', tree_sha, '-p', base, '-m', message)
        return sha, level
    finally:
        if os.path.exists(idx):
            os.remove(idx)


def main():
    out = HERE / 'commits_test.json'
    if out.exists():
        raise SystemExit('preserve')
    labels = {r['id']: r for r in json.loads((EV.SAMPLES / 'labels_all.json').read_text(encoding='utf-8'))}
    result = {}
    for x in json.loads((HERE / 'prompt_index_test.json').read_text(encoding='utf-8')):
        r = labels[x['id']]
        mdir = EV.SAMPLES.parent / ('replay_samples_20261105' if r['batch'] == 1 else 'replay_samples_more_20261105')
        base = json.loads((mdir / 'replay' / r['id'] / 'meta.json').read_text(encoding='utf-8'))['base']
        patch = HERE / 'patches' / f'{x["dir"]}.patch'
        sha, level = commit(base, patch, x['dir']) if patch.exists() and patch.read_text(encoding='utf-8').strip() \
            else (None, None)
        result[x['dir']] = {'base': base, 'sha': sha, 'level': level}
        print(x['dir'], level, sha)
    out.write_text(json.dumps(result, indent=1) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
