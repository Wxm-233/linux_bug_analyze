"""Check saved bytes, bounded commands and no-query stop; never run a detector."""
from pathlib import Path
import hashlib
import json
import re
import sys

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
RULE=BASE/'numeric_compare_development_20261008/numeric_compare.py'
RULE_SHA='1ca111bf2d10014ceeebfbe8984e14d6ae586ff7160c40c6c2f27401e7b8bbb5'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name):return json.loads((HERE/name).read_text(encoding='utf-8'))
def verify_records(records):
    for row in records:assert sha(Path(row['path']))==row['sha256'],row['path']

def verify():
    freeze=load('freeze_metadata_pre.json');verify_records(freeze['files'])
    assert sha(RULE)==RULE_SHA
    assert freeze['source_exports_before_freeze']==freeze['rule_executions_before_freeze']==freeze['patch_exports_before_freeze']==0
    pool=load('metadata_pool.json');audit=load('audit_metadata/exposure_audit.json')
    assert len(pool['records'])==audit['pool_count']==16
    assert audit['metadata_pool_sha256']==sha(HERE/'metadata_pool.json')
    excluded={r['commit'] for r in audit['confirmed_prior_source_exposure']}
    expected=[r for r in pool['records'] if r['commit'] not in excluded and re.search(r'endian|byte[ -]?order|(?:le|be)(?:16|32|64)|convert|conversion',r['subject'],re.I)][:2]
    queue=load('queue_pre.json')['queue'];assert queue==expected
    parent=load('parent_manifest.json');rows=parent['observations']
    assert parent['parent_support_attempts']==len(rows)==len(queue)==1
    assert parent['rule_executions']==parent['patch_exports']==0
    commands=load('parent_commands.json');assert len(commands)==6
    for cmd in commands:
        assert cmd['argv'][:7]==['wsl','-d','Ubuntu','--','git','-C','/root/repos/linux']
        for kind in ['stdout','stderr']:assert sha(Path(cmd[kind]))==cmd[kind+'_sha256']
        assert cmd['returncode']==0 or cmd['missing_allowed']
    row=rows[0];commit=queue[0]['commit'];rev=row['revision'];path=row['selected_c_path']
    assert row['commit']==commit and row['export_status']=='ok'
    assert path==sorted(p for p in row['changed_path_names'] if p.endswith('.c'))[0]
    assert len(row['sources'])==1 and len(row['missing_headers'])==2
    wanted=[['show','-s','--format=%P',commit],['diff-tree','--no-commit-id','--name-only','-r',commit],['show',rev+':'+path],['rev-parse',rev+':'+path]]
    actual=[c['argv'][7:] for c in commands if not c['missing_allowed'] or c['returncode']==0]
    assert actual==wanted
    missing=[c for c in commands if c['returncode']!=0]
    assert [c['argv'][7:] for c in missing]==[['show',rev+':'+h] for h in row['missing_headers']]
    source=row['sources'][0];raw=Path(source['saved_path']).read_bytes()
    assert sha(Path(source['saved_path']))==source['sha256']
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==source['blob_sha1']
    assert len(raw)==source['byte_count']
    support=load('audit_parent_support/review.json')
    assert support['supported_main_input'] is None
    assert support['rule_executions']==support['patch_exports']==0
    stop=load('stop_receipt.json')
    assert stop['status']=='stopped_after_parent_support_no_input'
    assert stop['second_input_freeze']=='not_performed_no_supported_input'
    assert stop['output_lock']=='not_performed_no_rule_output'
    assert stop['rule_executions']==stop['patch_exports']==0
    quote_count=0
    for quote in support['source_quotes']+stop['root_hypothesis_quotes']:
        assert Path(quote['saved_path']).resolve()==Path(source['saved_path']).resolve()
        lines=raw.decode('utf-8').splitlines()
        assert lines[quote['line']-1]==quote['text'];quote_count+=1
    result=dict(metadata_pool=16,prior_source_exposed_excluded=len(excluded),queue_items=1,
                parent_support_attempts=1,parent_source_files=1,missing_header_attempts=2,
                git_commands=6,verified_quotes=quote_count,supported_main_inputs=0,
                rule_executions=0,patch_exports=0,new_confirmed_cases=0,independent_positive_cases=0,
                project_model_calls=0,no_rule_reexecution=True,hash_checks_do_not_certify_semantics=True)
    return result

if __name__=='__main__':
    result=verify()
    if '--freeze' in sys.argv:
        p=HERE/'completion_manifest.json';assert not p.exists()
        files=[dict(path=str(f),sha256=sha(f)) for f in sorted(HERE.rglob('*')) if f.is_file() and '__pycache__' not in f.parts]
        p.write_text(json.dumps(dict(files=files,counts=result),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    elif (HERE/'completion_manifest.json').exists():
        closed=load('completion_manifest.json');verify_records(closed['files']);assert closed['counts']==result
    print(json.dumps(result,ensure_ascii=False))
