"""Snapshot and execute one saved-source composition evidence query."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess,sys,shutil

HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def put(p,value):
    assert not p.exists(),p
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def check(files):
    for f in files:assert sha(Path(f['path']))==f['sha256'],f['path']
def verified_inputs():
    check(load(HERE/'freeze_inputs_pre.json')['files'])
    value=load(HERE/'inputs_pre.json');check(load(Path(value['previous_completion_path']))['files'])
    return value
def worker(folder):
    check(load(folder/'freeze_code_pre.json')['files']);inputs=verified_inputs()
    spec=importlib.util.spec_from_file_location('bounded_length_composition',folder/'extractor_snapshot.py')
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    sources=[module.Source(Path(s['saved_path']).read_bytes(),s) for s in inputs['sources']]
    selection={k:inputs[k] for k in ['structure','producer_function','consumer_function']}
    try:result=module.analyze(*sources,selection,inputs['prior_template'])
    except (ValueError,KeyError,TypeError,IndexError) as e:result=dict(status='insufficient',reason=str(e),new_confirmed_cases=0,independent_positive_cases=0)
    tests={}
    if result['status']=='source_evidence_collected':
        facts=result['machine_facts'];p=facts['producer'];model=result['conditional_composition'];expected=inputs['expected']
        tests=dict(structure_fields=len(facts['layout']['fields'])==expected['structure_fields'],
            conditional_prefix=facts['layout']['conditional_prefix_model']==expected['conditional_header_prefix'],
            encoded_write=p['encoded_length_write']['helper']=='htons',tail_array_copies=len(p['tail_array_copies'])==expected['tail_array_copies'],
            scalar_width_not_defaulted=p['scalar_store']['width_C_bytes']=='sizeof(unsigned short)' and p['scalar_store']['width_and_alignment_certified'] is False,
            handoff_to_selected_function=p['handoff']['args'][1]==p['object'],
            object_start_copy=facts['consumer']['object_start_copy']['args'][1]==facts['consumer']['parameter_object'],
            unknown_symbols=model['unknown_symbols']==expected['unknown_symbols'],
            payload_model=model['payload_model']==dict(constant=2,symbols={'ETH_ALEN':1,'old_tag_len':1}),
            total_model=model['total_object_model']==dict(constant=6,symbols={'ETH_ALEN':1,'old_tag_len':1}),
            guard_not_promoted=p['capacity_guard']['inside_old_object_block'] and p['capacity_guard']['all_paths_certified'] is False,
            full_length_not_certified=model['complete_length_contract_certified'] is False,
            all_conditions_unproven=len(result['condition_evidence_card'])==12 and all(c['proven'] is False for c in result['condition_evidence_card']),
            no_new_confirmed=result['new_confirmed_cases']==result['independent_positive_cases']==0)
    passed=bool(tests) and all(tests.values())
    counts=dict(saved_source_queries=1,queries_passed=int(passed),saved_sources=2,interface_cases=1,
        failure_records=int(not passed),new_confirmed_cases=0,independent_positive_cases=0,
        old_detector_reexecutions=0,old_template_reexecutions=0,new_source_queries=0,project_model_calls=0,kernel_or_compiler_runs=0)
    put(folder/'results.json',dict(counts=counts,tests=tests,passed=passed,evidence=result,
        source_input_freeze_sha256=sha(HERE/'freeze_inputs_pre.json'),prior_template_pointer=inputs['prior_template_pointer']))
    print(json.dumps(counts,ensure_ascii=False));return 0 if passed else 1

if __name__=='__main__':
    mode=sys.argv[1];phase=sys.argv[2];folder=HERE/'runs'/phase
    if mode=='freeze':
        verified_inputs();folder.mkdir(parents=True,exist_ok=False)
        for src,target in [(HERE/'composition_extract.py','extractor_snapshot.py'),(HERE/'run_evidence.py','runner_snapshot.py')]:shutil.copyfile(src,folder/target)
        paths=[HERE/'composition_extract.py',HERE/'run_evidence.py',HERE/'inputs_pre.json',HERE/'freeze_inputs_pre.json',
            folder/'extractor_snapshot.py',folder/'runner_snapshot.py',HERE/'audit_protocol/review_code_pre.json']
        put(folder/'freeze_code_pre.json',dict(files=[dict(path=str(p),sha256=sha(p)) for p in paths],
            execution_extractor_sha256=sha(HERE/'composition_extract.py'),purpose='first evidence-query code snapshot before execution'))
        print(json.dumps(dict(phase=phase,freeze_sha256=sha(folder/'freeze_code_pre.json')),ensure_ascii=False))
    elif mode=='run':
        assert folder.is_dir() and not (folder/'receipt.json').exists()
        check(load(folder/'freeze_code_pre.json')['files']);before=sha(folder/'extractor_snapshot.py')
        argv=[sys.executable,'-B','-X','utf8',str(folder/'runner_snapshot.py'),'worker',phase]
        p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        for name,raw in [('stdout.bin',p.stdout),('stderr.bin',p.stderr)]:
            target=folder/name;assert not target.exists();target.write_bytes(raw)
        output=folder/'results.json'
        put(folder/'receipt.json',dict(argv=argv,returncode=p.returncode,extractor_before_sha256=before,
            extractor_after_sha256=sha(folder/'extractor_snapshot.py'),stdout_sha256=sha(folder/'stdout.bin'),
            stderr_sha256=sha(folder/'stderr.bin'),results_sha256=sha(output) if output.exists() else None,
            old_detector_reexecuted=False,old_template_reexecuted=False))
        sys.stdout.buffer.write(p.stdout);sys.stderr.buffer.write(p.stderr);raise SystemExit(p.returncode)
    elif mode=='worker':
        if HERE.parent.name=='runs':folder=HERE;HERE=HERE.parent.parent
        raise SystemExit(worker(folder))
    else:raise SystemExit('unsupported mode')
