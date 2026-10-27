"""Freeze prior saved facts, then retrieve exactly two fixed Git blobs once."""
from pathlib import Path
import hashlib,json,re,subprocess,sys

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
REV='3123109284176b1532874591f7c81f3837bbdc17'
TARGETS=[('top_makefile','Makefile','top_Makefile'),('public_wrapper','include/linux/if_pppox.h','public_if_pppox.h')]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def put(name,obj):
    p=HERE/name
    assert not p.exists(),p
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def check(records):
    for row in records:assert sha(Path(row['path']))==row['sha256'],row['path']

def freeze():
    prev=BASE/'driver_binding_20261009'
    closed=prev/'completion_manifest.json'
    assert sha(closed)=='8202d4ed033658bc0b6facdcbe6388e858e461928f19e0c56daea43c96009b4e'
    check(read(closed)['files'])
    old=read(prev/'inputs_pre.json')['old_source']
    assert old['revision']==REV
    source=Path(old['saved_path'])
    assert sha(source)==old['sha256']
    uapi=BASE/'encoded_length_contract_20261008'/'parent_if_pppox.h'
    assert sha(uapi)=='aa3da6f6a3f1bc67b2507afde489106f895c07553723f04cda3dfbb10ec03b1e'
    revision_receipt=prev/'raw/revision_type.receipt.json'
    receipt=read(revision_receipt)
    assert receipt['returncode']==0
    assert Path(receipt['stdout']).read_bytes().strip()==b'commit'
    assert receipt['argv'][-1]==REV
    inputs=dict(revision=REV,old_source=old,uapi_source=dict(saved_path=str(uapi),source_path='include/uapi/linux/if_pppox.h',revision=REV,sha256=sha(uapi)),
        previous_completion_path=str(closed),previous_completion_sha256=sha(closed),
        revision_receipt=str(revision_receipt),revision_exists_from_previous_receipt=True,
        targets=[dict(role=r,source_path=p,saved_name=n) for r,p,n in TARGETS],max_git_commands=1,max_file_requests=2,
        actual_preprocessing_certified=False,new_confirmed_cases=0,independent_positive_cases=0)
    put('inputs_pre.json',inputs)
    paths=[HERE/'protocol_pre.md',HERE/'retrieve.py',HERE/'inputs_pre.json',closed,source,uapi,revision_receipt,Path(receipt['stdout'])]
    put('freeze_pre.json',dict(files=[dict(path=str(p),sha256=sha(p)) for p in paths],new_git_commands_before_lock=0))
    print(json.dumps(dict(freeze_sha256=sha(HERE/'freeze_pre.json'),fixed_requests=2)))

def export():
    check(read(HERE/'freeze_pre.json')['files'])
    check(read(Path(read(HERE/'inputs_pre.json')['previous_completion_path']))['files'])
    review=read(HERE/'audit_protocol/review.json')
    assert review['exporter_sha256']==sha(HERE/'retrieve.py') and review['ready_for_export'] is True
    specs=[REV+':'+p for r,p,n in TARGETS]
    raw=HERE/'raw';raw.mkdir(exist_ok=True)
    request=('\n'.join(specs)+'\n').encode('ascii')
    stdin=raw/'batch.stdin.bin';out=raw/'batch.stdout.bin';err=raw/'batch.stderr.bin'
    assert not any(p.exists() for p in [stdin,out,err])
    stdin.write_bytes(request)
    argv=['wsl','-d','Ubuntu','--','git','-C','/root/repos/linux','cat-file','--batch']
    p=subprocess.run(argv,input=request,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out.write_bytes(p.stdout);err.write_bytes(p.stderr)
    put('raw/batch.receipt.json',dict(argv=argv,returncode=p.returncode,stdin=str(stdin),stdin_sha256=sha(stdin),stdout=str(out),stdout_sha256=sha(out),stderr=str(err),stderr_sha256=sha(err)))
    if p.returncode:
        put('export_manifest.json',dict(status='batch_failed',git_commands=1,file_requests=2,observations=[]))
        raise SystemExit('batch failed, raw preserved; no retry')
    offset=0;observations=[]
    for (role,path,name),spec in zip(TARGETS,specs):
        end=p.stdout.index(b'\n',offset);header=p.stdout[offset:end];offset=end+1
        if header==(spec+' missing').encode('ascii'):
            observations.append(dict(role=role,source_path=path,revision=REV,status='missing',response_header=header.decode('ascii')))
            continue
        parts=header.split();assert len(parts)==3 and parts[1]==b'blob'
        oid=parts[0].decode('ascii');assert re.fullmatch('[0-9a-f]{40}',oid)
        size=int(parts[2]);assert size>=0
        content=p.stdout[offset:offset+size]
        assert len(content)==size and p.stdout[offset+size:offset+size+1]==b'\n';offset+=size+1
        assert hashlib.sha1(b'blob '+str(size).encode()+b'\0'+content).hexdigest()==oid
        dest=HERE/name;assert not dest.exists();dest.write_bytes(content)
        observations.append(dict(role=role,source_path=path,revision=REV,status='saved',saved_path=str(dest),byte_count=size,blob_sha1=oid,sha256=sha(dest),response_header=header.decode('ascii')))
    assert offset==len(p.stdout)
    manifest=dict(status='fixed_requests_complete',revision=REV,git_commands=1,file_requests=2,observations=observations,
        saved_files=sum(o['status']=='saved' for o in observations),missing_files=sum(o['status']=='missing' for o in observations),
        alternative_requests=0,actual_preprocessing_certified=False,new_confirmed_cases=0,independent_positive_cases=0)
    put('export_manifest.json',manifest)
    print(json.dumps({k:v for k,v in manifest.items() if k!='observations'}))

if __name__=='__main__':
    try:{'freeze':freeze,'export':export}[sys.argv[1]]()
    except Exception as e:
        put('failure_'+sys.argv[1]+'.json',dict(error_type=type(e).__name__,message=str(e),no_automatic_retry=True));raise
