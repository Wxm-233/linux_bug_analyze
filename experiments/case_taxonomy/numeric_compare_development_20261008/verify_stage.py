"""Verify saved stages and quotes without executing the detector again."""
from pathlib import Path
import hashlib
import json
import re
import sys

HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def verify_records(records,archive=None):
    mapped={r['original_path']:r for r in (archive or [])}
    for r in records:
        p=Path(mapped[r['path']]['preserved_path']) if r['path'] in mapped else Path(r['path'])
        assert sha(p)==r['sha256'],str(p)
        if r['path'] in mapped:assert mapped[r['path']]['sha256']==r['sha256']

def quotes(value):
    if isinstance(value,dict):
        if {'saved_path','sha256','blob_sha1','start_line','end_line','text'}<=value.keys():yield value
        for child in value.values():yield from quotes(child)
    elif isinstance(value,list):
        for child in value:yield from quotes(child)

def main():
    inputs=read(HERE/'input_lock_pre.json');verify_records(inputs['files'])
    sources=inputs['source_inputs']
    for s in sources.values():
        raw=Path(s['saved_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==s['sha256']
        assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==s['blob_sha1']
    rounds=[('initial','freeze_code_pre.json',[1,0]),
            ('after_arrow_repair','freeze_code_repair_pre.json',[0,0]),
            ('final','freeze_code_final_pre.json',[1,0]),
            ('accepted','freeze_code_closeout_pre.json',[0,0])]
    quote_count=0;unique=set()
    for tag,lockname,expected in rounds:
        folder=HERE/tag;lock=read(HERE/lockname)
        archive=read(folder/'code_archive.json')['files'] if (folder/'code_archive.json').exists() else []
        verify_records(lock['files'],archive)
        receipt=read(folder/'execution_receipt.json')
        assert receipt['freeze_sha256']==sha(HERE/lockname)
        assert lock['time_utc']<=receipt['start_utc']<=receipt['end_utc']
        assert receipt['code_unchanged_after_execution']
        assert [r['returncode'] for r in receipt['commands']]==expected
        for c in receipt['commands']:
            assert sha(Path(c['stdout']))==c['stdout_sha256']
            assert sha(Path(c['stderr']))==c['stderr_sha256']
        data=read(folder/'results.json')
        assert data['development_only'] and data['new_confirmed_cases']==data['independent_detections']==0
        for q in quotes(data):
            raw=Path(q['saved_path']).read_bytes()
            assert hashlib.sha256(raw).hexdigest()==q['sha256']
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==q['blob_sha1']
            assert '\n'.join(raw.decode('utf-8').splitlines()[q['start_line']-1:q['end_line']])==q['text']
            quote_count+=1;unique.add((q['sha256'],q['start_line'],q['end_line'],q['text']))
    accepted=read(HERE/'accepted/results.json')
    for row in accepted['records']:
        atoms=[x for f in row['functions'] for x in f['field_atoms']]
        assert sum(f['enumerated_logical_atoms'] for f in row['functions'])==26 and len(atoms)==8
        target=[x for x in atoms if x['function']=='is_rst_area_valid' and x['evidence']['start_line']==520]
        assert len(target)==1 and target[0]['status']==('candidate' if row['label']=='parent' else 'normal')
        assert [x['status'] for x in atoms if x['expression']=='!rhdr->minor_ver']==['normal']
        for x in atoms:
            assert not x['runtime_value_proven'] and not x['control_flow_certified'] and not x['pointer_origin_certified']
            assert not x['whole_function_certified'] and not x['full_preprocessing_certified']
        context=row['format_context']
        assert context[1]['status']=='insufficient' and not context[1]['sightings']
        assert len(context[0]['sightings'])==1 and context[0]['sightings'][0]['binding_status']=='insufficient'
    tests=(HERE/'accepted/tests_stderr.txt').read_text(encoding='utf-8')
    assert re.search(r'Ran 18 tests',tests) and tests.rstrip().endswith('OK')
    probe_sha=None
    for tag,code_path in [('initial',HERE/'after_arrow_repair/code_snapshot/numeric_compare.py'),('final',HERE/'numeric_compare.py')]:
        folder=HERE/'audit_numeric_boundary'/('execution_'+tag)
        probe=read(folder/'results.json')
        assert probe['probe_count']==probe['passed_count']==20 and not probe['failed_ids']
        assert probe['dependencies_before']==probe['dependencies_after']
        for path,digest in probe['dependencies_before'].items():
            assert sha(code_path if Path(path).name=='numeric_compare.py' else Path(path))==digest
        assert read(folder/'tool_receipt.json')['exit_code']==0
        for q in quotes(probe):
            raw=Path(q['saved_path']).read_bytes()
            assert hashlib.sha256(raw).hexdigest()==q['sha256']
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==q['blob_sha1']
            assert '\n'.join(raw.decode('utf-8').splitlines()[q['start_line']-1:q['end_line']])==q['text']
    manifest=HERE/'completion_manifest.json'
    if '--freeze' in sys.argv:
        assert not manifest.exists()
        files=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p!=manifest]
        deps=[Path(r['path']) for r in inputs['files']]
        manifest.write_text(json.dumps(dict(files=[dict(path=str(p),sha256=sha(p)) for p in sorted(set(files+deps))]),indent=2)+'\n',encoding='utf-8')
    if manifest.exists():verify_records(read(manifest)['files'])
    print(json.dumps(dict(development_interfaces=1,revision_observations=2,logical_atoms_per_revision=26,
                         field_atoms_per_revision=8,root_tests=18,independent_synthetic_cases=20,
                         saved_development_runs=4,verified_development_quote_records=quote_count,
                         unique_development_quotes=len(unique),new_confirmed_cases=0,independent_positive_detections=0,
                         model_calls=0,no_rule_reexecution=True,semantic_truth_certified_by_hash_check=False)))


if __name__=='__main__':main()
