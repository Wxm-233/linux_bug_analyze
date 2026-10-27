"""Freeze and retrieve one revision type plus three fixed historical file objects."""
from pathlib import Path
import hashlib,json,posixpath,re,subprocess,sys

HERE=Path(__file__).resolve().parent;BASE=HERE.parent
REV='3123109284176b1532874591f7c81f3837bbdc17'
TARGETS=[('private_header','drivers/staging/r8188eu/include/linux/if_pppox.h','private_if_pppox.h'),
         ('makefile','drivers/staging/r8188eu/Makefile','Makefile'),
         ('kconfig','drivers/staging/r8188eu/Kconfig','Kconfig')]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def put(name,value):
    p=HERE/name;assert not p.exists(),p;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def check(files):
    for f in files:assert sha(Path(f['path']))==f['sha256'],f['path']
def freeze():
    previous=BASE/'encoded_length_composition_20261009'
    closed=previous/'completion_manifest.json'
    assert sha(closed)=='812baaac9631cded48930b391a5f4bf3daa19dfbdc48c70b4fe0851ddb205041'
    check(load(closed)['files'])
    old=load(previous/'inputs_pre.json')['sources'][0];assert old['revision']==REV
    source=Path(old['saved_path']);assert sha(source)==old['sha256']
    lines=source.read_text(encoding='utf-8').splitlines()
    matches=[(i+1,re.fullmatch(r'\s*#\s*include\s*"([^"]*if_pppox\.h)"\s*',line)) for i,line in enumerate(lines)]
    candidates=[(n,m.group(1)) for n,m in matches if m];assert len(candidates)==1
    line,token=candidates[0]
    normalized=posixpath.normpath(posixpath.join(posixpath.dirname(old['source_path']),token))
    assert normalized==TARGETS[0][1]
    put('inputs_pre.json',dict(revision=REV,repository='/root/repos/linux',old_source=old,
        include=dict(token=token,start_line=line,end_line=line,text=lines[line-1],
            primary_relative_path=normalized,actual_include_binding_certified=False),
        targets=[dict(role=role,source_path=path,saved_name=name) for role,path,name in TARGETS],
        previous_completion_path=str(closed),previous_completion_sha256=sha(closed),
        max_file_requests=3,max_git_commands=2,all_three_are_fixed_independent_requests=True,
        no_alternative_paths=True,new_confirmed_cases=0,independent_positive_cases=0))
    paths=[HERE/'protocol_pre.md',HERE/'prepare_export.py',HERE/'inputs_pre.json',closed,source,previous/'inputs_pre.json']
    put('freeze_inputs_pre.json',dict(files=[dict(path=str(p),sha256=sha(p)) for p in paths],
        new_git_commands_before_lock=0,file_requests_before_lock=0))
    print(json.dumps(dict(freeze_sha256=sha(HERE/'freeze_inputs_pre.json'),fixed_file_requests=3),ensure_ascii=False))
def command(label,args,stdin=None):
    folder=HERE/'raw';folder.mkdir(exist_ok=True)
    out=folder/(label+'.stdout.bin');err=folder/(label+'.stderr.bin')
    assert not out.exists() and not err.exists()
    argv=['wsl','-d','Ubuntu','--','git','-C','/root/repos/linux',*args]
    if stdin is not None:
        target=folder/(label+'.stdin.bin');assert not target.exists();target.write_bytes(stdin)
    p=subprocess.run(argv,input=stdin,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out.write_bytes(p.stdout);err.write_bytes(p.stderr)
    receipt=dict(argv=argv,returncode=p.returncode,stdout=str(out),stderr=str(err),stdout_sha256=sha(out),stderr_sha256=sha(err))
    if stdin is not None:receipt.update(stdin=str(target),stdin_sha256=sha(target))
    put('raw/'+label+'.receipt.json',receipt)
    return p
def export():
    check(load(HERE/'freeze_inputs_pre.json')['files']);inputs=load(HERE/'inputs_pre.json')
    check(load(Path(inputs['previous_completion_path']))['files'])
    review=load(HERE/'audit_protocol/review_code_pre.json')
    assert review['exporter_sha256']==sha(HERE/'prepare_export.py') and review['ready_for_export'] is True
    status=command('revision_type',['cat-file','-t',REV])
    if status.returncode or status.stdout.strip()!=b'commit':
        put('export_manifest.json',dict(status='revision_unavailable',git_commands=1,file_requests=0,observations=[],new_confirmed_cases=0))
        raise SystemExit('specified revision not available as a commit; no file requests')
    specs=[REV+':'+path for role,path,name in TARGETS]
    raw=command('file_batch',['cat-file','--batch'],('\n'.join(specs)+'\n').encode('ascii'))
    if raw.returncode:
        put('export_manifest.json',dict(status='batch_process_failed',git_commands=2,file_requests=3,observations=[],new_confirmed_cases=0))
        raise SystemExit('batch process failed; raw streams preserved')
    offset=0;observations=[]
    for (role,path,name),spec in zip(TARGETS,specs):
        end=raw.stdout.index(b'\n',offset);header=raw.stdout[offset:end];offset=end+1
        if header==(spec+' missing').encode('ascii'):
            observations.append(dict(role=role,source_path=path,revision=REV,status='missing',response_header=header.decode('ascii')))
            continue
        pieces=header.split();assert len(pieces)==3 and pieces[1]==b'blob'
        oid=pieces[0].decode('ascii');assert re.fullmatch('[0-9a-f]{40}',oid)
        size=int(pieces[2]);assert size>=0
        content=raw.stdout[offset:offset+size];assert len(content)==size and raw.stdout[offset+size:offset+size+1]==b'\n';offset+=size+1
        assert hashlib.sha1(b'blob '+str(size).encode()+b'\0'+content).hexdigest()==oid
        p=HERE/name;assert not p.exists();p.write_bytes(content)
        observations.append(dict(role=role,source_path=path,saved_path=str(p),revision=REV,status='saved',blob_sha1=oid,
            sha256=sha(p),byte_count=size,response_header=header.decode('ascii')))
    assert offset==len(raw.stdout) and len(observations)==3
    put('export_manifest.json',dict(status='fixed_requests_complete',revision=REV,git_commands=2,file_requests=3,
        observations=observations,saved_files=sum(o['status']=='saved' for o in observations),
        missing_files=sum(o['status']=='missing' for o in observations),alternative_requests=0,
        actual_include_binding_certified=False,actual_build_certified=False,new_confirmed_cases=0,independent_positive_cases=0))
    print(json.dumps(dict(git_commands=2,file_requests=3,observations=[dict(role=o['role'],status=o['status']) for o in observations],
        actual_build_certified=False,new_confirmed_cases=0),ensure_ascii=False))
if __name__=='__main__':
    try:{'freeze':freeze,'export':export}[sys.argv[1]]()
    except Exception as e:
        put('failure_'+sys.argv[1]+'.json',dict(error_type=type(e).__name__,message=str(e),no_automatic_retry=True));raise
