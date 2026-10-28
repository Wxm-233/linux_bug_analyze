"""Phase-A driver (addendum 3): the frozen E4 runner (refreeze_20261028/m2c_eval.py, unchanged) on the first 10 scoped
samples and their normal controls. Labels scA_s01..s10 / scA_c01..c10 (controls marked normal_insufficient are skipped);
outputs land in refreeze_20261028/runs/<label>/. The runner's own output (which names commits) goes to
phase_a_runner.log; the console shows label and counts only.
"""
from pathlib import Path
import contextlib
import importlib.util
import io
import json
import time

HERE = Path(__file__).resolve().parent
FROZEN = HERE.parent / 'refreeze_20261028'
spec_ = importlib.util.spec_from_file_location('m2c_eval', FROZEN / 'm2c_eval.py')
ev = importlib.util.module_from_spec(spec_)
spec_.loader.exec_module(ev)


def counts(label):
    r = json.loads((FROZEN / 'runs' / label / 'results.json').read_text())
    if 'summary' not in r:
        return {'status': r['status']}
    s = r['summary']
    return {'instances': s['instances'], 'parent_only': len(s['parent_only']), 'fix_only': len(s['fix_only']),
            'both': len(s['both']), 'labels': s['labels'], 'builds_failed': s['builds_failed']}


def main():
    sel = json.loads((HERE / 'scoped_selection.json').read_text())
    phase_a = sel['phase_a']
    controls = {c['for']: c for c in sel['controls']}
    jobs = [('scA_s%02d' % (n + 1), h) for n, h in enumerate(phase_a)]
    jobs += [('scA_c%02d' % (n + 1), controls[h]['control']) for n, h in enumerate(phase_a) if controls[h]['status'] == 'ok']
    log = HERE / 'phase_a_runner.log'
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
