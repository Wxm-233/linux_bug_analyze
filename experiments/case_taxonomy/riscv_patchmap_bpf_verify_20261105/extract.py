"""results.json from logs/<kind>.log (criteria.md section 3). The serial console interleaves kernel printk records
with the test's output, so printk records ("[ seconds] ...") are cut out before the BPF-TEST lines are read; the
WARNING lines are counted on the raw log. Windows Python.
"""
from pathlib import Path
import json
import re

HERE = Path(__file__).resolve().parent


def main():
    out = {}
    for kind in ('observe', 'control', 'fixed'):
        raw = (HERE / 'logs' / f'{kind}.log').read_text(encoding='utf-8', errors='replace')
        user = re.sub(r'\[\s*\d+\.\d+\][^\n]*\n', '', raw)
        loads = [{'load': int(m.group(1)), 'jited_prog_len': int(m.group(2))}
                 for m in re.finditer(r'BPF-TEST load (\d) fd=\d+ jited_prog_len=(\d+)', user)]
        warnings = re.findall(r'WARNING: ([^\n]*)', raw)
        out[kind] = {'loads': loads, 'load_failures': len(re.findall(r'BPF-TEST load \d failed', user)),
                     'warnings': warnings, 'done': 'BPF-TEST done' in user}
    o, c, f = out['observe'], out['control'], out['fixed']
    ok = lambda r: len(r['loads']) == 3 and all(x['jited_prog_len'] > 0 for x in r['loads']) and not r['warnings']
    observe_fails = len(o['loads']) == 3 and (all(x['jited_prog_len'] == 0 for x in o['loads']) or o['warnings'])
    out['verdict'] = 'holds' if observe_fails and ok(c) and ok(f) else \
        'does_not_hold' if ok(o) else 'undecided'
    (HERE / 'results.json').write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
