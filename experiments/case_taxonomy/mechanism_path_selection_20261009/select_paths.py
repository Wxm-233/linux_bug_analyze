"""Metadata-only bounded selection and later frozen local Git path listing."""
from pathlib import Path
import hashlib,json,posixpath,re,subprocess,sys

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
PROJECT=HERE.parents[2]
INPUT=PROJECT/'analysis_out/stratified-20260921/manifest.json'
INPUT_SHA='8e61c456af84b1cee027a38793e4146a5d96bf652307fc83582e4c661f4d995a'
REP=r'(?<![A-Za-z0-9])(?:endian(?:ness)?|byte[ -]?order|(?:le|be)(?:16|32|64)|convert(?:ed|ing|s)?|conversion)(?![A-Za-z0-9])'
COUNT=r'(?<![A-Za-z0-9])(?:len|length|size|count|bytes)(?![A-Za-z0-9])'
PREFIXES={'arch','block','crypto','drivers','fs','include','init','ipc','kernel','lib','mm','net','security','sound','virt'}
DEPS=[BASE/'encoded_length_check_development_20261008/encoded_length_check.py',BASE/'interface_facts_20261008/interface_fact_extractor.py',BASE/'endian_consumer_single_revision.py',BASE/'declaration_source_gate_20261009/source_gate.py']

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def put(name,value):
    p=HERE/name
    assert not p.exists(),p
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def check(rows):
    for row in rows:assert sha(Path(row['path']))==row['sha256'],row['path']

def materialize():
    assert sha(INPUT)==INPUT_SHA
    data=load(INPUT);assert len(data['samples'])==500
    matches=[]
    for index,row in enumerate(data['samples'],1):
        a=re.search(REP,row['subject'],re.I);b=re.search(COUNT,row['subject'],re.I)
        if a and b:
            matches.append(dict(original_manifest_index=index,commit=row['hash'],subject=row['subject'],stratum=row['stratum'],band=row['band'],representation_match=a.group(),count_match=b.group()))
    put('metadata_pool.json',dict(source=str(INPUT),source_sha256=INPUT_SHA,sample_count=500,all_matching_count=len(matches),materialized_count=min(3,len(matches)),cap_applied_before_exposure=True,representation_regex=REP,count_regex=COUNT,model_results_used=False,records=matches[:3]))
    print(json.dumps(dict(all_matching_count=len(matches),materialized_count=min(3,len(matches)),metadata_sha256=sha(HERE/'metadata_pool.json')),ensure_ascii=False))

def freeze():
    pool=load(HERE/'metadata_pool.json');assert pool['source_sha256']==sha(INPUT)==INPUT_SHA
    audit=load(HERE/'audit_exposure/exposure_audit.json')
    assert audit['metadata_pool_sha256']==sha(HERE/'metadata_pool.json')
    rows={r['commit']:r for r in audit['records']}
    assert len(rows)==len(pool['records']) and set(rows)=={r['commit'] for r in pool['records']}
    queue=[r for r in pool['records'] if rows[r['commit']]['status']=='no_evidence_in_defined_scope' and rows[r['commit']]['source_exposure_confirmed'] is False]
    put('selection_pre.json',dict(queue=queue,excluded_commits=[r['commit'] for r in pool['records'] if r not in queue],no_replacement=True,queue_size=len(queue)))
    files=[HERE/'protocol_pre.md',HERE/'select_paths.py',HERE/'metadata_pool.json',HERE/'selection_pre.json',HERE/'audit_exposure/exposure_audit.json',HERE/'audit_exposure/review.md',INPUT,*DEPS]
    # Preserve the old closed stage identity without modifying or executing it.
    closed=BASE/'encoded_count_support_20261009/completion_manifest.json'
    assert sha(closed)=='77eb72ef71cb5b289f37c2d8673754082ed6164ba137e4061189fe30659540e0'
    check(load(closed)['files']);files.append(closed)
    put('freeze_pre.json',dict(files=[dict(path=str(p),sha256=sha(p)) for p in files],git_commands_before_freeze=0,new_source_requests_before_freeze=0,rule_runs_before_freeze=0))
    print(json.dumps(dict(queue_size=len(queue),freeze_sha256=sha(HERE/'freeze_pre.json')),ensure_ascii=False))

