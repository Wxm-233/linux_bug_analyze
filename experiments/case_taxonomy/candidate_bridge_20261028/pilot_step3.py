"""Pilot-2 bridge step 3: parse the model formalizations, validate, and evaluate each candidate twice —
unreviewed (model_proposal claims, expected insufficient) and, only for those listed in
researcher_review.json as faithful, reviewed. Facts come from the step-1 bundle answers."""
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
INNER = HERE.parents[2]
sys.path.insert(0, str(INNER))
from linux_bug_analyze.candidate_bridge import evaluate_candidate, parse_formalizations  # noqa: E402
from linux_bug_analyze.contract_envelope import document  # noqa: E402

CALL = INNER.parent / '模型调用测试/2026-10-28/bridge_formalize_pilot2'


def main():
    target = HERE / 'pilot_results.json'
    if target.exists():
        raise SystemExit('preserve')
    receipt = json.loads((CALL / 'receipt.json').read_text(encoding='utf-8'))
    step1 = json.loads((HERE / 'pilot_bridged.json').read_text(encoding='utf-8'))
    out = {'delivery': receipt.get('status'), 'finish_reasons': receipt.get('finish_reasons'), 'usage': receipt.get('usage'),
           'elapsed_seconds': receipt.get('elapsed_seconds'), 'candidates': []}
    if receipt.get('status') != 'complete_final_received':
        out['result'] = 'delivery_insufficient'
        target.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        print(json.dumps(out, ensure_ascii=False))
        return
    try:
        formal = parse_formalizations((CALL / 'final.md').read_text(encoding='utf-8'))
    except (ValueError, KeyError) as exc:
        out['result'] = 'formalization_unparsable'
        out['error'] = str(exc)[:200]
        target.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        print(json.dumps(out, ensure_ascii=False))
        return
    review_path = HERE / 'researcher_review.json'
    review = json.loads(review_path.read_text(encoding='utf-8')) if review_path.exists() else {}
    docs = {'evidence': document(HERE / 'bundle_pilot2/bundle.json', INNER, 'pilot2_parent')}
    for b in step1['bridged']:
        i = b['candidate']
        facts = {k: v['value'] for k, v in step1['answers'][str(i)].items() if v['answered']}
        f = formal.get(i, {'expressible': False, 'reason': 'missing from model output'})
        row = {'candidate': i, 'formalization': f,
               'unreviewed': evaluate_candidate(f, facts, context=f'pilot2.c{i}', revision='pilot2_parent', basis='compiled_object',
                                                documents=docs, reviewed=False)}
        verdict = review.get(str(i))
        row['researcher_review'] = verdict
        if verdict and verdict.get('faithful'):
            row['reviewed'] = evaluate_candidate(f, facts, context=f'pilot2.c{i}', revision='pilot2_parent', basis='compiled_object',
                                                 documents=docs, reviewed=True)
        out['candidates'].append(row)
    out['result'] = 'evaluated'
    target.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    for r in out['candidates']:
        print(r['candidate'], r['formalization'].get('expressible'), r['unreviewed'].get('status'), r['unreviewed'].get('relation_at_observation'),
              (r.get('reviewed') or {}).get('relation_at_observation'), (r['researcher_review'] or {}).get('faithful'))


if __name__ == '__main__':
    main()
