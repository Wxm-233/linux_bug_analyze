"""Set-C driver (addendum 3b): the frozen M3a runner (m3a_20261028/m3a_eval.py, unchanged) on the 20 set-C samples and their
normal controls. Labels C_s01..s20 / C_c01..c20 (controls marked normal_insufficient are skipped); outputs land in
m3a_20261028/runs/<label>/. The runner's own output (which names commits) goes to set_c_runner.log; the console shows
label and counts only.
"""
from pathlib import Path
import contextlib
import importlib.util
import io
import json
import time

HERE = Path(__file__).resolve().parent
FROZEN = HERE.parent / 'm3a_20261028'
spec_ = importlib.util.spec_from_file_location('m3a_eval', FROZEN / 'm3a_eval.py')
ev = importlib.util.module_from_spec(spec_)
spec_.loader.exec_module(ev)


def counts(label):
    r = json.loads((FROZEN / 'runs' / label / 'results.json').read_text())
    if 'summary' not in r:
        return {'status': r['status']}
    s = r['summary']
    return {'instances': s['instances'], 'parent_only': len(s['parent_only']), 'fix_only': len(s['fix_only']), 'both': len(s['both']),
            'by_family': s['by_family'], 'labels': s['labels']}


def main():
    sel = json.loads((HERE / 'topup_selection.json').read_text())
    controls = {c['for']: c for c in sel['controls']}
    jobs = [('C_s%02d' % (n + 1), s['commit']) for n, s in enumerate(sel['set_c'])]
    jobs += [('C_c%02d' % (n + 1), controls[s['commit']]['control']) for n, s in enumerate(sel['set_c']) if controls[s['commit']]['status'] == 'ok']
    log = HERE / 'set_c_runner.log'
    for label, commit in jobs:
        if (FROZEN / 'runs' / label / 'results.json').exists():
            print(label, 'done', json.dumps(counts(label)), flush=True)
            continue
        started = time.time()
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                ev.run(commit, label)
            status = 'ok'
        except Exception as exc:  # recorded, not retried
            status = 'error: ' + repr(exc)[:200]
            (FROZEN / 'runs' / label).mkdir(parents=True, exist_ok=True)
            (FROZEN / 'runs' / label / 'results.json').write_text(json.dumps({'status': 'runner_error', 'error': repr(exc)[:500]}) + '\n')
        with log.open('a') as fh:
            fh.write('== %s %s %.0fs\n%s\n' % (label, status, time.time() - started, buf.getvalue()))
        print(label, status, '%.0fs' % (time.time() - started), json.dumps(counts(label)), flush=True)


if __name__ == '__main__':
    main()
