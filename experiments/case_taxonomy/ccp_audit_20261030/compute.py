"""Coverage by blind follow_up label (criteria.md step 2). Run after audit_30.json SHA is recorded. Output: stats.json."""
from pathlib import Path
import json
import statistics

HERE = Path(__file__).resolve().parent
pool = {(p['seed'], p['target']): p for p in json.loads((HERE.parent / 'ccp_feasibility_20261030' / 'ccp_pool.json').read_text())['pairs']}
labels = json.loads((HERE / 'audit_30.json').read_text(encoding='utf-8'))['labels']
rows = []
for l in labels:
    p = pool[(l['seed'], l['target'])]
    rows.append({**{k: l[k] for k in ('n', 'follow_up', 'contract_kind')},
                 **{k: p[k] for k in ('linked', 'interface_ids', 'pool', 'cov_20', 'cov_50', 'cov_all')}})


def summary(rs):
    if not rs:
        return None
    return {'pairs': len(rs), **{k: sum(r[k] for r in rs) for k in ('cov_20', 'cov_50', 'cov_all', 'linked')},
            'pool_median': statistics.median(r['pool'] for r in rs)}


groups = {g: summary([r for r in rows if r['follow_up'] == g]) for g in ('yes', 'partial', 'no')}
groups['all'] = summary(rows)
yes_missed = [r for r in rows if r['follow_up'] == 'yes' and not r['cov_all']]
out = {'labels': {g: groups[g]['pairs'] if groups[g] else 0 for g in ('yes', 'partial', 'no')}, 'by_label': groups,
       'yes_by_linked': {str(v): summary([r for r in rows if r['follow_up'] == 'yes' and r['linked'] == v]) for v in (True, False)},
       'yes_missed': yes_missed, 'rows': rows}
(HERE / 'stats.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print(json.dumps({k: out[k] for k in ('labels', 'by_label', 'yes_by_linked')}, ensure_ascii=False))
print('yes_missed', [(r['n'], r['linked'], r['interface_ids'], r['pool']) for r in yes_missed])
