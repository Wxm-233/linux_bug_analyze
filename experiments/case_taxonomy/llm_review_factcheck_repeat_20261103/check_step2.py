"""Check the step-1 claims of runs 2-5 with llm_review_factcheck_20261103/factcheck.py (imported, unchanged) and write
the step-2 prompts in the same format as that round (criteria.md section 1). WSL (git).
Output: checks.json, step2_index.json and <CALLS>/S2_<run dir>/prompt.md.
"""
from pathlib import Path
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
PREV = HERE.parent / 'llm_review_factcheck_20261103'
sys.path.insert(0, str(PREV))
import factcheck as F  # noqa: E402

spec = importlib.util.spec_from_file_location('prev_score', HERE.parent / 'llm_review_rule_flags_20261103' / 'score.py')
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)
CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-03' / 'llm_review_factcheck_repeat_20261103'
S.CALLS = CALLS


def main():
    if (HERE / 'checks.json').exists():
        raise SystemExit('preserve')
    checks, step2 = [], []
    for it in json.loads((HERE / 'items.json').read_text(encoding='utf-8')):
        a = S.parse(it['dir'])
        results = []
        for c in ((a or {}).get('claims') or [])[:5]:
            status, detail = F.check(c, it['rev'])
            results.append({'claim': c, 'status': status, 'detail': detail})
        bad = [r for r in results if r['status'] == 'mismatch']
        checks.append({'dir': it['dir'], 'answered': a is not None, 'verdict': (a or {}).get('verdict'),
                       'claims': results, 'mismatch': len(bad)})
        if bad:
            prompt = (CALLS / it['dir'] / 'prompt.md').read_text(encoding='utf-8').rstrip()
            answer = json.dumps({k: a[k] for k in ('verdict', 'reason', 'lines', 'claims') if k in a}, ensure_ascii=False)
            feedback = '\n'.join(f'- 你写的：{json.dumps(r["claim"], ensure_ascii=False)}\n  核对结果：不符。{r["detail"]}'
                                 for r in bad)
            text = (prompt + '\n\n【你之前的回答】\n' + answer + '\n\n【程序在该版本代码上的核对结果】\n以下事实与代码不符：\n'
                    + feedback + '\n\n请根据核对结果重新判断，按同样格式输出（最后一个JSON对象）。\n')
            d = CALLS / f'S2_{it["dir"]}'
            d.mkdir(parents=True)
            (d / 'prompt.md').write_text(text, encoding='utf-8', newline='\n')
            step2.append({'dir': d.name, 'run_dir': it['dir']})
    (HERE / 'checks.json').write_text(json.dumps(checks, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'step2_index.json').write_text(json.dumps(step2, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    n = [r['status'] for c in checks for r in c['claims']]
    print('claims', len(n), {s: n.count(s) for s in ('ok', 'mismatch', 'unverifiable')}, 'step-2 prompts', len(step2),
          'no answer', sum(not c['answered'] for c in checks))


if __name__ == '__main__':
    main()
