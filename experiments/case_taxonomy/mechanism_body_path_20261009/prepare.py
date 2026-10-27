"""Prospective metadata queue and bounded commit-message/path retrieval only."""
from pathlib import Path
import hashlib,json,posixpath,re,subprocess,sys

HERE=Path(__file__).resolve().parent;BASE=HERE.parent;PROJECT=HERE.parents[2]
INPUT=PROJECT/'analysis_out/stratified-20260921/manifest.json'
INPUT_SHA='8e61c456af84b1cee027a38793e4146a5d96bf652307fc83582e4c661f4d995a'
REP=r'(?<![A-Za-z0-9])(?:endian(?:ness)?|byte[ -]?order|(?:le|be)(?:16|32|64)|convert(?:ed|ing|s)?|conversion)(?![A-Za-z0-9])'
COUNT=r'(?<![A-Za-z0-9])(?:len|length|size|count|bytes)(?![A-Za-z0-9])'
PREFIXES={'arch','block','crypto','drivers','fs','include','init','ipc','kernel','lib','mm','net','security','sound','virt'}
TRAILERS={'signed-off-by','reviewed-by','acked-by','tested-by','reported-by','suggested-by','co-developed-by','fixes','link','cc','closes','stable-dep-of','message-id'}
DEPS=[BASE/'encoded_length_check_development_20261008/encoded_length_check.py',BASE/'interface_facts_20261008/interface_fact_extractor.py',BASE/'endian_consumer_single_revision.py',BASE/'declaration_source_gate_20261009/source_gate.py']

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def put(name,value):
    p=HERE/name;assert not p.exists(),p;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def check(rows):
    for row in rows:assert sha(Path(row['path']))==row['sha256'],row['path']

def materialize():
    assert sha(INPUT)==INPUT_SHA
    data=load(INPUT);assert len(data['samples'])==500
    records=[];order=0
    for index,row in enumerate(data['samples'],1):
        if row['stratum']!='representation':continue
        order+=1
        if 33<=order<=64:
            m=re.search(REP,row['subject'],re.I)
            records.append(dict(pool_order=len(records)+1,representation_order=order,original_manifest_index=index,commit=row['hash'],subject=row['subject'],stratum=row['stratum'],band=row['band'],representation_title_match=m.group() if m else None))
        if order==64:break
    put('metadata_pool.json',dict(source=str(INPUT),source_sha256=INPUT_SHA,sample_count=500,range_start=33,range_end=64,pool_count=len(records),representation_regex=REP,count_regex=COUNT,model_results_used=False,records=records))
    print(json.dumps(dict(pool_count=len(records),title_matches=sum(r['representation_title_match'] is not None for r in records),metadata_pool_sha256=sha(HERE/'metadata_pool.json')),ensure_ascii=False))

def freeze():
    pool=load(HERE/'metadata_pool.json');assert pool['source_sha256']==sha(INPUT)==INPUT_SHA
    audit=load(HERE/'audit_exposure/exposure_audit.json')
    assert audit['metadata_pool_sha256']==sha(HERE/'metadata_pool.json')
    rows={r['commit']:r for r in audit['records']};assert len(rows)==len(pool['records']) and set(rows)=={r['commit'] for r in pool['records']}
    eligible=[r for r in pool['records'] if r['representation_title_match'] is not None and rows[r['commit']]['status']=='no_evidence_in_defined_scope' and rows[r['commit']]['source_exposure_confirmed'] is False]
    put('selection_pre.json',dict(queue=eligible[:8],eligible_count=len(eligible),queue_cap=8,no_replacement_after_retrieval=True,source_exposed_commits=[r['commit'] for r in pool['records'] if rows[r['commit']]['source_exposure_confirmed']],selected_by_metadata_only=True))
    files=[HERE/'protocol_pre.md',HERE/'prepare.py',HERE/'metadata_pool.json',HERE/'selection_pre.json',INPUT,*DEPS]
    # Bind the complete saved exposure audit, not only its summary JSON.
    files.extend(sorted(p for p in (HERE/'audit_exposure').rglob('*') if p.is_file()))
    for row in audit['searched_files']:
        source=Path(row['path'])
        if not source.is_absolute():source=BASE/source
        assert sha(source)==row['sha256'],row['path']
    closed=BASE/'mechanism_path_selection_20261009/completion_manifest.json'
    assert sha(closed)=='9f24a2b2f5b33319cce5cc393d1845c4f3b859db39c6babc3428cb33e71f2622'
    check(load(closed)['files']);files.append(closed)
    put('freeze_pre.json',dict(files=[dict(path=str(p),sha256=sha(p)) for p in files],git_before_freeze=0,source_before_freeze=0,rule_before_freeze=0))
    print(json.dumps(dict(queue_size=min(8,len(eligible)),freeze_sha256=sha(HERE/'freeze_pre.json')),ensure_ascii=False))

def body_lines(message):
    lines=message.splitlines();blocks=[];current=[]
    for number,text in enumerate(lines[1:],2):
        if text.strip():current.append(dict(message_line=number,text=text))
        elif current:blocks.append(current);current=[]
    if current:blocks.append(current)
    removed=[]
    while blocks:
        seen=False;valid=True
        for row in blocks[-1]:
            text=row['text']
            if text[:1].isspace():
                if not seen:valid=False;break
                continue
            m=re.match(r'^([A-Za-z][A-Za-z0-9-]*):\s*.*$',text)
            if not m or m.group(1).lower() not in TRAILERS:valid=False;break
            seen=True
        if not valid or not seen:break
        removed=blocks.pop()+removed
    return [row for block in blocks for row in block],removed

