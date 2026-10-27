"""Freeze a bounded queue; export parent files only, with every attempt counted."""
from pathlib import Path,PurePosixPath
import hashlib
import json
import posixpath
import re
import subprocess
import sys
from datetime import datetime,timezone

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
RULE=BASE/'numeric_compare_development_20261008/numeric_compare.py'
DEPS=[RULE,BASE/'interface_facts_20261008/interface_fact_extractor.py',BASE/'endian_consumer_single_revision.py',BASE/'numeric_compare_development_20261008/completion_manifest.json']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(name):return json.loads((HERE/name).read_text(encoding='utf-8'))
def save(name,value):
    p=HERE/name;assert not p.exists(),str(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def check(records):
    for r in records:assert sha(Path(r['path']))==r['sha256'],r['path']

def freeze():
    pool=read('metadata_pool.json');assert len(pool['records'])==16
    audit=read('audit_metadata/exposure_audit.json')
    assert audit['pool_count']==16 and audit['metadata_pool_sha256']==sha(HERE/'metadata_pool.json')
    excluded={r['commit'] for r in audit['confirmed_prior_source_exposure']}
    queue=[r for r in pool['records'] if r['commit'] not in excluded and
           re.search(r'endian|byte[ -]?order|(?:le|be)(?:16|32|64)|convert|conversion',r['subject'],re.I)][:2]
    save('queue_pre.json',dict(queue=queue,pool_count=16,source_exposed_commits=sorted(excluded)))
    files=[HERE/n for n in ['protocol_pre.md','metadata_pool.py','metadata_pool.json','prepare.py','audit_metadata/exposure_audit.json','audit_metadata/audit_exposure.py','audit_metadata/review.md','queue_pre.json']]
    files += [Path(pool['source']),*DEPS]
    save('freeze_metadata_pre.json',dict(time_utc=datetime.now(timezone.utc).isoformat(),
         files=[dict(path=str(p),sha256=sha(p)) for p in files],source_exports_before_freeze=0,rule_executions_before_freeze=0,patch_exports_before_freeze=0))
    print(json.dumps(dict(pool_count=16,queue=[r['commit'] for r in queue],freeze_sha256=sha(HERE/'freeze_metadata_pre.json'))))

def git(folder,label,args,commands,allow_missing=False):
    argv=['wsl','-d','Ubuntu','--','git','-C','/root/repos/linux',*args]
    p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out=folder/(label+'.stdout.bin');err=folder/(label+'.stderr.bin');out.write_bytes(p.stdout);err.write_bytes(p.stderr)
    commands.append(dict(argv=argv,returncode=p.returncode,missing_allowed=allow_missing,
                         stdout=str(out),stderr=str(err),stdout_sha256=sha(out),stderr_sha256=sha(err)))
    if p.returncode:
        if allow_missing:return None
        raise RuntimeError('git command failed: '+label)
    return p.stdout

def export():
    check(read('freeze_metadata_pre.json')['files']);commands=[];observations=[]
    assert not (HERE/'parent_manifest.json').exists()
    try:
        for item in read('queue_pre.json')['queue']:
            folder=HERE/'prescreen'/item['commit'][:12];folder.mkdir(parents=True,exist_ok=False)
            row=dict(item);row.update(sources=[],export_status='started',source_exposure='current_parent_prescreen')
            observations.append(row)  # Even a no-C/missing-parent attempt consumes the queue slot.
            parents=git(folder,'parents',['show','-s','--format=%P',item['commit']],commands).decode().split()
            if len(parents)!=1:row['export_status']='not_single_parent';continue
            row['revision']=parents[0]
            paths=git(folder,'path_names',['diff-tree','--no-commit-id','--name-only','-r',item['commit']],commands).decode().splitlines()
            row['changed_path_names']=paths;cs=sorted(p for p in paths if p.endswith('.c'))
            if not cs:row['export_status']='no_changed_c_file';continue
            path=cs[0];row['selected_c_path']=path
            raw=git(folder,'parent_c',['show',parents[0]+':'+path],commands,True)
            if raw is None:row['export_status']='parent_c_missing';continue
            headers=re.findall(rb'^\s*#\s*include\s*"([^"\n]+)"',raw,re.M)[:2]
            names=[path]+[posixpath.normpath(str(PurePosixPath(path).parent/x.decode())) for x in headers]
            for i,name in enumerate(names):
                content=raw if i==0 else git(folder,'header_'+str(i),['show',parents[0]+':'+name],commands,True)
                if content is None:row.setdefault('missing_headers',[]).append(name);continue
                blob=git(folder,'blob_'+str(i),['rev-parse',parents[0]+':'+name],commands).decode().strip()
                assert blob==hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()
                saved=folder/('source_'+str(i)+PurePosixPath(name).suffix);saved.write_bytes(content)
                row['sources'].append(dict(revision=parents[0],source_path=name,saved_path=str(saved),blob_sha1=blob,sha256=sha(saved),byte_count=len(content)))
            row['export_status']='ok'
    finally:
        save('parent_commands.json',commands)
        save('parent_manifest.json',dict(parent_support_attempts=len(observations),observations=observations,rule_executions=0,patch_exports=0))
    print(json.dumps(dict(parent_support_attempts=len(observations),sources=sum(len(r['sources']) for r in observations),rule_executions=0,patch_exports=0)))

if __name__=='__main__':{'freeze':freeze,'export':export}[sys.argv[1]]()
