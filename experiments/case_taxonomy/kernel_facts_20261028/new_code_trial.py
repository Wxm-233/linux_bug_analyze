"""Support-domain measurement on new (pilot, contacted, not evaluated) code: map each line cited by the
pilot-2 model candidates to its enclosing top-level function in the parent file, collect a generic fact
bundle for those functions, and count which facts are obtainable. No candidate is judged (run in WSL)."""
from pathlib import Path
import json
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
INNER = HERE.parents[2]
sys.path.insert(0, str(INNER))
from linux_bug_analyze.gimple_cfg_facts import analyze_cfg  # noqa: E402
from linux_bug_analyze.kernel_facts import collect, query  # noqa: E402

PREP = HERE.parent / 'eval_prep_20261028'
CALL = INNER.parent / '模型调用测试/2026-10-28/e1_pilot_2'


def spans(text):
    """Top-level brace spans with the identifier before the opening '(' of the header."""
    out, depth, start, header = [], 0, None, ''
    lines = text.splitlines()
    for n, line in enumerate(lines, 1):
        code = re.sub(r'//.*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', '', line)
        if depth == 0 and '{' in code:
            window = ' '.join(lines[max(0, n - 4):n])
            m = re.findall(r'\b([A-Za-z_]\w*)\s*\([^;{}]*\)\s*(?:__\w+\s*)*\{?\s*$', window.split('{')[0] + ' {')
            start, header = n, (m[-1] if m else None)
        depth += code.count('{') - code.count('}')
        if depth == 0 and start is not None:
            out.append((start, n, header))
            start = None
    return out


def main():
    target = HERE / 'new_code_trial.json'
    if target.exists():
        raise SystemExit('preserve')
    meta = json.loads((PREP / 'e1_pilot_prompts.json').read_text())[1]
    path = re.findall(r'^=== FILE: (.+) ===$', (CALL / 'prompt.md').read_text(encoding='utf-8'), re.M)[0]
    final = (CALL / 'final.md').read_text(encoding='utf-8')
    cands = json.loads(final[final.find('{'):final.rfind('}') + 1])['candidates']
    src = subprocess.run(['git', '-C', '/root/repos/linux', 'show', meta['parent'] + ':' + path], capture_output=True, text=True).stdout
    fns = spans(src)
    cited = []
    for i, c in enumerate(cands):
        for role in ('provider', 'consumer'):
            line = c[role]['line']
            enclosing = [h for s, e, h in fns if s <= line <= e and h]
            cited.append({'candidate': i, 'role': role, 'line': line, 'function': enclosing[0] if enclosing else None})
    functions = sorted({x['function'] for x in cited if x['function']})
    spec = {'revision': meta['parent'], 'arch': 'x86_64', 'defconfig': 'x86_64_defconfig', 'config_set': {},
            'files': [path], 'functions': functions}
    (HERE / 'specs').mkdir(exist_ok=True)
    (HERE / 'specs/new_code_pilot2.json').write_text(json.dumps(spec, indent=1) + '\n')
    collect(spec, HERE / 'bundles/new_code_pilot2')
    bundle = json.loads((HERE / 'bundles/new_code_pilot2/bundle.json').read_text(encoding='utf-8'))
    entry = bundle['files'][path]
    per = {}
    for f in functions:
        rec = (entry.get('cfg_records') or {}).get(f)
        cfg = analyze_cfg({'id': f, 'path': path, 'revision': bundle['revision'], 'text': rec}, real_kernel=True) if rec else None
        lines = entry.get('functions', {}).get(f, [])
        per[f] = {'defined_in_object': query(bundle, {'kind': 'defined', 'function': f})[1],
                  'relocation_targets': len({re.search(r'R_\w+\s+(\S+)', l).group(1) for l in lines if re.search(r'R_\w+\s+\S+', l)}),
                  'preprocessed_body': bool((entry.get('bodies') or {}).get(f)),
                  'cfg_record': bool(rec), 'cfg_parsed': bool(cfg and cfg['status'] == 'compiler_normal_graph_facts'),
                  'cfg_reason': None if not cfg else (cfg['unknowns'][0]['reason'] if cfg['unknowns'] else cfg['status'])}
    out = {'commit_role': 'pilot (contacted, not evaluated)', 'file': path, 'arch_config': 'x86_64_defconfig',
           'build_returncode': entry.get('build_returncode'), 'cited_references': len(cited),
           'cited_mapped_to_function': sum(1 for x in cited if x['function']), 'distinct_functions': len(functions),
           'per_function': per,
           'summary': {k: sum(1 for v in per.values() if v[k]) for k in ('defined_in_object', 'preprocessed_body', 'cfg_record', 'cfg_parsed')}}
    target.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: out[k] for k in ('build_returncode', 'cited_references', 'cited_mapped_to_function', 'distinct_functions', 'summary')}))
    for f, v in per.items():
        print(f, v)


if __name__ == '__main__':
    main()
