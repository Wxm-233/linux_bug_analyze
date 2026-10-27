"""Validate the fixed metadata attempt and an early no-C stop, read-only."""
from pathlib import Path
import hashlib,json,re

HERE=Path(__file__).resolve().parent;BASE=HERE.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def check(rows):
    for row in rows:assert sha(Path(row['path']))==row['sha256'],row['path']
def verify():
    check(load(HERE/'freeze_metadata_pre.json')['files'])
    check(load(HERE/'freeze_metadata_v2_pre.json')['files'])
    pool=load(HERE/'metadata_pool.json');source=Path(pool['source'])
    assert sha(source)==pool['source_sha256']
    samples=load(source)['samples'];assert len(samples)==500
    represented=[(i,s) for i,s in enumerate(samples,1) if s['stratum']=='representation']
    target=represented[16:32];assert len(target)==16
    for order,(row,(index,s)) in enumerate(zip(pool['records'],target),1):
        assert row['pool_order']==order and row['representation_order']==order+16
        assert row['original_manifest_index']==index and row['commit']==s['hash'] and row['subject']==s['subject']
    exposure=load(HERE/'audit_exposure/exposure_audit.json')
    assert exposure['metadata_pool_sha256']==sha(HERE/'metadata_pool.json')
    assert exposure['scope_search_sha256']==sha(HERE/'audit_exposure/scope_search.json')
    for row in exposure['searched_files']:assert sha(BASE/row['path'])==row['sha256']
    byhash={r['commit']:r for r in exposure['records']}
    eligible=[r for r in pool['records'] if not byhash[r['commit']]['source_exposure_confirmed'] and re.search(r'endian|byte[ -]?order|(?:le|be)(?:16|32|64)|convert|conversion',r['subject'],re.I)]
    preferred=[r for r in eligible if re.search(r'\b(?:len|length|size|count|bytes)\b',r['subject'],re.I)]
    chosen=(preferred or eligible)[:1]
    assert load(HERE/'selection_pre.json')['queue']==chosen and len(chosen)==1
    method=load(HERE/'audit_method/review.json')
    assert method['ready_for_export'] is True and method['exporter_sha256']==sha(HERE/'prepare_v2.py')
    assert method['metadata_lock_sha256']==sha(HERE/'freeze_metadata_v2_pre.json')
    old=load(HERE/'audit_method/review_v1.json');assert old['ready_for_export'] is False
    manifest=load(HERE/'parent_manifest.json')
    assert manifest['parent_support_attempts']==manifest['selected_inputs']==1 and manifest['selected']==chosen[0]
    assert manifest['stop_reason']=='no_changed_c_file' and manifest['git_commands']==2
    assert manifest['file_requests']==manifest['rule_runs']==manifest['gate_runs']==manifest['patch_exports']==0
    assert manifest['observations']==[]
    for label in ['commit_object','path_names']:
        r=load(HERE/'raw'/f'{label}.receipt.json');assert r['returncode']==0
        for k in ['stdout','stderr']:assert sha(Path(r[k]))==r[k+'_sha256']
        prefix=['wsl','-d','Ubuntu','--','git','-C','/root/repos/linux']
        args=['cat-file','-p',chosen[0]['commit']] if label=='commit_object' else ['diff-tree','--no-commit-id','--name-only','-r','-z',chosen[0]['commit']]
        assert r['argv']==prefix+args
    raw=(HERE/'raw/commit_object.stdout.bin').read_bytes()
    assert hashlib.sha1(b'commit '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==chosen[0]['commit']
    parent=[l[7:].decode('ascii') for l in raw.split(b'\n\n',1)[0].splitlines() if l.startswith(b'parent ')]
    assert parent==[manifest['revision']]
    paths=(HERE/'raw/path_names.stdout.bin').read_bytes()
    assert paths.endswith(b'\0')
    names=[p.decode('utf-8') for p in paths.split(b'\0') if p]
    assert names==manifest['changed_path_names'] and names and not any(p.endswith('.c') for p in names)
    assert not (HERE/'sources').exists() and not (HERE/'c_selection_pre.json').exists() and not (HERE/'header_selection_pre.json').exists()
    card=load(HERE/'support_card.json');assert card['verdict']=='input_not_available_no_changed_c' and card['actual_support_proven'] is False
    review=load(HERE/'audit_support/review.json');assert review['review_passed'] is True and review['parent_manifest_sha256']==sha(HERE/'parent_manifest.json')
    return dict(metadata_pool=16,confirmed_prior_source_exposure=sum(r['source_exposure_confirmed'] for r in exposure['records']),
        selected_inputs=1,parent_support_attempts=1,git_commands=2,source_file_requests=0,saved_sources=0,
        detector_runs=0,source_gate_runs=0,patch_exports=0,new_confirmed_cases=0,independent_positive_cases=0,
        stop_reason='no_changed_c_file',rule_or_git_reexecution=False)
if __name__=='__main__':
    counts=verify();closed=HERE/'completion_manifest.json'
    if closed.exists():
        sealed=load(closed);check(sealed['files']);assert sealed['counts']==counts
    print(json.dumps(counts,ensure_ascii=False))
