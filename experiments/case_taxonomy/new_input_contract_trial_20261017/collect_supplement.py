"""One registered symbol search and one registered source supplement per case."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

STAGE = Path(__file__).resolve().parent
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--locate', action='store_true')
    args = p.parse_args()
    if args.locate:
        out = STAGE / 'symbol_search.json'
        assert not out.exists(), 'preserve first search'
        plan = json.loads((STAGE / 'symbol_search_pre.json').read_text())
        rows = []
        for case in plan['cases']:
            assert len(case['symbols']) <= 6
            argv = ['git', '-C', '/root/repos/linux', 'grep', '-n', '-w']
            for name in case['symbols']:
                argv.extend(['-e', name])
            argv.extend([case['parent'], '--', *case['paths']])
            proc = subprocess.run(argv, capture_output=True, timeout=45)
            rows.append({'case': case['case'], 'parent': case['parent'], 'argv': argv,
                         'exit_code': proc.returncode, 'stdout': proc.stdout.decode('utf-8'),
                         'stderr': proc.stderr.decode('utf-8', errors='replace')})
        out.write_text(json.dumps({'plan_sha256': sha(STAGE / 'symbol_search_pre.json'),
                                   'results': rows}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps([{'case': r['case'], 'exit_code': r['exit_code'], 'lines': len(r['stdout'].splitlines())} for r in rows]))
        return
    out = STAGE / 'supplement_sources.json'
    assert not out.exists(), 'preserve first supplement'
    plan_path = STAGE / 'supplement_material_plan.json'
    plan = json.loads(plan_path.read_text())
    assert plan['selection_sha256'] == sha(STAGE / 'selection.json')
    initial = json.loads((STAGE / 'initial_sources.json').read_text())['documents']
    rows = []
    for case in plan['cases']:
        assert len(case['paths']) <= 4
        initial_paths = {d['path'] for d in initial if d['case'] == case['case']}
        assert not initial_paths.intersection(case['paths']) and len(initial_paths) + len(case['paths']) <= 8
        for path in case['paths']:
            argv = ['git', '-C', '/root/repos/linux', 'show', case['parent'] + ':' + path]
            proc = subprocess.run(argv, capture_output=True, timeout=30)
            row = {'id': case['case'] + ':' + path, 'case': case['case'],
                   'material_group': case['case'] + '_parent', 'revision': case['parent'],
                   'path': path, 'status': 'collection_error', 'argv': argv, 'exit_code': proc.returncode}
            if proc.returncode:
                row['error'] = proc.stderr.decode('utf-8', errors='replace')[:1500]
            else:
                row.update(text=proc.stdout.decode('utf-8'), bytes=len(proc.stdout),
                           sha256=hashlib.sha256(proc.stdout).hexdigest(), status='collected')
            rows.append(row)
    result = {'protocol_sha256': sha(STAGE / 'protocol_pre.json'),
              'adapter_baseline_sha256': sha(STAGE / 'adapter_baseline.json'),
              'material_plan_sha256': sha(plan_path), 'documents': rows,
              'semantic_layer': 'unpreprocessed_original_parent_source', 'child_material_read': False}
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'files': len(rows), 'collected': sum(r['status']=='collected' for r in rows),
                      'bytes': sum(r.get('bytes',0) for r in rows)}))

if __name__ == '__main__':
    main()
