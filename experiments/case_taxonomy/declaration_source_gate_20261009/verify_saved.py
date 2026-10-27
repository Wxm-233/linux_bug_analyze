"""Read-only verify saved gate outputs, locks and semantic acceptance fields."""
from pathlib import Path
import hashlib,json

HERE=Path(__file__).resolve().parent;BASE=HERE.parent;RUN=HERE/'runs/initial'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(rows):
    for row in rows:assert sha(Path(row['path']))==row['sha256'],row['path']
def verify():
    check(load(HERE/'freeze_inputs_pre.json')['files'])
    check(load(HERE/'freeze_inputs_v2_pre.json')['files'])
    check(load(HERE/'freeze_code_pre.json')['files'])
    check(load(BASE/'include_route_20261009/completion_manifest.json')['files'])
    rejected=load(HERE/'audit_acceptance/review_inputs.json');assert rejected['ready_to_run'] is False
    accepted=load(HERE/'audit_acceptance/review_inputs_v2.json')
    assert accepted['ready_to_run'] is True and accepted['input_lock_sha256']==sha(HERE/'freeze_inputs_v2_pre.json')
    audit=load(HERE/'audit_code/review.json')
    assert audit['ready_to_run'] is True and audit['code_sha256']==sha(HERE/'source_gate.py') and audit['runner_sha256']==sha(HERE/'run_once.py')
    old=load(HERE/'fixtures_pre.json')['fixtures'];fixtures=load(HERE/'fixtures_pre_v2.json')['fixtures']
    assert len(fixtures)==len(old)==8
    assert [i for i,(a,b) in enumerate(zip(old,fixtures)) if a!=b]==[4]
    real=load(HERE/'real_input_pre.json');saved=Path(real['source_result_path'])
    assert sha(saved)==real['source_result_sha256']
    assert real['input']['candidate']==load(saved)['development'][0]['result']['assignments'][0]
    receipt=load(RUN/'receipt.json')
    assert receipt['returncode']==0 and receipt['raw_native_streams'] is True
    assert receipt['stdout_sha256']==sha(RUN/'stdout.bin') and receipt['stderr_sha256']==sha(RUN/'stderr.bin')
    assert receipt['gate_snapshot_sha256']==sha(RUN/'gate_snapshot.py')==sha(HERE/'source_gate.py')
    assert receipt['runner_snapshot_sha256']==sha(RUN/'runner_snapshot.py')==sha(HERE/'run_once.py')
    assert receipt['input_lock_sha256']==sha(HERE/'freeze_inputs_v2_pre.json') and receipt['code_lock_sha256']==sha(HERE/'freeze_code_pre.json')
    results=load(RUN/'results.json');assert load(RUN/'stdout.bin')==results['counts']
    queries=fixtures+[real];assert len(results['evaluated'])==9
    flags=['actual_include_binding_certified','actual_preprocessing_certified','actual_build_certified','actual_layout_certified','complete_length_certified']
    for input,row in zip(queries,results['evaluated']):
        result=row['result'];expected=input['expected']
        assert result['upstream_candidate']==input['input']['candidate']
        assert result['disposition']==expected['disposition'] and row['passed'] is True
        assert row['no_certification_promotion'] is True and row['upstream_candidate_preserved'] is True
        assert all(result[k] is False for k in flags)
        assert len(result['requirements'])==12 and all(r['proven'] is False for r in result['requirements'])
        if expected['required_reason']:
            assert expected['required_reason'] in [r['code'] for r in result['reasons']]
            assert result['check_proposal'] is None and result['source_gate']['level']=='insufficient'
        else:
            assert result['source_gate']['level']=='conditional_static_source_route' and result['reasons']==[]
            assert result['check_proposal']['kind']=='representation_normalization_review'
            assert result['source_gate']['assumptions'] and len(result['source_gate']['unresolved'])==5
            assert result['source_gate']['missing_in_registry_is_proven_absence'] is False
    counts=results['counts']
    assert counts['synthetic_inputs']==counts['synthetic_passed']==8
    assert counts['saved_parent_candidates']==counts['saved_attachment_passed']==1
    assert counts['total_gate_queries']==9 and counts['conditional_candidates']==2 and counts['insufficient']==7
    for name in ['failure_records','new_confirmed_cases','independent_positive_cases','old_detector_runs','git_commands','compiler_or_kernel_runs','project_model_calls']:assert counts[name]==0
    review=load(HERE/'audit_results/review.json');assert review['review_passed'] is True
    assert review['results_sha256']==sha(RUN/'results.json')
    return dict(**counts,input_errata_before_first_rule_run=1,actual_binding_promotions=0,old_files_unchanged=True,verification_did_not_rerun_rule=True)
if __name__=='__main__':
    counts=verify();closed=HERE/'completion_manifest.json'
    if closed.exists():
        previous=load(closed);check(previous['files']);assert previous['counts']==counts
    print(json.dumps(counts,ensure_ascii=False))
