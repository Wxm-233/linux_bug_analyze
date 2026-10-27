"""Read-only byte/receipt/citation checks, without Git or C execution."""
from pathlib import Path
import hashlib,json

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def blob(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
def check(rows):
    for row in rows:assert sha(Path(row['path']))==row['sha256'],row['path']
def canonical(p):
    p=Path(p)
    return str((p if p.is_absolute() else BASE/p).resolve())
def quotes(v):
    if isinstance(v,dict):
        if {'saved_path','start_line','end_line','text','revision','sha256','blob_sha1'}<=v.keys():yield v
        else:
            for sub in v.values():yield from quotes(sub)
    elif isinstance(v,list):
        for sub in v:yield from quotes(sub)

def verify():
    check(load(HERE/'freeze_pre.json')['files'])
    inputs=load(HERE/'inputs_pre.json');rev=inputs['revision']
    check(load(Path(inputs['previous_completion_path']))['files'])
    protocol=load(HERE/'audit_protocol/review.json')
    assert protocol['ready_for_export'] is True and protocol['exporter_sha256']==sha(HERE/'retrieve.py')
    receipt=load(HERE/'raw/batch.receipt.json')
    assert receipt['argv']==['wsl','-d','Ubuntu','--','git','-C','/root/repos/linux','cat-file','--batch']
    assert receipt['returncode']==0
    for k in ['stdin','stdout','stderr']:assert sha(Path(receipt[k]))==receipt[k+'_sha256']
    specs=[rev+':'+t['source_path'] for t in inputs['targets']]
    assert Path(receipt['stdin']).read_bytes()==('\n'.join(specs)+'\n').encode('ascii')
    manifest=load(HERE/'export_manifest.json')
    assert manifest['status']=='fixed_requests_complete' and manifest['git_commands']==1 and manifest['file_requests']==2
    assert manifest['alternative_requests']==0 and len(manifest['observations'])==2
    content=Path(receipt['stdout']).read_bytes();offset=0;sources={}
    for t,o,spec in zip(inputs['targets'],manifest['observations'],specs):
        assert o['source_path']==t['source_path'] and o['revision']==rev
        end=content.index(b'\n',offset);header=content[offset:end];offset=end+1
        assert header.decode('ascii')==o['response_header']
        if o['status']=='missing':
            assert header==(spec+' missing').encode('ascii');continue
        oid,kind,size=header.split();assert kind==b'blob';size=int(size)
        raw=content[offset:offset+size]
        assert len(raw)==size and content[offset+size:offset+size+1]==b'\n';offset+=size+1
        assert raw==Path(o['saved_path']).read_bytes() and blob(raw)==oid.decode()==o['blob_sha1']
        assert hashlib.sha256(raw).hexdigest()==o['sha256']
        sources[canonical(o['saved_path'])]=raw
    assert offset==len(content)
    assert manifest['saved_files']==sum(o['status']=='saved' for o in manifest['observations'])
    assert manifest['missing_files']==sum(o['status']=='missing' for o in manifest['observations'])
    old=inputs['old_source'];oldraw=Path(old['saved_path']).read_bytes()
    assert sha(Path(old['saved_path']))==old['sha256'] and blob(oldraw)==old['blob_sha1']
    sources[canonical(old['saved_path'])]=oldraw
    provenance=load(BASE/'encoded_length_contract_20261008/header_manifest.json')['source']
    assert provenance['revision']==rev and provenance['source_path']=='include/uapi/linux/if_pppox.h'
    assert canonical(provenance['saved_path'])==canonical(inputs['uapi_source']['saved_path'])
    uapi=Path(provenance['saved_path']).read_bytes()
    assert blob(uapi)==provenance['blob_sha1'] and hashlib.sha256(uapi).hexdigest()==provenance['sha256']==inputs['uapi_source']['sha256']
    sources[canonical(provenance['saved_path'])]=uapi
    prior=load(BASE/'driver_binding_20261009/export_manifest.json')
    for o in prior['observations']:
        if o['status']=='saved':sources[canonical(o['saved_path'])]=Path(o['saved_path']).read_bytes()
    counts={};unique=set()
    for label,data in [('root',load(HERE/'route_card.json')),('independent',load(HERE/'audit_source/review.json'))]:
        n=0
        for q in quotes(data):
            raw=sources[canonical(q['saved_path'])]
            assert q['revision']==rev and hashlib.sha256(raw).hexdigest()==q['sha256'] and blob(raw)==q['blob_sha1']
            lines=raw.decode('utf-8').splitlines();start=q['start_line'];end=q['end_line']
            assert 0<start<=end<=len(lines) and '\n'.join(lines[start-1:end])==q['text']
            n+=1;unique.add((canonical(q['saved_path']),start,end,q['text']))
        assert n>0;counts[label]=n
    card=load(HERE/'route_card.json')
    assert card['actual_preprocessing_certified'] is False and card['actual_build_certified'] is False
    assert card['new_confirmed_cases']==card['independent_positive_cases']==0
    assert len(card['conditions'])==12 and all(c['proven'] is False for c in card['conditions'])
    review=load(HERE/'audit_source/review.json')
    assert review['review_passed'] is True
    return dict(git_commands=1,file_requests=2,saved_files=manifest['saved_files'],missing_files=manifest['missing_files'],
        source_quote_records=counts,unique_quotes=len(unique),actual_preprocessing_certified=False,actual_build_certified=False,
        new_confirmed_cases=0,independent_positive_cases=0,old_rule_reexecution=False,compiler_runs=0,project_model_calls=0)

if __name__=='__main__':
    counts=verify()
    closed=HERE/'completion_manifest.json'
    if closed.exists():
        previous=load(closed);check(previous['files']);assert previous['counts']==counts
    print(json.dumps(counts,ensure_ascii=False))
