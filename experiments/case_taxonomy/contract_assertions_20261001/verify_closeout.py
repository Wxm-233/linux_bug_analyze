"""Verify saved bounded-development evidence; no build, Git query or API call.

--freeze records the post-development baseline once. This is not a pre-holdout
freeze. Default operation verifies that baseline without modifying evidence.
"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
RULES = HERE.parent
sys.path.insert(0, str(RULES))
import contract_assertion_generator as generator
from gcc_projection_bindings import verify_bindings
from run_automatic_checks import verify_runtime


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save_once(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def local_path(relative):
    path = (RULES / relative).resolve()
    if not path.is_relative_to(RULES.resolve()):
        raise ValueError('manifest path escapes case_taxonomy')
    return path


def file_record(path):
    return dict(path=path.relative_to(RULES).as_posix(), sha256=sha(path))


def import_closure(roots):
    """Record visible static local imports, including test fixture modules."""
    found, todo = set(), list(roots)
    search = [RULES, HERE, HERE/'audit', HERE/'paired_domain']
    while todo:
        path = todo.pop().resolve()
        if path in found:
            continue
        found.add(path)
        if path.suffix != '.py':
            continue
        tree = ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [item.name for item in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            else:
                continue
            for module in modules:
                for directory in search:
                    candidate = directory/(module.replace('.', '/')+'.py')
                    if candidate.is_file():
                        todo.append(candidate)
                        break
    return found


def create_freeze():
    if not (HERE/'runner_audit.md').is_file():
        raise ValueError('independent runner audit not yet saved')
    roots = [RULES/'contract_assertion_generator.py',
             RULES/'contract_assertion_generator_test.py',
             HERE/'run_automatic_checks.py', HERE/'gcc_projection_bindings.py',
             HERE/'run_root_tests.py', HERE/'verify_closeout.py',
             HERE/'paired_domain/run_matrix.py',
             HERE/'audit/audit_probe.py', HERE/'audit/run_audit_c.py']
    files = import_closure(roots)
    # Draft/pilot outputs are preserved, but are not final locked evidence.
    for path in HERE.rglob('*'):
        relative = path.relative_to(HERE)
        if (not path.is_file() or any(part in ('__pycache__', 'development', 'pilot_01')
                for part in relative.parts) or path.name.startswith('draft')
                or path.name in ('freeze_manifest.json', 'completion_manifest.json')):
            continue
        files.add(path.resolve())
    for relative in (
        'structured_payload_20261001/freeze_manifest.json',
        'structured_payload_20261001/completion_manifest.json',
        'structured_payload_20261001/compiler_probe/source_evidence.json',
        'structured_payload_20261001/compiler_probe/results.json',
        'outbound_scalar_20260930/freeze_manifest.json',
    ):
        files.add(local_path(relative))
    records = [file_record(path) for path in sorted(files)]
    save_once(HERE/'freeze_manifest.json', dict(
        frozen_at_utc=datetime.now(timezone.utc).isoformat(),
        scope='Post-development source/evidence lock; no new holdout in this stage.',
        import_closure='Static visible local imports, including fixture modules; not arbitrary dynamic imports.',
        files=records))


def check_records(records):
    verified = []
    for record in records:
        path = local_path(record['path'])
        if sha(path) != record['sha256']:
            raise ValueError('hash changed: '+record['path'])
        verified.append(dict(path=record['path'], sha256=record['sha256']))
    return verified


def verify(require_freeze=True):
    new = check_records(read(HERE/'freeze_manifest.json')['files']) if require_freeze else []
    old = []
    for stage in ('structured_payload_20261001', 'outbound_scalar_20260930'):
        records = read(RULES/stage/'freeze_manifest.json')['files']
        checked = check_records(records)
        old.extend(dict(record, freeze=stage) for record in checked)
    prior = read(RULES/'structured_payload_20261001/completion_manifest.json')
    old_reports = check_records(prior['verified_raw_reports'])

    tests = read(HERE/'root_test_run.json')
    assert tests['returncode'] == 0 and tests['code_unchanged_during_test']
    for name, digest in tests['tested_files'].items():
        assert sha(RULES/name) == digest
    for filename, flag in (('final_lock_probe_results.json', 'all_expected'),
                           ('final_lock_c_results.json', 'all_verified')):
        audit = read(HERE/'audit'/filename)
        assert audit[flag]
        assert audit['module_sha256'] == sha(RULES/'contract_assertion_generator.py')
        assert audit['test_sha256'] == sha(RULES/'contract_assertion_generator_test.py')

    run_dir = HERE/'final_run_01'
    results = read(run_dir/'results.json')
    assert results['status'] == 'verified'
    for name, key in (('contract_assertion_generator.py', 'generator_sha256'),
                      ('structured_hci_single_revision.py', 'extractor_sha256')):
        assert sha(RULES/name) == results[key]
    assert sha(HERE/'run_automatic_checks.py') == results['runner_sha256']
    assert sha(HERE/'gcc_projection_bindings.py') == results['binding_checker_sha256']
    for absolute, digest in results['started_code_hashes'].items():
        relative = absolute.split('/case_taxonomy/', 1)[1]
        assert sha(local_path(relative)) == digest
    summaries = []
    for item in results['programs']:
        name = item['input']
        plan = read(run_dir/(name+'_plan.json'))
        report = read(run_dir/(name+'_source_report.json'))
        selected = [p for p in plan['programs'] if p['id'] == item['program_id']]
        assert len(selected) == 1
        program = selected[0]
        inputs = program['validated_inputs']
        assert inputs['report'] == report
        assert generator.build_plan(report, inputs['files']) == plan
        source = run_dir/item['generated_source']
        assert sha(source) == item['generated_source_sha256']
        assert source.read_bytes() == generator.emit_c(program).encode('utf-8')
        prefix = source.stem
        for target in item['targets']:
            label = target['target']
            rows = read(run_dir/(prefix+'_'+label+'_rows.json'))
            summary = verify_runtime(rows, program, target['host_endian'])
            for key, value in summary.items():
                # Runtime helper uses layout tuples; JSON saved them as arrays.
                assert target[key] == json.loads(json.dumps(value))
            dump = run_dir/(prefix+'_'+label+'_tree.txt')
            assert sha(dump) == target['dump_sha256']
            assert verify_bindings(dump, program) == target['gcc_bindings']
            # The row artifact must also be the saved execution stdout.
            commands = [cmd for cmd in results['commands']
                if cmd['argv'][-1].endswith('/'+prefix+'_'+label)
                and '-o' not in cmd['argv']]
            assert len(commands) == 1 and commands[0]['returncode'] == 0
            assert [json.loads(line) for line in commands[0]['stdout'].splitlines()
                    if line.strip()] == rows
            summaries.append(dict(input=name, target=label,
                field_check_rows=summary['field_check_rows'], variants=summary['variants']))

    pair = read(HERE/'paired_domain/results.json')
    for filename, key in (('run_matrix.py', 'runner_sha256'),
                          ('domain_matrix.c', 'generated_c_sha256'),
                          ('source_card.json', 'source_card_sha256')):
        assert sha(HERE/'paired_domain'/filename) == pair[key]
    pair_summaries = {}
    for label, target in pair['targets'].items():
        summary = target['summary']
        assert summary['matrix_rows'] == 81
        assert summary['payload_oracle_mismatches_regular_matrix'] == 0
        assert summary['reader_oracle_mismatches_regular_matrix'] == 0
        assert summary['deliberate_mutation_rejected_by_independent_oracle']
        pair_summaries[label] = summary

    return dict(saved_at_utc=datetime.now(timezone.utc).isoformat(),
        conclusion='Saved final evidence and old baselines consistent; conditional development only.',
        verified_new_frozen_files=new, verified_old_frozen_files=old,
        verified_old_raw_reports=old_reports,
        root_generator_test_exit=tests['returncode'],
        final_audits_match_locked_generator=True,
        automatic_check_summaries=summaries, paired_domain_summaries=pair_summaries,
        limitations='No independent new defect/holdout, full kernel/controller execution, external contract or arbitrary preprocessing proof.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', action='store_true')
    parser.add_argument('--save-completion', action='store_true')
    parser.add_argument('--check-unfrozen', action='store_true')
    args = parser.parse_args()
    if args.check_unfrozen and (args.freeze or args.save_completion):
        parser.error('unfrozen preflight cannot freeze or save completion')
    if args.freeze:
        create_freeze()
    summary = verify(require_freeze=not args.check_unfrozen)
    if args.save_completion:
        save_once(HERE/'completion_manifest.json', summary)
    print('verified:', len(summary['verified_new_frozen_files']), 'new frozen files,',
          len(summary['verified_old_frozen_files']), 'old frozen entries,',
          len(summary['automatic_check_summaries']), 'automatic target runs')


if __name__ == '__main__':
    main()