def classify(path):
    top=path.split('/')[0];suffix=posixpath.splitext(path)[1]
    if top in PREFIXES and suffix=='.c':return 'potential_kernel_c'
    if top in PREFIXES and suffix=='.h':return 'potential_implementation_header'
    if suffix in {'.c','.h'}:return 'tool_or_other_source'
    if top=='Documentation' or suffix in {'.md','.rst','.txt'}:return 'documentation'
    leaf=posixpath.basename(path)
    if leaf.startswith(('Kconfig','Makefile')) or leaf.endswith(('defconfig','.config')):return 'configuration'
    return 'other'

def command(label,args):
    folder=HERE/'raw'/label;assert not folder.exists();folder.mkdir(parents=True)
    argv=['wsl','-d','Ubuntu','--','git','-C','/root/repos/linux',*args]
    p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out=folder/'stdout.bin';err=folder/'stderr.bin';out.write_bytes(p.stdout);err.write_bytes(p.stderr)
    put(f'raw/{label}/receipt.json',dict(argv=argv,returncode=p.returncode,stdout=str(out),stderr=str(err),stdout_sha256=sha(out),stderr_sha256=sha(err)))
    return p

def retrieve():
    check(load(HERE/'freeze_pre.json')['files'])
    review=load(HERE/'audit_method/review.json')
    assert review['ready_for_retrieval'] is True and review['script_sha256']==sha(HERE/'prepare.py') and review['freeze_sha256']==sha(HERE/'freeze_pre.json')
    queue=load(HERE/'selection_pre.json')['queue'];assert len(queue)<=8
    assert not (HERE/'raw').exists() and not (HERE/'retrieval_manifest.json').exists()
    observations=[];calls=0
    for i,row in enumerate(queue,1):
        fix=row['commit'];assert re.fullmatch('[0-9a-f]{40}',fix)
        ob=dict(**row,queue_index=i,status='insufficient',parent=None,message_subject=None,body_lines=[],removed_trailer_lines=[],count_hint_lines=[],paths=[],classified=[],commit_receipt=f'raw/{i}_commit/receipt.json',path_receipt=None)
        observations.append(ob)
        p=command(f'{i}_commit',['cat-file','-p',fix]);calls+=1
        if p.returncode:ob['reason']='commit_unavailable';continue
        if hashlib.sha1(b'commit '+str(len(p.stdout)).encode()+b'\0'+p.stdout).hexdigest()!=fix:ob['reason']='commit_identity_mismatch';continue
        header,separator,payload=p.stdout.partition(b'\n\n')
        if not separator:ob['reason']='malformed_commit';continue
        try:
            parents=[line[7:].decode('ascii') for line in header.splitlines() if line.startswith(b'parent ')]
            if len(parents)!=1 or not re.fullmatch('[0-9a-f]{40}',parents[0]):ob['reason']='not_single_parent';continue
            message=payload.decode('utf-8')
        except UnicodeDecodeError:ob['reason']='unsupported_commit_encoding';continue
        if not message.splitlines():ob['reason']='missing_message_subject';continue
        body,removed=body_lines(message)
        ob.update(parent=parents[0],message_subject=message.splitlines()[0],body_lines=body,removed_trailer_lines=removed,count_hint_lines=[r for r in body if re.search(COUNT,r['text'],re.I)])
        p=command(f'{i}_paths',['diff-tree','--root','-m','--no-commit-id','--name-only','-r','-z',fix]);calls+=1;ob['path_receipt']=f'raw/{i}_paths/receipt.json'
        if p.returncode:ob['reason']='path_query_failed';continue
        if not p.stdout or not p.stdout.endswith(b'\0'):ob['reason']='empty_or_non_nul_path_listing';continue
        try:
            names=[x.decode('utf-8') for x in p.stdout.split(b'\0') if x]
            assert all(not x.startswith('/') and posixpath.normpath(x)==x and x not in {'.','..'} and not x.startswith('../') and '\n' not in x and '\r' not in x and '\\' not in x for x in names)
        except (UnicodeDecodeError,AssertionError):ob['reason']='unsupported_paths';continue
        ob.update(paths=names,classified=[dict(path=x,category=classify(x)) for x in dict.fromkeys(names)],status='message_and_paths_available',reason=None)
    chosen=None
    for category in ['potential_kernel_c','potential_implementation_header']:
        for ob in observations:
            if ob['status']!='message_and_paths_available' or not ob['count_hint_lines']:continue
            names=sorted(x['path'] for x in ob['classified'] if x['category']==category)
            if not names:continue
            chosen=dict(commit=ob['commit'],parent=ob['parent'],subject=ob['subject'],queue_index=ob['queue_index'],source_path=names[0],path_category=category,count_hint_lines=ob['count_hint_lines'],selection_only_not_bug_truth=True,message_read_before_source_test=True,source_not_yet_read=True,inline_not_certified=True,detector_support_not_yet_assessed=True)
            break
        if chosen:break
    stop='potential_implementation_path_selected' if chosen else ('no_metadata_queue' if not queue else 'no_body_count_and_implementation_in_fixed_queue')
    put('retrieval_manifest.json',dict(queue_size=len(queue),git_commands=calls,observations=observations,selected_path=chosen,stop_reason=stop,new_source_requests=0,rule_runs=0,gate_runs=0,patch_exports=0,new_confirmed_cases=0,independent_positive_cases=0))
    print(json.dumps(dict(queue_size=len(queue),git_commands=calls,selected_path=chosen,stop_reason=stop),ensure_ascii=False))

if __name__=='__main__':{'materialize':materialize,'freeze':freeze,'retrieve':retrieve}[sys.argv[1]]()
