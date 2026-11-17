"""L3 prompts (criteria.md section 3): replay_migration_20261105/build_detect.py's detection prompt for each of the
42 generated patches, unchanged except section 5, which now also lists the C1/C2 flags of checks_generated.json and
the facts C2a/C2c collected. WSL (git); no model calls.
Output: <CALLS>/L3_<dir>/prompt.md and l3_index.json.
"""
from pathlib import Path
import importlib.util
import json

HERE = Path(__file__).resolve().parent
REPLAY = HERE.parent / 'replay_migration_20261105'
spec = importlib.util.spec_from_file_location('build_detect', REPLAY / 'build_detect.py')
BD = importlib.util.module_from_spec(spec)
spec.loader.exec_module(BD)
CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-05' / 'migration_checks_20261105'
HEAD = '## 五、程序检查结果（只作参考）'


def section(rules_text, res):
    rows = [f'- {f["check"]} `{f["where"]}`：{f["what"]}' for f in res['flags']]
    facts = [f'- {x}' for x in res['facts']]
    return (HEAD + '\n\n### 规则检查\n\n' + rules_text
            + '\n\n### 迁移检查（同类位置、参照前提；程序给出，可能有误报）\n\n' + ('\n'.join(rows) or '（无标记）')
            + '\n\n### 目标架构事实（程序收集）\n\n' + ('\n'.join(facts) or '（无）') + '\n')


def main():
    if (HERE / 'l3_index.json').exists():
        raise SystemExit('preserve')
    checks = json.loads((HERE / 'checks_generated.json').read_text(encoding='utf-8'))
    index = []
    for x in json.loads((REPLAY / 'detect_index_test.json').read_text(encoding='utf-8')):
        old = (BD.CALLS / x['dir'] / 'prompt.md').read_text(encoding='utf-8')
        start = old.index(HEAD)
        rules_text = old[start + len(HEAD):].strip()
        text = old[:start] + section(rules_text, checks[x['patch']])
        text = text.replace('- 程序检查的结果（如果有）附在第五节，只作参考，可能有误报，也可能漏报。',
                            '- 程序检查的结果和程序收集的目标架构事实附在第五节。程序检查可能有误报，也可能漏报；目标架构事实可以作为依据引用。')
        assert text.count(HEAD) == 1 and old.count('- 程序检查的结果（如果有）附在第五节，只作参考，可能有误报，也可能漏报。') == 1
        d = CALLS / f'L3_{x["patch"]}'
        d.mkdir(parents=True)
        (d / 'prompt.md').write_text(text, encoding='utf-8', newline='\n')
        index.append({'dir': d.name, 'patch': x['patch'], 'id': x['id'], 'cond': x['cond'], 'chars': len(text)})
    (HERE / 'l3_index.json').write_text(json.dumps(index, indent=1) + '\n', encoding='utf-8')
    print(len(index), sum(i['chars'] for i in index) // len(index), max(i['chars'] for i in index))


if __name__ == '__main__':
    main()
