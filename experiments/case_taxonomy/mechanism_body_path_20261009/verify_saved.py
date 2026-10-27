"""Read-only saved metadata/message/path checks; no Git or detector invocation."""
from pathlib import Path
import hashlib,json,posixpath,re

HERE=Path(__file__).resolve().parent;BASE=HERE.parent
REP=r'(?<![A-Za-z0-9])(?:endian(?:ness)?|byte[ -]?order|(?:le|be)(?:16|32|64)|convert(?:ed|ing|s)?|conversion)(?![A-Za-z0-9])'
COUNT=r'(?<![A-Za-z0-9])(?:len|length|size|count|bytes)(?![A-Za-z0-9])'
PREFIXES={'arch','block','crypto','drivers','fs','include','init','ipc','kernel','lib','mm','net','security','sound','virt'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def receipt(relative,expected_args):
    p=HERE/relative;row=load(p)
    assert row['argv']==['wsl','-d','Ubuntu','--','git','-C','/root/repos/linux',*expected_args]
    for key in ['stdout','stderr']:assert sha(Path(row[key]))==row[key+'_sha256']
    return row,Path(row['stdout']).read_bytes()

def verify():
    pool=load(HERE/'metadata_pool.json');source=Path(pool['source'])
    assert sha(source)==pool['source_sha256']=='8e61c456af84b1cee027a38793e4146a5d96bf652307fc83582e4c661f4d995a'
    samples=load(source)['samples'];assert len(samples)==pool['sample_count']==500
    represented=[(i,s) for i,s in enumerate(samples,1) if s['stratum']=='representation'][32:64]
    assert len(represented)==pool['pool_count']<=32
    assert pool['representation_regex']==REP and pool['count_regex']==COUNT and pool['model_results_used'] is False
    for order,(r,(index,s)) in enumerate(zip(pool['records'],represented),1):
        assert r['pool_order']==order and r['representation_order']==order+32 and r['original_manifest_index']==index
        assert all(r[k]==s[v] for k,v in [('commit','hash'),('subject','subject'),('stratum','stratum'),('band','band')])
        m=re.search(REP,s['subject'],re.I);assert r['representation_title_match']==(m.group() if m else None)
    audit=load(HERE/'audit_exposure/exposure_audit.json')
    assert audit['metadata_pool_sha256']==sha(HERE/'metadata_pool.json')
    assert len(audit['records'])==len(pool['records'])
    for r in audit['searched_files']:
        p=Path(r['path']);p=p if p.is_absolute() else BASE/p
        assert sha(p)==r['sha256'],r['path']
    byhash={r['commit']:r for r in audit['records']};assert set(byhash)=={r['commit'] for r in pool['records']}
    eligible=[r for r in pool['records'] if r['representation_title_match'] is not None and byhash[r['commit']]['status']=='no_evidence_in_defined_scope' and byhash[r['commit']]['source_exposure_confirmed'] is False]
    selection=load(HERE/'selection_pre.json');queue=selection['queue']
    assert queue==eligible[:8] and selection['eligible_count']==len(eligible) and selection['queue_cap']==8
    lock=load(HERE/'freeze_pre.json')
    for row in lock['files']:assert sha(Path(row['path']))==row['sha256'],row['path']
    method=load(HERE/'audit_method/review.json')
    assert method['ready_for_retrieval'] is True and method['script_sha256']==sha(HERE/'prepare.py') and method['freeze_sha256']==sha(HERE/'freeze_pre.json')
    result=load(HERE/'retrieval_manifest.json');assert result['queue_size']==len(queue)
    assert len(result['observations'])==len(queue)
    count=0;quote_records=0
    for i,(item,ob) in enumerate(zip(queue,result['observations']),1):
        assert ob['queue_index']==i and all(ob[k]==item[k] for k in item)
        r,raw=receipt(ob['commit_receipt'],['cat-file','-p',item['commit']]);count+=1
        if r['returncode']!=0:
            assert ob['reason']=='commit_unavailable' and ob['path_receipt'] is None;continue
        assert hashlib.sha1(b'commit '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==item['commit']
        header,sep,payload=raw.partition(b'\n\n');assert sep
        parents=[line[7:].decode('ascii') for line in header.splitlines() if line.startswith(b'parent ')]
        if ob['parent'] is None:
            assert ob['status']=='insufficient' and ob['path_receipt'] is None;continue
        assert parents==[ob['parent']]
        lines=payload.decode('utf-8').splitlines();assert ob['message_subject']==lines[0]
        joined=ob['body_lines']+ob['removed_trailer_lines']
        indices=[r['message_line'] for r in joined]
        assert len(indices)==len(set(indices))
        assert sorted(indices)==[n for n,text in enumerate(lines,1) if n>1 and text.strip()]
        for q in joined:
            assert q['text']==lines[q['message_line']-1];quote_records+=1
        assert ob['count_hint_lines']==[q for q in ob['body_lines'] if re.search(COUNT,q['text'],re.I)]
        r,raw=receipt(ob['path_receipt'],['diff-tree','--root','-m','--no-commit-id','--name-only','-r','-z',item['commit']]);count+=1
        if ob['status']!='message_and_paths_available':
            assert ob['reason'] is not None;continue
        assert r['returncode']==0 and raw and raw.endswith(b'\0')
        names=[s.decode('utf-8') for s in raw.split(b'\0') if s]
        assert names==ob['paths'] and [q['path'] for q in ob['classified']]==list(dict.fromkeys(names))
        for q in ob['classified']:
            path=q['path'];assert not path.startswith('/') and posixpath.normpath(path)==path and not path.startswith('../')
            if path.split('/')[0] in PREFIXES and path.endswith('.c'):assert q['category']=='potential_kernel_c'
            if path.split('/')[0] in PREFIXES and path.endswith('.h'):assert q['category']=='potential_implementation_header'
    assert count==result['git_commands']<=16
    saved_receipts=list((HERE/'raw').rglob('receipt.json')) if (HERE/'raw').exists() else []
    assert len(saved_receipts)==count
    expected=None
    for category in ['potential_kernel_c','potential_implementation_header']:
        for ob in result['observations']:
            if ob['status']!='message_and_paths_available' or not ob['count_hint_lines']:continue
            paths=sorted(q['path'] for q in ob['classified'] if q['category']==category)
            if paths:expected=(ob,paths[0],category);break
        if expected:break
    if expected:
        ob,path,category=expected;chosen=result['selected_path']
        assert chosen['commit']==ob['commit'] and chosen['parent']==ob['parent'] and chosen['queue_index']==ob['queue_index']
        assert chosen['source_path']==path and chosen['path_category']==category and chosen['count_hint_lines']==ob['count_hint_lines']
        assert chosen['selection_only_not_bug_truth'] is True and chosen['message_read_before_source_test'] is True and chosen['source_not_yet_read'] is True
        assert result['stop_reason']=='potential_implementation_path_selected'
    else:assert result['selected_path'] is None and result['stop_reason'] in {'no_metadata_queue','no_body_count_and_implementation_in_fixed_queue'}
    for key in ['new_source_requests','rule_runs','gate_runs','patch_exports','new_confirmed_cases','independent_positive_cases']:assert result[key]==0,key
    assert not (HERE/'sources').exists()
    independent=load(HERE/'audit_result/review.json')
    assert independent['review_passed'] is True and independent['retrieval_manifest_sha256']==sha(HERE/'retrieval_manifest.json') and independent['freeze_sha256']==sha(HERE/'freeze_pre.json')
    previous=BASE/'mechanism_path_selection_20261009/completion_manifest.json'
    assert sha(previous)=='9f24a2b2f5b33319cce5cc393d1845c4f3b859db39c6babc3428cb33e71f2622'
    for row in load(previous)['files']:assert sha(Path(row['path']))==row['sha256']
    return dict(verification_passed=True,metadata_pool=len(pool['records']),title_matches=sum(r['representation_title_match'] is not None for r in pool['records']),exposure_confirmed=sum(r['source_exposure_confirmed'] for r in audit['records']),queue_size=len(queue),git_commands=count,message_quote_records=quote_records,implementation_path_selected=result['selected_path'] is not None,new_source_requests=0,detector_runs=0,gate_runs=0,patch_exports=0,new_confirmed_cases=0,independent_positive_cases=0,stop_reason=result['stop_reason'],old_closed_stage_unchanged=True)
if __name__=='__main__':print(json.dumps(verify(),ensure_ascii=False))
