"""Check the step-1 claims and write step-2 prompts for items with at least one mismatch (criteria.md section 3).
WSL (git). Output: checks.json, step2_index.json and <CALLS>/S2_<base>/prompt.md.
"""
from pathlib import Path
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import factcheck as F  # noqa: E402

spec = importlib.util.spec_from_file_location('prev_score', HERE.parent / 'llm_review_rule_flags_20261103' / 'score.py')
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)
CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-03' / 'llm_review_factcheck_20261103'
S.CALLS = CALLS


def main():
    if (HERE / 'checks.json').exists():
        raise SystemExit('preserve')
    items = json.loads((HERE / 'items.json').read_text(encoding='utf-8'))
    checks, step2 = [], []
    for it in items:
        a = S.parse(it['dir'])
        claims = (a or {}).get('claims') or []
        results = []
        for c in claims[:5]:
            status, detail = F.check(c, it['rev'])
            results.append({'claim': c, 'status': status, 'detail': detail})
        bad = [r for r in results if r['status'] == 'mismatch']
        checks.append({'dir': it['dir'], 'base': it['base'], 'answered': a is not None,
                       'verdict': (a or {}).get('verdict'), 'claims': results, 'mismatch': len(bad)})
        if bad:
            prompt = (CALLS / it['dir'] / 'prompt.md').read_text(encoding='utf-8').rstrip()
            answer = json.dumps({k: a[k] for k in ('verdict', 'reason', 'lines', 'claims') if k in a}, ensure_ascii=False)
            feedback = '\n'.join(f'- 你写的：{json.dumps(r["claim"], ensure_ascii=False)}\n  核对结果：不符。{r["detail"]}'
                                 for r in bad)
            text = (prompt + '\n\n【你之前的回答】\n' + answer + '\n\n【程序在该版本代码上的核对结果】\n以下事实与代码不符：\n'
                    + feedback + '\n\n请根据核对结果重新判断，按同样格式输出（最后一个JSON对象）。\n')
            d = CALLS / f'S2_{it["base"]}'
            d.mkdir(parents=True)
            (d / 'prompt.md').write_text(text, encoding='utf-8', newline='\n')
            step2.append({'dir': d.name, 'base': it['base']})
    (HERE / 'checks.json').write_text(json.dumps(checks, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'step2_index.json').write_text(json.dumps(step2, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    n = [r['status'] for c in checks for r in c['claims']]
    print('claims', len(n), {s: n.count(s) for s in ('ok', 'mismatch', 'unverifiable')},
          'items with mismatch', len(step2), 'no answer', sum(not c['answered'] for c in checks))


if __name__ == '__main__':
    main()
