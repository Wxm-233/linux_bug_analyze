"""Read-only verification of saved facts; does not execute any detector/Git."""
from pathlib import Path
import hashlib,json,re

HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def verify():
    pool=load(HERE/'metadata_pool.json');source=Path(pool['source'])
    assert sha(source)==pool['source_sha256']=='8e61c456af84b1cee027a38793e4146a5d96bf652307fc83582e4c661f4d995a'
    rows=load(source)['samples'];assert len(rows)==pool['sample_count']==500
    total=sum(bool(re.search(pool['representation_regex'],r['subject'],re.I) and re.search(pool['count_regex'],r['subject'],re.I)) for r in rows)
    assert total==pool['all_matching_count']==pool['materialized_count']==0
    assert pool['records']==[] and pool['cap_applied_before_exposure'] is True and pool['model_results_used'] is False
    lock=load(HERE/'freeze_pre.json')
    for row in lock['files']:assert sha(Path(row['path']))==row['sha256'],row['path']
    audit=load(HERE/'audit_exposure/exposure_audit.json')
    assert audit['metadata_pool_sha256']==sha(HERE/'metadata_pool.json')
    assert audit['records']==[] and audit['searched_file_count']==0 and audit['searched_files']==[]
    selection=load(HERE/'selection_pre.json')
    assert selection['queue']==selection['excluded_commits']==[] and selection['queue_size']==0 and selection['no_replacement'] is True
    method=load(HERE/'audit_method/review.json')
    assert method['ready_for_path_queries'] is True and method['script_sha256']==sha(HERE/'select_paths.py')
    assert method['freeze_sha256']==sha(HERE/'freeze_pre.json')
    result=load(HERE/'path_manifest.json')
    assert result['observations']==[] and result['selected_path'] is None and result['stop_reason']=='no_unexposed_metadata_input'
    for key in ['queue_size','git_commands','new_source_requests','rule_runs','gate_runs','patch_exports','new_confirmed_cases','independent_positive_cases']:assert result[key]==0,key
    assert not (HERE/'raw').exists() and not (HERE/'sources').exists()
    independent=load(HERE/'audit_result/review.json')
    assert independent['review_passed'] is True and independent['path_manifest_sha256']==sha(HERE/'path_manifest.json')
    assert independent['freeze_sha256']==sha(HERE/'freeze_pre.json')
    closed=HERE.parent/'encoded_count_support_20261009/completion_manifest.json'
    assert sha(closed)=='77eb72ef71cb5b289f37c2d8673754082ed6164ba137e4061189fe30659540e0'
    for row in load(closed)['files']:assert sha(Path(row['path']))==row['sha256']
    return dict(verification_passed=True,fixed_metadata_count=500,double_hint_matches=0,path_queries=0,new_source_requests=0,detector_runs=0,source_gate_runs=0,patch_exports=0,new_confirmed_cases=0,independent_positive_cases=0,old_closed_stage_unchanged=True,meaning='metadata_selection_empty_not_detector_negative')
if __name__=='__main__':print(json.dumps(verify(),ensure_ascii=False))
