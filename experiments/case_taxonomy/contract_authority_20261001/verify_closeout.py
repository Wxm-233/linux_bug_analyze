"""Verify saved authority-stage evidence and its unchanged prior baselines.

No compiler, controller, Git network or model is called. --freeze is a one-time
post-development lock; it is not a successful independent holdout experiment.
"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
RULES=HERE.parent
PRIOR=RULES/'contract_assertions_20261001'
sys.path.insert(0,str(RULES))
from authority_gate import evaluate
from run_provider_projection import verify_rows


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save_once(path,value):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2)
        stream.write('\n')


def safe(relative):
    path=(RULES/relative).resolve()
    if not path.is_relative_to(RULES.resolve()):
        raise ValueError('path escapes case_taxonomy')
    return path


def record(path):
    return dict(path=path.relative_to(RULES).as_posix(),sha256=sha(path))


def closure(roots):
    found,todo=set(),list(roots)
    search=[HERE,RULES,HERE/'source_authority',HERE/'selection',HERE/'gate_audit']
    while todo:
        path=todo.pop().resolve()
        if path in found:
            continue
        found.add(path)
        if path.suffix!='.py':
            continue
        tree=ast.parse(path.read_text(encoding='utf-8-sig'))
        for node in ast.walk(tree):
            names=[item.name for item in node.names] if isinstance(node,ast.Import) else (
                [node.module] if isinstance(node,ast.ImportFrom) and node.module else [])
            for name in names:
                for directory in search:
                    candidate=directory/(name.replace('.','/')+'.py')
                    if candidate.is_file():
                        todo.append(candidate)
                        break
    return found


def check(records):
    verified=[]
    for item in records:
        assert sha(safe(item['path']))==item['sha256'],item['path']
        verified.append(item)
    return verified


def freeze():
    assert (HERE/'gate_audit/final_audit.json').is_file()
    files=set()
    for path in HERE.rglob('*'):
        relative=path.relative_to(HERE)
        if (not path.is_file() or any(part in ('__pycache__','development') for part in relative.parts)
                or path.name in ('freeze_manifest.json','completion_manifest.json','root_test_run.json')):
            continue
        files.add(path.resolve())
    files |= closure([path for path in files if path.suffix=='.py'])
    files.add((PRIOR/'freeze_manifest.json').resolve())
    files.add((PRIOR/'completion_manifest.json').resolve())
    save_once(HERE/'freeze_manifest.json',dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),
        scope='Final known-source review/gate development. Selection is empty; independent detector not executed.',
        import_closure='Static visible local imports, including development fixtures.',
        preserved_but_not_current_code_proof=['development/','root_test_run.json'],
        files=[record(path) for path in sorted(files)]))


def verify(require_freeze=True):
    new=check(read(HERE/'freeze_manifest.json')['files']) if require_freeze else []
    old=check(read(PRIOR/'freeze_manifest.json')['files'])
    old_raw=check(read(PRIOR/'completion_manifest.json')['verified_old_raw_reports'])
    ancestry=[]
    for stage in ('structured_payload_20261001','outbound_scalar_20260930'):
        ancestry.extend(check(read(RULES/stage/'freeze_manifest.json')['files']))
    tests=read(HERE/'root_test_final_lock.json')
    assert tests['returncode']==0 and tests['code_unchanged_during_test']
    for name,digest in tests['tested_files'].items():
        assert sha(HERE/name)==digest
    development=read(HERE/'development_final_lock/results.json')
    assert development['gate_unchanged_during_run']
    assert development['gate_sha256']==sha(HERE/'authority_gate.py')
    assert development['runner_sha256']==sha(HERE/'run_gate_development.py')
    plan_path=PRIOR/'final_run_01/parent_plan.json'
    assert sha(plan_path)==development['input_plan_sha256']
    plan=read(plan_path)
    files=read(HERE/'development_final_lock/source_files.json')
    for name,filename in (('local_source_review','local_source_card.json'),
                          ('historical_external_pending','external_history_card.json')):
        actual=evaluate(plan,read(HERE/'development_final_lock'/filename),files)
        assert actual==development['outputs'][name]
    for result in development['outputs'].values():
        assert all(result[key] is False for key in ('machine_contract_proven','runtime_reachability_proven',
                                                    'full_kernel_proven','external_protocol_proven'))
    source=read(HERE/'source_authority/evidence.json')
    source_checks=[]
    for item in source['sources']:
        text=item['full_text'].encode('utf-8')
        assert hashlib.sha256(text).hexdigest()==item['full_file_sha256']
        assert hashlib.sha1(b'blob '+str(len(text)).encode()+b'\0'+text).hexdigest()==item['git_blob_sha1']
        raw=HERE/'source_authority'/item['raw_file']
        # The evidence stores a path relative to source_authority.
        assert raw.read_bytes()==text
        source_checks.append(dict(path=item['path'],sha256=item['full_file_sha256'],blob=item['git_blob_sha1']))
    projection=read(HERE/'provider_projection/results.json')
    assert projection['runner_sha256']==sha(HERE/'run_provider_projection.py')
    assert projection['source_sha256']==sha(HERE/'provider_projection/chain.c')
    for relative,digest in projection['input_hashes'].items():
        assert sha(safe(relative))==digest
    projected=[]
    for label,target in projection['targets'].items():
        endian={'x86_64':'little','s390x':'big'}[label]
        assert verify_rows(target['rows'],endian)==target['summary']
        commands=[cmd for cmd in projection['commands'] if cmd['argv'][-1].endswith('/'+label)
                  and '-o' not in cmd['argv']]
        assert len(commands)==1 and commands[0]['returncode']==0
        assert [json.loads(line) for line in commands[0]['stdout'].splitlines()]==target['rows']
        projected.append(dict(target=label,summary=target['summary']))
    selection=read(HERE/'selection/selection_pre.json')
    assert sha(HERE/'selection/metadata_pool.json')==selection['metadata_pool_sha256']
    assert sha(HERE/'selection/build_metadata_pool.py')==selection['pool_builder_sha256']
    assert selection['selected']==[] and selection['pool_count']==39
    final_audit=read(HERE/'gate_audit/final_audit.json')
    assert final_audit['gate_sha256']==sha(HERE/'authority_gate.py')
    assert final_audit['runner_sha256']==sha(HERE/'run_gate_development.py')
    return dict(saved_at_utc=datetime.now(timezone.utc).isoformat(),
        conclusion='Final development records and prior locks consistent; local reviewed contract only.',
        verified_new_files=new,verified_prior_files=old,verified_ancestry_entries=ancestry,
        verified_old_raw_reports=old_raw,
        root_test_exit=tests['returncode'],source_files=source_checks,
        gate_statuses={name:result['status'] for name,result in development['outputs'].items()},
        projection_summaries=projected,independent_selected=0,independent_detector_executions=0,
        final_audit_file_sha256=sha(HERE/'gate_audit/final_audit.json'),
        final_audit_keys=list(final_audit),
        limits='Quotes are not semantic proofs; historical external protocol, real runtime and generalization unproved.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze',action='store_true')
    parser.add_argument('--save-completion',action='store_true')
    parser.add_argument('--check-unfrozen',action='store_true')
    args=parser.parse_args()
    if args.check_unfrozen and (args.freeze or args.save_completion):
        parser.error('unfrozen preflight cannot write final evidence')
    if args.freeze:
        freeze()
    results=verify(require_freeze=not args.check_unfrozen)
    if args.save_completion:
        save_once(HERE/'completion_manifest.json',results)
    print('verified:',len(results['verified_new_files']),'stage files,',len(results['verified_prior_files']),
          'prior files,',len(results['verified_ancestry_entries']),'older entries; selected/detector executions 0/0')


if __name__=='__main__':
    main()