def classify(path):
    root=path.split('/')[0];suffix=posixpath.splitext(path)[1]
    if root in PREFIXES and suffix=='.c':return 'potential_kernel_c'
    if root in PREFIXES and suffix=='.h':return 'potential_implementation_header'
    if suffix in {'.c','.h'}:return 'tool_or_other_source'
    if root=='Documentation' or suffix in {'.md','.rst','.txt'}:return 'documentation'
    leaf=posixpath.basename(path)
    if leaf.startswith(('Kconfig','Makefile')) or leaf.endswith(('defconfig','.config')):return 'configuration'
    return 'other'

def run_paths():
    check(load(HERE/'freeze_pre.json')['files'])
    review=load(HERE/'audit_method/review.json')
    assert review['ready_for_path_queries'] is True
    assert review['script_sha256']==sha(HERE/'select_paths.py')
    assert review['freeze_sha256']==sha(HERE/'freeze_pre.json')
    queue=load(HERE/'selection_pre.json')['queue'];assert len(queue)<=3
    assert not (HERE/'path_manifest.json').exists() and not (HERE/'raw').exists()
    observations=[]
    for index,row in enumerate(queue,1):
        fix=row['commit'];assert re.fullmatch('[0-9a-f]{40}',fix)
        folder=HERE/'raw'/str(index);folder.mkdir(parents=True)
        argv=['wsl','-d','Ubuntu','--','git','-C','/root/repos/linux','diff-tree','--root','-m','--no-commit-id','--name-only','-r','-z',fix]
        p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        out=folder/'stdout.bin';err=folder/'stderr.bin';out.write_bytes(p.stdout);err.write_bytes(p.stderr)
        receipt=dict(argv=argv,returncode=p.returncode,stdout=str(out),stderr=str(err),stdout_sha256=sha(out),stderr_sha256=sha(err))
        put(f'raw/{index}/receipt.json',receipt)
        ob=dict(**row,query_index=index,receipt=str(folder/'receipt.json'),paths=[],classified=[],status='insufficient')
        if p.returncode:ob['reason']='path_query_failed'
        elif not p.stdout:ob['reason']='empty_path_listing'
        elif not p.stdout.endswith(b'\0'):ob['reason']='non_nul_path_listing'
        else:
            try:
                names=[x.decode('utf-8') for x in p.stdout.split(b'\0') if x]
                assert all(not x.startswith('/') and posixpath.normpath(x)==x and x not in {'.','..'} and not x.startswith('../') and '\n' not in x and '\r' not in x and '\\' not in x for x in names)
                unique=list(dict.fromkeys(names))
                ob.update(paths=names,classified=[dict(path=x,category=classify(x)) for x in unique],status='path_metadata_available',reason=None)
            except (UnicodeDecodeError,AssertionError):ob['reason']='unsupported_path_encoding_or_normalization'
        observations.append(ob)
    chosen=None
    for category in ['potential_kernel_c','potential_implementation_header']:
        for ob in observations:
            candidates=sorted(r['path'] for r in ob['classified'] if r['category']==category)
            if candidates:
                chosen=dict(commit=ob['commit'],subject=ob['subject'],original_manifest_index=ob['original_manifest_index'],source_path=candidates[0],path_category=category,query_index=ob['query_index'],parent_not_yet_determined=True,source_not_yet_read=True,inline_not_certified=True,support_not_yet_assessed=True)
                break
        if chosen:break
    stop='potential_implementation_path_selected' if chosen else ('no_unexposed_metadata_input' if not queue else 'no_supported_implementation_path_in_fixed_queue')
    put('path_manifest.json',dict(queue_size=len(queue),git_commands=len(queue),observations=observations,selected_path=chosen,stop_reason=stop,new_source_requests=0,rule_runs=0,gate_runs=0,patch_exports=0,new_confirmed_cases=0,independent_positive_cases=0))
    print(json.dumps(dict(queue_size=len(queue),git_commands=len(queue),selected_path=chosen,stop_reason=stop),ensure_ascii=False))

if __name__=='__main__':
    {'materialize':materialize,'freeze':freeze,'paths':run_paths}[sys.argv[1]]()
