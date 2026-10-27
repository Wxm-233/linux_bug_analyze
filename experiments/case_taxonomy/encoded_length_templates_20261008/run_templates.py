"""Freeze code, then generate from 14 saved outputs; never rerun extraction."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess,sys,shutil

HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def put(p,data):
    assert not p.exists(),p
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def check(files):
    for f in files:assert sha(Path(f['path']))==f['sha256'],f['path']
def verified_inputs():
    check(load(HERE/'freeze_inputs_pre.json')['files'])
    inputs=load(HERE/'inputs_pre.json')
    check(load(Path(inputs['previous_completion_path']))['files'])
    return inputs,load(Path(inputs['saved_result_path']))

def worker(folder):
    check(load(folder/'freeze_code_pre.json')['files'])
    inputs,saved=verified_inputs()
    spec=importlib.util.spec_from_file_location('saved_length_template_generator',folder/'generator_snapshot.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    outputs=[];failures=[]
    for row in inputs['queries']:
        raw=saved[row['group']][row['index']]['result']
        generated=module.generate(raw)
        records=generated['records'];templates=[r for r in records if r['disposition']=='conditional_template']
        refused=[r for r in records if r['disposition']=='refused']
        tests=dict(query_disposition=generated['disposition']==row['expected_query_disposition'],
            generated_count=len(templates)==row['expected_generated'],refused_count=len(refused)==row['expected_refused_assignments'],
            statuses_preserved=[r['upstream_representation_status'] for r in records]==row['expected_upstream_statuses'],
            observed_terms_only=[[t['value'] for t in r['relation']['rhs']['terms']] for r in templates]==row['expected_component_values'],
            no_complete_length_claim=all(r['limits']['length_contract_certified'] is False and r['relation']['normative_complete_length_formula'] is False for r in templates),
            no_executable_assertion=all(r['limits']['runtime_assertion_generated'] is False and r['limits']['automatic_patch_generated'] is False for r in templates),
            all_conditions_unproven=all(all(c['proven'] is False for c in r['applicability_conditions']) for r in templates),
            missing_components_not_inferred=all(r['unresolved']['missing_addends_inferred'] is False for r in templates))
        passed=all(tests.values())
        if not passed:failures.append(dict(query=row['query_label_outside_generator'],failed=[k for k,v in tests.items() if not v]))
        outputs.append(dict(query_label_outside_generator=row['query_label_outside_generator'],input_json_pointer=row['json_pointer'],
            saved_result_sha256=inputs['saved_result_sha256'],tests=tests,passed=passed,generated=generated))
    counts=dict(saved_queries=len(outputs),queries_passed=sum(o['passed'] for o in outputs),
        generated_templates=sum(sum(r['disposition']=='conditional_template' for r in o['generated']['records']) for o in outputs),
        refused_assignment_records=sum(sum(r['disposition']=='refused' for r in o['generated']['records']) for o in outputs),
        insufficient_queries=sum(o['generated']['disposition']=='insufficient' for o in outputs),
        no_eligible_assignment_queries=sum(o['generated']['disposition']=='no_eligible_assignment' for o in outputs),
        failure_records=len(failures),new_confirmed_cases=0,independent_positive_cases=0,
        old_detector_reexecutions=0,new_source_queries=0,project_model_calls=0,kernel_or_compiler_runs=0)
    put(folder/'results.json',dict(counts=counts,outputs=outputs,failures=failures))
    lines=['# 由保存事实生成的有条件检查模板','',
        '这是数学域中的审阅关系，不是C断言/补丁；所有适用条件均未证，完整长度未知。','']
    for o in outputs:
        g=o['generated'];lines.extend(['## '+o['query_label_outside_generator'],'',
            '保存输入位置：`'+o['input_json_pointer']+'`。状态：`'+g['disposition']+'`。',''])
        if not g['records']:lines.extend([g['reason'],''])
        for r in g['records']:
            if r['disposition']=='refused':lines.extend(['拒生成：'+r['reason']+'。','']);continue
            lines.extend(['关系：`'+r['human_relation']+'`。','',
                '上游局部表示：`'+r['upstream_representation_status']+'`；完整长度未证。显式加项不是完整长度契约。','',
                '首个可见词法消费：`'+r['first_lexical_consumer']['api']+'`，不证明执行顺序。','',
                '以下条件均需进一步确认：',''])
            lines.extend(['- '+c['name']+'：'+c['requirement'] for c in r['applicability_conditions']]);lines.append('')
    (folder/'templates.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(counts,ensure_ascii=False));return 0 if not failures else 1

if __name__=='__main__':
    mode=sys.argv[1]
    folder=HERE/'runs'/sys.argv[2]
    if mode=='freeze':
        verified_inputs();folder.mkdir(parents=True,exist_ok=False)
        for src,target in [(HERE/'template_generator.py','generator_snapshot.py'),(HERE/'run_templates.py','runner_snapshot.py')]:shutil.copyfile(src,folder/target)
        paths=[HERE/'template_generator.py',HERE/'run_templates.py',HERE/'inputs_pre.json',HERE/'freeze_inputs_pre.json',
            folder/'generator_snapshot.py',folder/'runner_snapshot.py']
        put(folder/'freeze_code_pre.json',dict(files=[dict(path=str(p),sha256=sha(p)) for p in paths],
            generator_sha256=sha(HERE/'template_generator.py'),purpose='code lock before first template generation'))
        print(json.dumps(dict(phase=sys.argv[2],freeze_sha256=sha(folder/'freeze_code_pre.json')),ensure_ascii=False))
    elif mode=='run':
        assert folder.is_dir() and not (folder/'receipt.json').exists()
        check(load(folder/'freeze_code_pre.json')['files']);before=sha(folder/'generator_snapshot.py')
        argv=[sys.executable,'-B','-X','utf8',str(folder/'runner_snapshot.py'),'worker',sys.argv[2]]
        p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        for name,raw in [('stdout.bin',p.stdout),('stderr.bin',p.stderr)]:
            target=folder/name;assert not target.exists();target.write_bytes(raw)
        result=folder/'results.json'
        put(folder/'receipt.json',dict(argv=argv,returncode=p.returncode,
            generator_before_sha256=before,generator_after_sha256=sha(folder/'generator_snapshot.py'),
            stdout_sha256=sha(folder/'stdout.bin'),stderr_sha256=sha(folder/'stderr.bin'),
            results_sha256=sha(result) if result.exists() else None,old_detector_reexecuted=False))
        sys.stdout.buffer.write(p.stdout);sys.stderr.buffer.write(p.stderr);raise SystemExit(p.returncode)
    elif mode=='worker':
        # The snapshot lives inside runs/phase; its original inputs remain in the stage root.
        if HERE.parent.name=='runs':
            folder=HERE;HERE=HERE.parent.parent
        raise SystemExit(worker(folder))
    else:raise SystemExit('unsupported mode')
