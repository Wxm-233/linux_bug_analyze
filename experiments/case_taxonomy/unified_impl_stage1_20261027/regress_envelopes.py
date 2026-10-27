"""Regression (attempt3 adds observation_binding_extra; attempt2: compare only contract/ledger/record; reasons included): every saved envelope is rebuilt from its extracted parameters by the shared builder;
compare canonical JSON and core decisions. Read-only over the archives."""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
INNER = HERE.parents[2]
sys.path.insert(0, str(INNER))
from linux_bug_analyze.contract_envelope import build_envelope, envelope_spec  # noqa: E402
from linux_bug_analyze.contract_protocol import evaluate_contract  # noqa: E402


def canonical(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False)


def items(o):
    if isinstance(o, dict):
        if {'contract', 'ledger', 'record'} <= set(o):
            yield o
            return
        for v in o.values():
            yield from items(v)
    elif isinstance(o, list):
        for v in o:
            yield from items(v)


def decide(it):
    synthetic = it['record'].get('basis') == 'synthetic' or it['ledger'].get('basis') == 'synthetic'
    return evaluate_contract(it['contract'], it['ledger'], it['record'], allow_synthetic=synthetic)


def main():
    target = HERE / 'envelope_regression.json'
    if target.exists():
        raise SystemExit('preserve envelope_regression.json')
    per_file, totals = {}, Counter()
    for path in sorted((INNER / 'experiments').rglob('*.json')):
        if HERE in path.parents or path.stat().st_size > 60_000_000:
            continue
        try:
            obj = json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            continue
        found = list(items(obj))
        if not found:
            continue
        control = 'control' in path.as_posix().lower()
        row = Counter()
        failures = []
        for it in found:
            totals['items'] += 1
            row['items'] += 1
            try:
                rebuilt = build_envelope(envelope_spec(it))
            except (KeyError, ValueError, TypeError) as exc:
                row['spec_error'] += 1
                failures.append({'contract_id': it['contract'].get('id'), 'error': repr(exc)[:200]})
                continue
            part = {k: it[k] for k in ('contract', 'ledger', 'record')}
            exact = canonical(rebuilt) == canonical(part)
            row['exact' if exact else 'structural_diff'] += 1
            a, b = decide(it), decide(rebuilt)
            keys = ('applicability', 'relation_at_observation', 'relation_at_deadline', 'whole_path', 'reasons')
            same = all(a[k] == b[k] for k in keys)
            row['decision_same' if same else 'decision_diff'] += 1
            if not exact or not same:
                failures.append({'contract_id': it['contract'].get('id'), 'exact': exact, 'decision_same': same,
                                 'original': [a[k] for k in keys[:4]], 'rebuilt': [b[k] for k in keys[:4]],
                                 'reason_orig': a['reasons'][:1], 'reason_rebuilt': b['reasons'][:1]})
        rel = path.relative_to(INNER).as_posix()
        per_file[rel] = {'control_file': control, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                         **dict(row), 'failures': failures[:10]}
        for k, v in row.items():
            totals[('control_' if control else 'main_') + k] += v
    out = {'files': len(per_file), 'totals': dict(totals), 'per_file': per_file}
    target.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'files': len(per_file), 'totals': dict(totals)}, ensure_ascii=False))
    for rel, row in per_file.items():
        if row['failures']:
            print(rel, {k: v for k, v in row.items() if k not in ('failures', 'sha256')}, row['failures'][:2])


if __name__ == '__main__':
    main()
