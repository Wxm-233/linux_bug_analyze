"""Freeze then execute a fixed 12-probe set and one reviewed revision pair."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess,sys,traceback
from datetime import datetime,timezone

HERE=Path(__file__).resolve().parent;BASE=HERE.parent
RULE=HERE/'encoded_length_check.py'
DEPS=[BASE/'interface_facts_20261008/interface_fact_extractor.py',BASE/'endian_consumer_single_revision.py']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):
    assert not p.exists(),str(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def check(rs):
    for r in rs:assert sha(Path(r['path']))==r['sha256'],r['path']
def freeze_inputs():
    inputs=load(HERE/'inputs_pre.json');assert len(load(HERE/'probes_pre.json')['cases'])==12
    files=[HERE/'protocol_pre.md',HERE/'inputs_pre.json',HERE/'probes_pre.json',*DEPS]
    for label in ['parent','fixed']:
        for meta in [inputs[label]['source'],*inputs[label]['declarations']]:
            p=Path(meta['saved_path']);assert sha(p)==meta['sha256'];files.append(p)
            for r in meta.get('proof_files',[]):assert sha(Path(r['path']))==r['sha256'];files.append(Path(r['path']))
    files=list(dict.fromkeys(files))
    save(HERE/'freeze_inputs_pre.json',dict(time_utc=datetime.now(timezone.utc).isoformat(),
        files=[dict(path=str(p),sha256=sha(p)) for p in files],detector_executions_before_freeze=0,new_git_calls=0))
    print(json.dumps(dict(input_lock_sha256=sha(HERE/'freeze_inputs_pre.json'),probe_count=12)))
def source(module,meta):
    raw=Path(meta['saved_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==meta['sha256']
    return module.Source(meta['source_path'],meta['revision'],meta['saved_path'],meta['blob_sha1'],raw)
def synthetic(module,case,kind):
    key='source' if kind=='main' else 'declaration';raw=case[key+'_text'].encode('utf-8')
    blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    return module.Source('probe/'+case['id']+'/'+kind+'.c',case[key+'_revision'],
                         'synthetic://'+case['id']+'/'+kind,blob,raw)
def observation(result):
    rows=result.get('assignments',[])
    if rows:return [r['status'] for r in rows]
    return ['insufficient'] if result.get('execution_status')=='insufficient' else []
def worker(phase):
    folder=HERE/'runs'/phase;freeze=load(folder/'freeze_code_pre.json')
    check(freeze['files']);assert sha(RULE)==freeze['execution_rule_sha256']
    assert sha(Path(__file__))==sha(folder/'runner_snapshot.py')
    check(load(HERE/'freeze_inputs_pre.json')['files'])
    sys.path.insert(0,str(HERE));sys.path.insert(0,str(BASE))
    spec=importlib.util.spec_from_file_location('encoded_length_development_rule',RULE)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    probes=[];dev=[];failures=[]
    for case in load(HERE/'probes_pre.json')['cases']:
        try:
            result=module.inspect_function(synthetic(module,case,'main'),case['function_name'],[synthetic(module,case,'header')])
            seen=observation(result);expected=[] if case['expected_status']=='no_assignment' else [case['expected_status']]
            status_ok=(bool(seen) and all(s=='insufficient' for s in seen)) if case['expected_status']=='insufficient' else seen==expected
            ok=status_ok and result.get('length_contract_certified') is False and result.get('whole_function_certified') is False
            for row in result.get('assignments',[]):
                if row['status']=='normal':ok=ok and row.get('length_contract_certified') is False
            probes.append(dict(id=case['id'],expected=expected,observed=seen,passed=ok,result=result))
            if not ok:failures.append(dict(kind='probe',id=case['id'],expected=expected,observed=seen,reason='status or certification boundary mismatch'))
        except Exception as exc:
            error=dict(kind='probe',id=case['id'],error_type=type(exc).__name__,message=str(exc));failures.append(error);probes.append(dict(**error,passed=False,traceback=traceback.format_exc()))
    inputs=load(HERE/'inputs_pre.json')
    for label,expected in [('parent',['candidate']),('fixed',['normal'])]:
        try:
            result=module.inspect_function(source(module,inputs[label]['source']),inputs['function_name'],[source(module,m) for m in inputs[label]['declarations']])
            seen=observation(result);ok=seen==expected and result.get('length_contract_certified') is False
            dev.append(dict(revision_label_outside_rule=label,input=inputs[label],expected_representation=expected,observed=seen,passed=ok,result=result))
            if not ok:failures.append(dict(kind='development',revision=label,expected=expected,observed=seen))
        except Exception as exc:
            error=dict(kind='development',revision=label,error_type=type(exc).__name__,message=str(exc));failures.append(error);dev.append(dict(**error,passed=False,traceback=traceback.format_exc()))
    counts=dict(fixed_synthetic_probes=12,probes_passed=sum(r['passed'] for r in probes),development_interfaces=1,
        revision_queries=2,development_queries_passed=sum(r['passed'] for r in dev),failure_records=len(failures),
        new_confirmed_cases=0,independent_positive_cases=0,project_model_calls=0)
    save(folder/'results.json',dict(counts=counts,probes=probes,development=dev,failures=failures))
    print(json.dumps(counts,ensure_ascii=False));return 1 if failures else 0
def run(phase):
    assert phase and phase.replace('_','').isalnum()
    check(load(HERE/'freeze_inputs_pre.json')['files'])
    folder=HERE/'runs'/phase;folder.mkdir(parents=True,exist_ok=False)
    for name,p in [('rule_snapshot.py',RULE),('runner_snapshot.py',Path(__file__))]:(folder/name).write_bytes(p.read_bytes())
    files=[folder/'rule_snapshot.py',folder/'runner_snapshot.py',*DEPS,HERE/'freeze_inputs_pre.json']
    save(folder/'freeze_code_pre.json',dict(time_utc=datetime.now(timezone.utc).isoformat(),execution_rule_path=str(RULE),execution_rule_sha256=sha(RULE),
        files=[dict(path=str(p),sha256=sha(p)) for p in files],probe_count=12,revision_queries=2))
    argv=[sys.executable,'-B','-X','utf8',str(Path(__file__).resolve()),'__worker',phase]
    p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    (folder/'stdout.bin').write_bytes(p.stdout);(folder/'stderr.bin').write_bytes(p.stderr)
    save(folder/'receipt.json',dict(argv=argv,returncode=p.returncode,rule_before_sha256=sha(folder/'rule_snapshot.py'),rule_after_sha256=sha(RULE),
        stdout_sha256=sha(folder/'stdout.bin'),stderr_sha256=sha(folder/'stderr.bin'),results_sha256=sha(folder/'results.json') if (folder/'results.json').exists() else None))
    assert sha(RULE)==sha(folder/'rule_snapshot.py')
    sys.stdout.buffer.write(p.stdout)
    if p.returncode:sys.stderr.buffer.write(p.stderr)
    return p.returncode
if __name__=='__main__':
    op=sys.argv[1]
    if op=='freeze_inputs':freeze_inputs()
    elif op=='run':raise SystemExit(run(sys.argv[2]))
    elif op=='__worker':raise SystemExit(worker(sys.argv[2]))
