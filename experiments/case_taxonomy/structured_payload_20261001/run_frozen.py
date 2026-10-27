"""Freeze local rule closure; preserve parent evidence before patch review."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import ast
import hashlib
import importlib
import json
import sys

HERE = Path(__file__).resolve().parent
RULES = HERE.parent
MODULE = 'structured_hci_single_revision'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_new(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')

def closure(path, seen=None):
    seen = set() if seen is None else seen
    if path in seen:
        return seen
    seen.add(path)
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    for node in ast.walk(tree):
        names = ([node.module] if isinstance(node, ast.ImportFrom) and node.module
                 else [alias.name for alias in node.names] if isinstance(node, ast.Import) else [])
        for name in names:
            candidate = RULES / (name.split('.')[0] + '.py')
            if candidate.is_file():
                closure(candidate, seen)
    return seen

def verify(frozen):
    for record in frozen['files']:
        if digest(RULES / record['path']) != record['sha256']:
            raise RuntimeError('frozen file changed: '+record['path'])

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=['freeze', 'parent', 'fix'], required=True)
    parser.add_argument('--repo', type=Path, default=Path('/root/repos/linux'))
    args = parser.parse_args()
    freeze_path = HERE / 'freeze_manifest.json'
    selection_path = HERE / 'selection_pre.json'
    if args.phase == 'freeze':
        tests = json.loads((HERE/'root_test_run.json').read_text(encoding='utf-8'))
        if tests['returncode'] != 0:
            raise RuntimeError('root tests did not pass')
        for name, expected in tests['tested_files'].items():
            if digest(RULES/name) != expected:
                raise RuntimeError('tested file changed: '+name)
        audit = json.loads((HERE/'method_code_audit.json').read_text(encoding='utf-8'))['final_recheck']
        if (audit['remaining_audit_blockers'] or audit['module_sha256'] != digest(RULES/(MODULE+'.py'))
            or audit['test_sha256'] != digest(RULES/(MODULE+'_test.py'))):
            raise RuntimeError('audit not current or blockers remain')
        paths = closure(RULES / (MODULE+'.py'))
        paths |= closure(RULES / (MODULE+'_test.py'))
        paths |= {Path(__file__).resolve(), HERE/'protocol_pre.md', HERE/'select_metadata.py',
                  HERE/'select_targets_pre.py', HERE/'run_tests.py', HERE/'save_review.py', HERE/'metadata_pool.json', selection_path}
        paths |= {HERE/'root_test_run.json', HERE/'method_code_audit.json', HERE/'method_code_audit.md',
                  HERE/'method_audit_probe_final_lock.json'}
        files = [dict(path=path.relative_to(RULES).as_posix(), sha256=digest(path))
                 for path in sorted(paths)]
        write_new(freeze_path, dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),
                  module=MODULE, files=files,
                  selection_sha256=digest(selection_path),
                  scope='Rule and static local import closure frozen before target source/patch review.'))
        print('frozen files:', len(files))
        return
    frozen = json.loads(freeze_path.read_text(encoding='utf-8'))
    verify(frozen)
    if digest(selection_path) != frozen['selection_sha256']:
        raise RuntimeError('selection changed')
    targets = json.loads(selection_path.read_text(encoding='utf-8'))['targets']
    if len(targets) > 2:
        raise RuntimeError('target cap exceeded')
    output_dir = HERE / 'holdout'
    output_dir.mkdir(exist_ok=True)
    parent_path = output_dir / 'parent_manifest_pre_review.json'
    if args.phase == 'fix':
        parent = json.loads(parent_path.read_text(encoding='utf-8'))
        if parent['freeze_sha256'] != digest(freeze_path):
            raise RuntimeError('parent/freeze mismatch')
        for record in parent['records']:
            if digest(output_dir / record['output']) != record['sha256']:
                raise RuntimeError('parent output changed')
    manifest_path = parent_path if args.phase == 'parent' else output_dir/'fix_manifest_post_review.json'
    if manifest_path.exists():
        raise RuntimeError('refusing to overwrite manifest')
    sys.path.insert(0, str(RULES))
    module = importlib.import_module(MODULE)
    records = []
    for target in targets:
        revision = target['old_revision'] if args.phase == 'parent' else target['commit']
        path = output_dir / (target['commit'][:12]+'_'+args.phase+'_raw.json')
        try:
            analysis = module.analyze_revision(args.repo, revision, target['source_path'])
            status = 'ok'
        except Exception as exc:
            analysis = dict(runner_error=type(exc).__name__+': '+str(exc))
            status = 'runner_error'
        write_new(path, dict(target=target['commit'], revision=revision,
                  source_path=target['source_path'], phase=args.phase, analysis=analysis))
        records.append(dict(target=target['commit'], revision=revision,
                            output=path.name, sha256=digest(path), runner_status=status))
    write_new(manifest_path, dict(phase=args.phase, saved_at_utc=datetime.now(timezone.utc).isoformat(),
              stage='parent outputs saved before target body/patch/source review' if args.phase=='parent'
                    else 'fix counterparts after parent preservation and review',
              freeze_sha256=digest(freeze_path), selection_sha256=digest(selection_path), records=records,
              scope='Purposeful metadata leads. Zero sites/insufficient/errors are never clean verdicts.'))
    print('saved reports:', len(records), args.phase)

if __name__ == '__main__':
    main()
