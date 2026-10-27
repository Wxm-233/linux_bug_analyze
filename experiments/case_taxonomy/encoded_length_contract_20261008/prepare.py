"""Bounded same-revision declaration and post-card unseal; no detector execution."""
from pathlib import Path
import hashlib,json,re,subprocess,sys
from datetime import datetime,timezone

HERE=Path(__file__).resolve().parent;BASE=HERE.parent
OLD=BASE/'numeric_compare_transfer_20261008'
COMMIT='20314bacd2f9b1b8fc10895417e6db0dc85f8248'
PARENT='3123109284176b1532874591f7c81f3837bbdc17'
C_PATH='drivers/staging/r8188eu/core/rtw_br_ext.c'
HEADER='include/uapi/linux/if_pppox.h'
RULE=BASE/'numeric_compare_development_20261008/numeric_compare.py'
ATTEMPT_COMMANDS=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(n):return json.loads((HERE/n).read_text(encoding='utf-8'))
def save(n,v):
    p=HERE/n;assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def check(rs):
    for r in rs:assert sha(Path(r['path']))==r['sha256'],r['path']
def freeze():
    old=json.loads((OLD/'parent_manifest.json').read_text(encoding='utf-8'))['observations'][0]['sources'][0]
    assert old['revision']==PARENT and old['source_path']==C_PATH
    assert old['sha256']==sha(Path(old['saved_path']))=='0310bf04241d497049337252be03ce69746f47ad4f1c9713295c36d72e0233e6'
    assert sha(RULE)=='1ca111bf2d10014ceeebfbe8984e14d6ae586ff7160c40c6c2f27401e7b8bbb5'
    files=[HERE/'protocol_pre.md',HERE/'prepare.py',HERE/'projection.py',OLD/'completion_manifest.json',OLD/'parent_manifest.json',Path(old['saved_path']),RULE]
    save('freeze_declaration_pre.json',dict(time_utc=datetime.now(timezone.utc).isoformat(),
        target=dict(commit=COMMIT,parent=PARENT,c_path=C_PATH,header_path=HEADER),
        files=[dict(path=str(p),sha256=sha(p)) for p in files],new_header_exports=0,patch_exports=0))
    print(json.dumps(dict(freeze_sha256=sha(HERE/'freeze_declaration_pre.json'))))
def git(label,args,commands,missing=False):
    folder=HERE/'raw';folder.mkdir(exist_ok=True)
    out=folder/(label+'.stdout.bin');err=folder/(label+'.stderr.bin');assert not out.exists() and not err.exists()
    argv=['wsl','-d','Ubuntu','--','git','-C','/root/repos/linux',*args]
    p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE);out.write_bytes(p.stdout);err.write_bytes(p.stderr)
    receipt=dict(argv=argv,returncode=p.returncode,missing_allowed=missing,stdout=str(out),stderr=str(err),stdout_sha256=sha(out),stderr_sha256=sha(err))
    commands.append(receipt);ATTEMPT_COMMANDS.append(receipt)
    if p.returncode:
        if missing:return None
        raise RuntimeError(label+' failed')
    return p.stdout
def source(raw,revision,path,saved,blob):
    assert blob==hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    p=HERE/saved;assert not p.exists();p.write_bytes(raw)
    return dict(revision=revision,source_path=path,saved_path=str(p),blob_sha1=blob,sha256=sha(p),byte_count=len(raw))
def header():
    check(load('freeze_declaration_pre.json')['files']);commands=[]
    raw=git('parent_header',['show',PARENT+':'+HEADER],commands,True)
    if raw is None:
        save('header_commands.json',commands);save('header_manifest.json',dict(status='missing',attempts=1,source=None,patch_exports=0));return
    blob=git('parent_header_blob',['rev-parse',PARENT+':'+HEADER],commands).decode().strip()
    s=source(raw,PARENT,HEADER,'parent_if_pppox.h',blob)
    save('header_commands.json',commands);save('header_manifest.json',dict(status='saved',attempts=1,source=s,patch_exports=0))
    print(json.dumps(dict(header_attempts=1,header_sha256=s['sha256'],patch_exports=0)))
def lock_parent():
    check(load('freeze_declaration_pre.json')['files'])
    assert load('header_manifest.json')['status']=='saved'
    card=load('parent_contract.json');assert card['parent_revision']==PARENT and card['allow_selected_commit_unseal'] is True
    files=[HERE/n for n in ['protocol_pre.md','prepare.py','freeze_declaration_pre.json','header_manifest.json','header_commands.json','parent_if_pppox.h','parent_contract.json']]
    files.extend(sorted((HERE/'audit_parent_contract').glob('*')))
    files.extend(sorted((HERE/'audit_protocol').glob('*')))
    save('freeze_parent_contract_pre.json',dict(time_utc=datetime.now(timezone.utc).isoformat(),files=[dict(path=str(p),sha256=sha(p)) for p in files if p.is_file()],patch_exports_before_freeze=0))
    print(json.dumps(dict(parent_contract_lock_sha256=sha(HERE/'freeze_parent_contract_pre.json'))))
def unseal():
    check(load('freeze_declaration_pre.json')['files']);check(load('freeze_parent_contract_pre.json')['files']);commands=[]
    body=git('commit_body',['show','-s','--format=%H%n%P%n%aI%n%cI%n%B',COMMIT],commands)
    patch=git('selected_c_patch',['show','--format=','--no-ext-diff','--no-renames',COMMIT,'--',C_PATH],commands)
    fixed=git('fixed_c',['show',COMMIT+':'+C_PATH],commands)
    blob=git('fixed_blob',['rev-parse',COMMIT+':'+C_PATH],commands).decode().strip()
    s=source(fixed,COMMIT,C_PATH,'fixed_rtw_br_ext.c',blob)
    fixes=re.findall(r'^Fixes:\s*([0-9a-fA-F]{7,40})\b',body.decode('utf-8'),re.M)
    anchor=None
    if fixes:
        meta=git('first_fixes_metadata',['show','-s','--format=%H%n%P%n%aI%n%cI%n%s',fixes[0]],commands,True)
        anchor=dict(reference=fixes[0],metadata_saved=meta is not None)
    save('unseal_commands.json',commands)
    save('unseal_manifest.json',dict(commit=COMMIT,parent=PARENT,selected_c_path=C_PATH,fixed_source=s,patch_exports=1,fixes_anchor=anchor,header_exports=0))
    print(json.dumps(dict(patch_exports=1,fixed_c_files=1,fixes_metadata_attempts=int(bool(fixes)),rule_executions=0)))
if __name__=='__main__':
    try:{'freeze':freeze,'header':header,'lock_parent':lock_parent,'unseal':unseal}[sys.argv[1]]()
    except Exception as exc:
        save('failure_'+sys.argv[1]+'.json',dict(status='incomplete',operation=sys.argv[1],error_type=type(exc).__name__,message=str(exc),commands=ATTEMPT_COMMANDS))
        raise
