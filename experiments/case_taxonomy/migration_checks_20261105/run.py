"""Run checks.py (criteria.md section 3) on the 42 generated test patches that apply
(replay_migration_20261105/commits_test.json) and, as the negative control, on the 42 true patches T on their
parents. 8 at a time. WSL (git); no model calls. Output: checks_generated.json, checks_truth.json.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import checks  # noqa: E402

REPLAY = HERE.parent / 'replay_migration_20261105'
SAMPLES = HERE.parent / 'replay_samples_more_20261105'


def meta(r):
    d = SAMPLES.parent / ('replay_samples_20261105' if r['batch'] == 1 else 'replay_samples_more_20261105')
    return json.loads((d / 'replay' / r['id'] / 'meta.json').read_text(encoding='utf-8'))


def main():
    if (HERE / 'checks_generated.json').exists():
        raise SystemExit('preserve')
    labels = {r['id']: r for r in json.loads((SAMPLES / 'labels_all.json').read_text(encoding='utf-8'))}
    commits = json.loads((REPLAY / 'commits_test.json').read_text(encoding='utf-8'))
    gen = [(d, c['base'], c['sha'], labels[d.split('_')[1]]) for d, c in commits.items() if c['sha']]
    truth = [(r['id'], meta(r)['base'], r['commit'], r) for r in labels.values()]

    def one(job):
        name, base, head, r = job
        full = checks.CK.git('rev-parse', head).strip()
        return name, checks.check(base, full, r['target_arch'], r['refs'], r['ref_arch'])

    with ThreadPoolExecutor(max_workers=8) as pool:
        g = dict(pool.map(one, gen))
        t = dict(pool.map(one, truth))
    (HERE / 'checks_generated.json').write_text(json.dumps(g, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'checks_truth.json').write_text(json.dumps(t, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    for name, res in list(g.items()) + list(t.items()):
        if res['flags']:
            print(name, [(f['check'], f['where'], f['what'][:80]) for f in res['flags']])
    print('generated', sum(len(v['flags']) for v in g.values()), 'truth', sum(len(v['flags']) for v in t.values()))


if __name__ == '__main__':
    main()
