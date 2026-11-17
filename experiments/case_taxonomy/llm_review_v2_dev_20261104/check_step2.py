"""Check every step-1 answer (criteria.md section 2): claims through factcheck2.check, and a not_issue verdict through
factcheck2.refute_ok. An answer with a mismatching claim or an unsupported not_issue gets one follow-up prompt in the
format of llm_review_factcheck_repeat_20261103/check_step2.py plus the refute feedback. WSL (git).
Output: checks.json, step2_index.json and <CALLS>/S2_<dir>/prompt.md."""
from pathlib import Path
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import factcheck2 as F2  # noqa: E402

spec = importlib.util.spec_from_file_location('prev_score', HERE.parent / 'llm_review_rule_flags_20261103' / 'score.py')
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)
CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-04' / 'llm_review_v2_dev_20261104'
S.CALLS = CALLS


def judge(a, it):
    """(claim results, verdict, refute accepted or None, why) for one parsed answer."""
    results = []
    for c in ((a or {}).get('claims') or [])[:5]:
        status, detail = F2.check(c, it['rev'])
        results.append({'claim': c, 'status': status, 'detail': detail})
    v = str((a or {}).get('verdict', 'unsure')).strip().lower()
    acc, why = (F2.refute_ok(a, results, {f['id'] for f in it['facts']}) if v == 'not_issue' else (None, ''))
    return results, v, acc, why


def main():
    if (HERE / 'checks.json').exists():
        raise SystemExit('preserve')
    checks, step2 = [], []
    for it in json.loads((HERE / 'items.json').read_text(encoding='utf-8')):
        a = S.parse(it['dir'])
        results, v, acc, why = judge(a, it)
        bad = [r for r in results if r['status'] == 'mismatch']
        checks.append({'dir': it['dir'], 'cand': it['cand'], 'answered': a is not None, 'verdict': v, 'claims': results,
                       'refute': (a or {}).get('refute'), 'refute_accepted': acc, 'refute_why': why})
        if bad or acc is False:
            prompt = (CALLS / it['dir'] / 'prompt.md').read_text(encoding='utf-8').rstrip()
            answer = json.dumps({k: a[k] for k in ('verdict', 'reason', 'lines', 'claims', 'refute') if k in a},
                                ensure_ascii=False)
            parts = [prompt, '', '【你之前的回答】', answer, '', '【程序在该版本代码上的核对结果】']
            if bad:
                parts.append('以下事实与代码不符：')
                parts += [f'- 你写的：{json.dumps(r["claim"], ensure_ascii=False)}\n  核对结果：不符。{r["detail"]}' for r in bad]
            if acc is False:
                parts.append(f'你判为not_issue，但{why}。按要求，没有核对相符的依据就不能判not_issue。')
            parts += ['', '请根据核对结果重新判断，按同样格式输出（最后一个JSON对象）。']
            d = CALLS / f'S2_{it["dir"]}'
            d.mkdir(parents=True)
            (d / 'prompt.md').write_text('\n'.join(parts) + '\n', encoding='utf-8', newline='\n')
            step2.append({'dir': d.name, 'run_dir': it['dir']})
    (HERE / 'checks.json').write_text(json.dumps(checks, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'step2_index.json').write_text(json.dumps(step2, indent=1) + '\n', encoding='utf-8')
    st = [r['status'] for c in checks for r in c['claims']]
    print('claims', len(st), {s: st.count(s) for s in ('ok', 'mismatch', 'unverifiable')},
          'not_issue', sum(c['verdict'] == 'not_issue' for c in checks),
          'refute rejected', sum(c['refute_accepted'] is False for c in checks), 'step-2 prompts', len(step2),
          'no answer', sum(not c['answered'] for c in checks))


if __name__ == '__main__':
    main()
