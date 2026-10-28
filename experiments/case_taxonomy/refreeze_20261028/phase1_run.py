"""Phase-1 driver (addendum 2): run the frozen E4 method on the 10 phase-1 samples and their normal controls.

Labels: s01..s10 for samples (frozen order), c01..c10 for the control of the same sample (controls marked
normal_insufficient are skipped). The runner's own output (which names commits) goes to phase1_runner.log;
the console shows label and counts only, so nothing about a sample is displayed before its outputs are saved.
"""
from pathlib import Path
import contextlib
import importlib.util
import io
import json
import time

HERE = Path(__file__).resolve().parent
spec_ = importlib.util.spec_from_file_location('m2c_eval', HERE / 'm2c_eval.py')
ev = importlib.util.module_from_spec(spec_)
spec_.loader.exec_module(ev)


def counts(label):
    r = json.loads((HERE / 'runs' / label / 'results.json').read_text())
    if 'summary' not in r:
        return {'status': r['status']}
    s = r['summary']
    return {'instances': s['instances'], 'parent_only': len(s['parent_only']), 'fix_only': len(s['fix_only']),
            'both': len(s['both']), 'labels': s['labels'], 'builds_failed': s['builds_failed']}


def main():
    sel = json.loads((HERE / 'selection.json').read_text())
    jobs = [('s%02d' % (n + 1), r['commit']) for n, r in enumerate(sel['phase1'])]
    jobs += [('c%02d' % (n + 1), c['control']) for n, c in enumerate(sel['controls']) if c['status'] == 'ok']
    log = HERE / 'phase1_runner.log'
    for label, commit in jobs:
        if (HERE / 'runs' / label / 'results.json').exists():
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
            (HERE / 'runs' / label).mkdir(parents=True, exist_ok=True)
            (HERE / 'runs' / label / 'results.json').write_text(json.dumps({'status': 'runner_error', 'error': repr(exc)[:500]}) + '\n')
        with log.open('a') as fh:
            fh.write('== %s %s %.0fs\n%s\n' % (label, status, time.time() - started, buf.getvalue()))
        print(label, status, '%.0fs' % (time.time() - started), json.dumps(counts(label)), flush=True)


if __name__ == '__main__':
    main()
