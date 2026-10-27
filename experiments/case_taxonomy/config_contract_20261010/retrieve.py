from pathlib import Path
import hashlib, json, subprocess
BASE = Path(__file__).resolve().parent
PARENT = '7ff730ca458e841dbcdc87f264d7afe3eaed525e'
REPO = '/root/repos/linux'
FILES = ['drivers/i3c/master/mipi-i3c-hci/core.c','Kconfig','arch/Kconfig','arch/arm/Kconfig','arch/arm64/Kconfig','drivers/i3c/Kconfig','drivers/i3c/master/Kconfig','drivers/i3c/master/mipi-i3c-hci/Makefile']
LIMIT = 2 * 1024 * 1024
sha = lambda raw: hashlib.sha256(raw).hexdigest()
rawdir = BASE/'raw'
assert not rawdir.exists(), 'Retrieval already exists; do not repeat'
rawdir.mkdir()
freeze = json.loads((BASE/'freeze_pre.json').read_text(encoding='utf-8'))
for name,digest in freeze['files'].items():
    assert sha((BASE/name).read_bytes()) == digest
receipts=[]
def run(label,args,stdin=b''):
    p=subprocess.run(['git','-C',REPO,*args],input=stdin,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    (rawdir/(label+'.stdout.bin')).write_bytes(p.stdout)
    (rawdir/(label+'.stderr.bin')).write_bytes(p.stderr)
    receipts.append({'label':label,'argv':['git','-C',REPO,*args],'exit':p.returncode,'stdout_bytes':len(p.stdout),'stdout_sha256':sha(p.stdout),'stderr_sha256':sha(p.stderr),'stdin_sha256':sha(stdin)})
    (rawdir/'receipts.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assert len(p.stdout)<=LIMIT and len(p.stderr)<=LIMIT, 'Output exceeded protocol bound; stop'
    return p
request=''.join(PARENT+':'+name+'\n' for name in FILES).encode()
(rawdir/'batch.request.txt').write_bytes(request)
p=run('01_objects',['cat-file','--batch'],request)
assert p.returncode==0
pos=0; sources=[]
for i,name in enumerate(FILES,1):
    end=p.stdout.index(b'\n',pos); header=p.stdout[pos:end]; pos=end+1
    if header.endswith(b' missing'):
        sources.append({'path':name,'status':'missing','query':PARENT+':'+name}); continue
    oid,kind,size=header.split(); size=int(size)
    assert kind==b'blob'
    raw=p.stdout[pos:pos+size]; pos+=size
    assert len(raw)==size and p.stdout[pos:pos+1]==b'\n'; pos+=1
    computed=hashlib.sha1(b'blob '+str(size).encode()+b'\0'+raw).hexdigest()
    assert computed==oid.decode()
    target=rawdir/(f'{i:02}_'+name.replace('/','__'))
    target.write_bytes(raw)
    sources.append({'path':name,'revision':PARENT,'status':'available','saved':target.relative_to(BASE).as_posix(),'blob':computed,'sha256':sha(raw),'bytes':size})
assert pos==len(p.stdout)
queries=[
('02_kconfig_declarations',['grep','-n','-E',r'^(menu)?config[[:space:]]+(BIG_ENDIAN|CPU_BIG_ENDIAN)([[:space:]]|$)',PARENT,'--','Kconfig',':(glob)**/Kconfig*']),
('03_original_references',['grep','-n','-F','CONFIG_BIG_ENDIAN',PARENT,'--']),
('04_direct_macro_definitions',['grep','-n','-E',r'^[[:space:]]*#[[:space:]]*define[[:space:]]+CONFIG_(BIG_ENDIAN|CPU_BIG_ENDIAN)([[:space:]]|$)',PARENT,'--'])]
for label,args in queries:
    p=run(label,args)
    assert p.returncode in (0,1), 'Git retrieval error'
result={'parent':PARENT,'target':'drivers/i3c/master/mipi-i3c-hci/core.c','source_requests':len(FILES),'git_commands':len(receipts),'sources':sources,'receipts':'raw/receipts.json','scope':'message_informed_development','patch_requests':0,'new_confirmed_cases':0,'independent_positive_cases':0}
(BASE/'retrieval_manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'source_requests':len(FILES),'available':sum(s['status']=='available' for s in sources),'git_commands':len(receipts)},ensure_ascii=False))
