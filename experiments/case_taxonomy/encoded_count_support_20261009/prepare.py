"""Freeze one metadata-selected input; export only bounded parent facts."""
from pathlib import Path
import hashlib,json,posixpath,re,subprocess,sys

HERE=Path(__file__).resolve().parent;BASE=HERE.parent
DEPS=[BASE/'encoded_length_check_development_20261008/encoded_length_check.py',
    BASE/'interface_facts_20261008/interface_fact_extractor.py',BASE/'endian_consumer_single_revision.py',
    BASE/'declaration_source_gate_20261009/source_gate.py',BASE/'declaration_source_gate_20261009/completion_manifest.json']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def put(name,v):
    p=HERE/name;assert not p.exists(),p;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def check(rows):
    for row in rows:assert sha(Path(row['path']))==row['sha256'],row['path']
def freeze():
    pool=load(HERE/'metadata_pool.json');assert pool['pool_count']==16
    audit=load(HERE/'audit_exposure/exposure_audit.json')
    assert audit['metadata_pool_sha256']==sha(HERE/'metadata_pool.json')
    rows={r['commit']:r for r in audit['records']}
    assert set(rows)=={r['commit'] for r in pool['records']}
    representation=re.compile(r'endian|byte[ -]?order|(?:le|be)(?:16|32|64)|convert|conversion',re.I)
    counts=re.compile(r'\b(?:len|length|size|count|bytes)\b',re.I)
    eligible=[r for r in pool['records'] if not rows[r['commit']]['source_exposure_confirmed'] and representation.search(r['subject'])]
    priority=[r for r in eligible if counts.search(r['subject'])]
    queue=(priority or eligible)[:1]
    put('selection_pre.json',dict(queue=queue,pool_count=16,eligible_commits=[r['commit'] for r in eligible],
        count_hint_commits=[r['commit'] for r in priority],source_exposed_commits=[c for c,r in rows.items() if r['source_exposure_confirmed']],
        selected_by_metadata_only=True,new_source_before_selection=False))
    closed=BASE/'declaration_source_gate_20261009/completion_manifest.json'
    assert sha(closed)=='6a915838025e4dbe51a5ed2e0974c0090a092e15e4bc78378b54329735d5aff7'
    check(load(closed)['files'])
    files=[HERE/'protocol_pre.md',HERE/'metadata_pool.py',HERE/'metadata_pool.json',HERE/'prepare.py',HERE/'selection_pre.json',
        HERE/'audit_exposure/exposure_audit.json',HERE/'audit_exposure/review.md',Path(pool['source']),*DEPS]
    put('freeze_metadata_pre.json',dict(files=[dict(path=str(p),sha256=sha(p)) for p in files],source_exports_before_lock=0,rule_runs_before_lock=0,patch_exports_before_lock=0))
    print(json.dumps(dict(pool_count=16,queue=[r['commit'] for r in queue],freeze_sha256=sha(HERE/'freeze_metadata_pre.json')),ensure_ascii=False))

