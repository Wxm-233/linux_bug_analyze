"""Post-hoc miss diagnosis (criteria.md step 3): for yes pairs not covered by any candidate, which of C's identifiers
appear in the target function at snapshot C (with doc freq), and which C identifiers T's arch edits mention. WSL. Output: miss_diag.json."""
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'ccp_feasibility_20261030'))
import count_ccp as CC  # noqa: E402

stats = json.loads((HERE / 'stats.json').read_text(encoding='utf-8'))
labels = {l['n']: l for l in json.loads((HERE / 'audit_30.json').read_text(encoding='utf-8'))['labels']}
pool = {(p['seed'], p['target']): p for p in json.loads((HERE.parent / 'ccp_feasibility_20261030' / 'ccp_pool.json').read_text())['pairs']}
out = []
for r in stats['yes_missed']:
    l = labels[r['n']]
    c, t = l['seed'], l['target']
    p = pool[(c, t)]
    ids_all = CC.idents([x for ls in CC.diff_lines(c, True).values() for x in ls])
    t_lines = [x for path, ls in CC.diff_lines(t, False).items() if CC.X.arch_of(path) not in set(p['c_arches']) for x in ls]
    t_words = set(CC.WORD.findall('\n'.join(t_lines)))
    body_words, found = set(), []
    for f, name in p['targets']:
        text = CC.P['blobs'](['%s:%s' % (c, f)]).get('%s:%s' % (c, f)) or ''
        lines = text.splitlines()
        for s, e, nm in CC.named_spans(text):
            if nm == name:
                found.append([f, name])
                body_words |= set(CC.WORD.findall('\n'.join(lines[s - 1:e])))
    in_body = ids_all & body_words
    in_t = ids_all & t_words
    df = CC.doc_freq(c, in_body | in_t) if in_body | in_t else {}
    out.append({'n': r['n'], 'interface_ids_kept': p['interface_ids'], 'pool': p['pool'], 'targets_found_at_c': found,
                'c_ids_in_target_body': {k: df.get(k, 0) for k in sorted(in_body)},
                'c_ids_in_t_edits': {k: df.get(k, 0) for k in sorted(in_t)}})
    print(out[-1], flush=True)
(HERE / 'miss_diag.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
