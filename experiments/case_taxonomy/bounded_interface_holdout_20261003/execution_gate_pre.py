"""One-shot parent execution and fail-closed patch-unseal gate.

Supplemental execution guard. Does not change frozen selection or rules.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
RULES = HERE.parent


def now():
    return datetime.now(timezone.utc).isoformat()


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, obj):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(obj, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def check_lock(filename):
    lock = read(HERE / filename)
    for item in lock['files']:
        path = (HERE / item['path']).resolve()
        require(path.is_relative_to(RULES.resolve()) and sha(path) == item['sha256'], 'lock mismatch ' + filename)
    return lock


def seal():
    check_lock('freeze_pre.json')
    require(not (HERE / 'parents_lock.json').exists() and not (HERE / 'parents_started.json').exists(),
            'cannot seal gate after parent execution')
    save(HERE / 'execution_gate_lock_pre.json', dict(sealed_at_utc=now(),
        scope='Supplemental pre-parent one-shot/failure guard; original runner and selection unchanged.',
        files=[dict(path=name, sha256=sha(HERE / name)) for name in (
            'execution_gate_pre.py', 'execution_gate_policy_pre.md', 'freeze_pre.json')]))


def run_phase(phase):
    result = subprocess.run(['python3', '-B', str(HERE / 'run_holdout.py'), phase], capture_output=True, check=False)
    record = dict(argv=['python3', '-B', str(HERE / 'run_holdout.py'), phase], returncode=result.returncode,
                  completed_at_utc=now())
    for stream in ('stdout', 'stderr'):
        relative = f'gate_{phase}.{stream}.bin'
        with (HERE / relative).open('xb') as output:
            output.write(getattr(result, stream))
        record[stream] = relative
        record[stream + '_sha256'] = sha(HERE / relative)
    save(HERE / f'gate_{phase}_command.json', record)
    require(result.returncode == 0, 'original runner failed, no retry or unseal')
    print(result.stdout.decode('utf-8'))


def parents():
    check_lock('freeze_pre.json')
    check_lock('execution_gate_lock_pre.json')
    items = read(HERE / 'selection.json')['selected']
    require(0 < len(items) <= 2, 'empty selection stops without rule execution')
    forbidden = ['parents_started.json', 'parents_lock.json', 'commands_parents.json', 'gate_parents_command.json']
    forbidden += [item['role'] + '/raw/parent.json' for item in items]
    require(all(not (HERE / name).exists() for name in forbidden), 'parent execution already attempted')
    require(not (HERE / 'commands/parents').exists(), 'parent capture directory already exists')
    save(HERE / 'parents_started.json', dict(started_at_utc=now(),
        gate_lock_sha256=sha(HERE / 'execution_gate_lock_pre.json'), selected_count=len(items), no_retry=True))
    run_phase('parents')


def unseal():
    check_lock('freeze_pre.json')
    check_lock('execution_gate_lock_pre.json')
    parent = check_lock('parents_lock.json')
    selection = read(HERE / 'selection.json')['selected']
    summaries = parent['summaries']
    require(0 < len(selection) <= 2 and len(summaries) == len(selection), 'parent attempt count')
    require(read(HERE / 'gate_parents_command.json')['returncode'] == 0, 'parent wrapper succeeded')
    require(parent['patch_unsealed'] is False, 'parent lock must precede patch')
    for item in selection:
        found = [entry for entry in summaries if entry['role'] == item['role']]
        require(len(found) == 1 and found[0]['returncode'] == 0 and found[0]['raw_path'], 'parent CLI/raw failure')
        entry = found[0]
        path = (HERE / entry['raw_path']).resolve()
        require(path.is_relative_to(HERE) and sha(path) == entry['raw_sha256'], 'parent output SHA')
        raw = read(path)
        require(raw['revision'] == item['parent'] and raw['source_file'] == item['source_file'], 'parent output identity')
        require(raw['counts'] == entry['counts'] and set(raw['counts']) == {'candidate', 'normal', 'insufficient'},
                'parent output schema/counts')
    forbidden = ['unseal_started.json', 'unseal_authorization.json', 'unseal_manifest.json',
                 'commands_unseal.json', 'gate_unseal_command.json']
    forbidden += [item['role'] + suffix for item in selection for suffix in ('/raw/fixed.json', '/patch_unsealed.txt')]
    require(all(not (HERE / name).exists() for name in forbidden) and not (HERE / 'commands/unseal').exists(),
            'unseal already attempted')
    save(HERE / 'unseal_authorization.json', dict(authorized_at_utc=now(), allowed=True,
        parent_lock_sha256=sha(HERE / 'parents_lock.json'), all_parent_returncodes_zero=True,
        all_raw_identity_and_hash_checked=True, parent_count=len(selection), semantic_label_not_preassigned=True))
    save(HERE / 'unseal_started.json', dict(started_at_utc=now(), no_retry=True,
                                          gate_lock_sha256=sha(HERE / 'execution_gate_lock_pre.json')))
    run_phase('unseal')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('seal', 'parents', 'unseal'))
    args = parser.parse_args()
    {'seal': seal, 'parents': parents, 'unseal': unseal}[args.phase]()