def command(label,args,stdin=None):
    folder=HERE/'raw';folder.mkdir(exist_ok=True)
    out=folder/(label+'.stdout.bin');err=folder/(label+'.stderr.bin')
    assert not out.exists() and not err.exists()
    argv=['wsl','-d','Ubuntu','--','git','-C','/root/repos/linux',*args]
    if stdin is not None:(folder/(label+'.stdin.bin')).write_bytes(stdin)
    p=subprocess.run(argv,input=stdin,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out.write_bytes(p.stdout);err.write_bytes(p.stderr)
    receipt=dict(argv=argv,returncode=p.returncode,stdout=str(out),stderr=str(err),stdout_sha256=sha(out),stderr_sha256=sha(err))
    if stdin is not None:receipt.update(stdin=str(folder/(label+'.stdin.bin')),stdin_sha256=sha(folder/(label+'.stdin.bin')))
    put('raw/'+label+'.receipt.json',receipt)
    return p
def batch(label,revision,targets):
    specs=[revision+':'+t['source_path'] for t in targets]
    p=command(label,['cat-file','--batch'],('\n'.join(specs)+'\n').encode('utf-8'))
    if p.returncode:return [],'batch_process_failed'
    offset=0;obs=[]
    for target,spec in zip(targets,specs):
        end=p.stdout.index(b'\n',offset);header=p.stdout[offset:end];offset=end+1
        if header==(spec+' missing').encode('utf-8'):
            obs.append(dict(**target,revision=revision,status='missing',response_header=header.decode('utf-8')));continue
        oid,kind,size=header.split();assert kind==b'blob' and re.fullmatch(rb'[0-9a-f]{40}',oid);size=int(size)
        raw=p.stdout[offset:offset+size]
        assert size>=0 and len(raw)==size and p.stdout[offset+size:offset+size+1]==b'\n';offset+=size+1
        assert hashlib.sha1(b'blob '+str(size).encode()+b'\0'+raw).hexdigest()==oid.decode('ascii')
        saved=HERE/'sources'/target['saved_name'];assert not saved.exists();saved.parent.mkdir(exist_ok=True);saved.write_bytes(raw)
        obs.append(dict(**target,revision=revision,status='saved',saved_path=str(saved),sha256=sha(saved),blob_sha1=oid.decode('ascii'),byte_count=size,response_header=header.decode('ascii')))
    assert offset==len(p.stdout)
    return obs,'batch_complete'
def export():
    check(load(HERE/'freeze_metadata_pre.json')['files'])
    review=load(HERE/'audit_method/review.json')
    assert review['ready_for_export'] is True and review['exporter_sha256']==sha(HERE/'prepare.py')
    assert review['metadata_lock_sha256']==sha(HERE/'freeze_metadata_pre.json')
    queue=load(HERE/'selection_pre.json')['queue']
    report=dict(selected_inputs=len(queue),parent_support_attempts=0,git_commands=0,file_requests=0,observations=[],rule_runs=0,gate_runs=0,patch_exports=0)
    assert not (HERE/'parent_manifest.json').exists()
    try:
        if not queue:report['stop_reason']='no_metadata_eligible_input';return
        item=queue[0];fix=item['commit'];assert re.fullmatch('[0-9a-f]{40}',fix)
        report['parent_support_attempts']=1;report['selected']=item
        p=command('commit_object',['cat-file','-p',fix]);report['git_commands']+=1
        if p.returncode:report['stop_reason']='commit_unavailable';return
        header=p.stdout.split(b'\n\n',1)[0]
        parents=[line[7:].decode('ascii') for line in header.splitlines() if line.startswith(b'parent ')]
        if len(parents)!=1 or not re.fullmatch('[0-9a-f]{40}',parents[0]):report['stop_reason']='not_single_parent';return
        revision=parents[0];report['revision']=revision
        p=command('path_names',['diff-tree','--no-commit-id','--name-only','-r','-z',fix]);report['git_commands']+=1
        if p.returncode:report['stop_reason']='path_listing_failed';return
        assert not p.stdout or p.stdout.endswith(b'\0')
        paths=[s.decode('utf-8') for s in p.stdout.split(b'\0') if s]
        report['changed_path_names']=paths;cs=sorted(path for path in paths if path.endswith('.c'))
        if not cs:report['stop_reason']='no_changed_c_file';return
        path=cs[0]
        if path.startswith('/') or '\n' in path or '\r' in path or posixpath.normpath(path)!=path or path.startswith('../'):
            report['stop_reason']='unsupported_c_path';return
        target=dict(role='primary_c',source_path=path,saved_name='parent_source.c')
        put('c_selection_pre.json',dict(revision=revision,target=target,changed_path_names_sha256=sha(HERE/'raw/path_names.stdout.bin')))
        obs,status=batch('parent_c',revision,[target]);report['git_commands']+=1;report['file_requests']+=1;report['observations']+=obs
        if status!='batch_complete' or not obs or obs[0]['status']!='saved':report['stop_reason']='parent_c_unavailable';return
        raw=Path(obs[0]['saved_path']).read_bytes()
        quoted=[]
        for i,line in enumerate(raw.decode('utf-8').splitlines(),1):
            match=re.fullmatch(r'\s*#\s*include\s*"([^"\n]+)"\s*',line)
            if not match:continue
            token=match.group(1);name=posixpath.normpath(posixpath.join(posixpath.dirname(path),token))
            quoted.append(dict(token=token,line=i,source_path=name))
            if len(quoted)==2:break
        targets=[]
        for i,q in enumerate(quoted,1):
            name=q['source_path']
            if name.startswith('/') or name=='..' or name.startswith('../') or '\n' in name or '\r' in name:
                report['stop_reason']='quoted_header_outside_namespace';put('header_selection_pre.json',dict(revision=revision,quoted=quoted,requests=[],stopped=True));return
            targets.append(dict(role='quoted_header_'+str(i),source_path=name,saved_name='parent_header_'+str(i)+'.h',include_token=q['token'],include_line=q['line']))
        put('header_selection_pre.json',dict(revision=revision,quoted=quoted,requests=targets,parent_c_sha256=obs[0]['sha256']))
        if targets:
            obs,status=batch('parent_headers',revision,targets);report['git_commands']+=1;report['file_requests']+=len(targets);report['observations']+=obs
            if status!='batch_complete':report['stop_reason']='header_batch_failed';return
        report['stop_reason']='fixed_parent_material_complete'
    finally:
        put('parent_manifest.json',report)
        print(json.dumps({k:v for k,v in report.items() if k not in ['observations','selected','changed_path_names']},ensure_ascii=False))
if __name__=='__main__':
    try:{'freeze':freeze,'export':export}[sys.argv[1]]()
    except Exception as error:
        put('failure_'+sys.argv[1]+'.json',dict(error_type=type(error).__name__,message=str(error),no_automatic_retry=True));raise
