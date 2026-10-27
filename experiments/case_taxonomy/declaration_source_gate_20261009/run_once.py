"""Freeze code, then execute one saved-candidate attachment and eight fixtures."""
from pathlib import Path
import ast,hashlib,importlib.util,json,subprocess,sys

HERE=Path(__file__).resolve().parent
RUN=HERE/'runs/initial'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,v):
    assert not p.exists(),p;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def check(rows):
    for row in rows:assert sha(Path(row['path']))==row['sha256'],row['path']
def check_inputs():
    check(load(HERE/'freeze_inputs_v2_pre.json')['files'])
    acceptance=load(HERE/'audit_acceptance/review_inputs_v2.json')
    assert acceptance['ready_to_run'] is True
    assert acceptance['input_lock_sha256']==sha(HERE/'freeze_inputs_v2_pre.json')
def freeze():
    check_inputs()
    audit=load(HERE/'audit_code/review.json')
    assert audit['ready_to_run'] is True
    assert audit['code_sha256']==sha(HERE/'source_gate.py') and audit['runner_sha256']==sha(HERE/'run_once.py')
    for p in [HERE/'source_gate.py',HERE/'run_once.py']:ast.parse(p.read_text(encoding='utf-8'))
    paths=[HERE/'source_gate.py',HERE/'run_once.py',HERE/'freeze_inputs_v2_pre.json',HERE/'audit_acceptance/review_inputs_v2.json',HERE/'audit_code/review.json']
    put(HERE/'freeze_code_pre.json',dict(files=[dict(path=str(p),sha256=sha(p)) for p in paths],rule_queries_before_lock=0))
    print(json.dumps(dict(code_lock_sha256=sha(HERE/'freeze_code_pre.json'),rule_sha256=sha(HERE/'source_gate.py'))))
def worker():
    check_inputs();check(load(HERE/'freeze_code_pre.json')['files'])
    assert sha(RUN/'gate_snapshot.py')==sha(HERE/'source_gate.py')
    assert sha(RUN/'runner_snapshot.py')==sha(HERE/'run_once.py')
    spec=importlib.util.spec_from_file_location('frozen_declaration_source_gate',RUN/'gate_snapshot.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    fixtures=load(HERE/'fixtures_pre_v2.json')['fixtures'];assert len(fixtures)==8
    real=load(HERE/'real_input_pre.json')
    evaluated=[]
    for label,item in [(f['id'],f) for f in fixtures]+[('saved_parent_candidate',real)]:
        result=module.evaluate(item['input'])
        expected=item['expected']
        passed=result['disposition']==expected['disposition']
        if expected['required_reason'] is not None:passed=passed and expected['required_reason'] in [r['code'] for r in result['reasons']]
        flags=['actual_include_binding_certified','actual_preprocessing_certified','actual_build_certified','actual_layout_certified','complete_length_certified']
        no_promotion=all(result[k] is False for k in flags) and len(result['requirements'])==12 and all(r['proven'] is False for r in result['requirements'])
        if result['disposition']=='insufficient':no_promotion=no_promotion and result['check_proposal'] is None
        candidate_preserved=result['upstream_candidate']==item['input']['candidate']
        passed=bool(passed and no_promotion and candidate_preserved)
        evaluated.append(dict(id=label,scope='saved_development_attachment' if label=='saved_parent_candidate' else 'synthetic_development_boundary',
            expected=expected,passed=passed,no_certification_promotion=no_promotion,upstream_candidate_preserved=candidate_preserved,result=result))
    check_inputs();check(load(HERE/'freeze_code_pre.json')['files'])
    counts=dict(synthetic_inputs=8,synthetic_passed=sum(r['passed'] for r in evaluated[:8]),
        saved_parent_candidates=1,saved_attachment_passed=int(evaluated[-1]['passed']),total_gate_queries=9,
        conditional_candidates=sum(r['result']['disposition']=='conditional_candidate' for r in evaluated),
        insufficient=sum(r['result']['disposition']=='insufficient' for r in evaluated),
        failure_records=sum(not r['passed'] for r in evaluated),new_confirmed_cases=0,independent_positive_cases=0,
        old_detector_runs=0,git_commands=0,compiler_or_kernel_runs=0,project_model_calls=0)
    put(RUN/'results.json',dict(counts=counts,evaluated=evaluated,input_lock_sha256=sha(HERE/'freeze_inputs_v2_pre.json'),rule_sha256=sha(RUN/'gate_snapshot.py')))
    print(json.dumps(counts,ensure_ascii=False))
    return 0 if counts['failure_records']==0 else 3
def launch():
    check_inputs();check(load(HERE/'freeze_code_pre.json')['files'])
    assert not RUN.exists(),'run already exists; no automatic retry'
    RUN.mkdir(parents=True)
    for name,src in [('gate_snapshot.py','source_gate.py'),('runner_snapshot.py','run_once.py')]:
        (RUN/name).write_bytes((HERE/src).read_bytes())
    argv=[sys.executable,'-B','-X','utf8',str(HERE/'run_once.py'),'__execute']
    p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    (RUN/'stdout.bin').write_bytes(p.stdout);(RUN/'stderr.bin').write_bytes(p.stderr)
    put(RUN/'receipt.json',dict(argv=argv,returncode=p.returncode,stdout_sha256=sha(RUN/'stdout.bin'),stderr_sha256=sha(RUN/'stderr.bin'),
        gate_snapshot_sha256=sha(RUN/'gate_snapshot.py'),runner_snapshot_sha256=sha(RUN/'runner_snapshot.py'),
        code_lock_sha256=sha(HERE/'freeze_code_pre.json'),input_lock_sha256=sha(HERE/'freeze_inputs_v2_pre.json'),
        raw_native_streams=True,old_detector_runs=0,git_commands=0,compiler_runs=0))
    sys.stdout.buffer.write(p.stdout)
    if p.returncode:sys.stderr.buffer.write(p.stderr)
    return p.returncode
if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='freeze':freeze()
    elif mode=='run':raise SystemExit(launch())
    elif mode=='__execute':raise SystemExit(worker())
    else:raise SystemExit('unknown mode')
