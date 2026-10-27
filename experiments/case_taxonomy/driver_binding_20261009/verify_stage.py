"""Read-only validation of fixed Git batch objects, receipts and citations."""
from pathlib import Path
import hashlib,json,sys

HERE=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def blob(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
def check(files):
    for f in files:assert sha(Path(f['path']))==f['sha256'],f['path']
def canonical(value):
    p=Path(value)
    if not p.is_absolute():p=HERE.parent/p
    return str(p.resolve())
def quotes(v):
    if isinstance(v,dict):
        if {'saved_path','start_line','end_line','text'}<=v.keys():
            yield dict(path=v['saved_path'],revision=v['revision'],sha256=v['sha256'],blob=v.get('blob_sha1',v.get('git_blob_sha1')),
                start=v['start_line'],end=v['end_line'],text=v['text'],kind=v.get('artifact_kind','source_quote'))
        elif {'saved_path','line_start','line_end','text'}<=v.keys():
            yield dict(path=v['saved_path'],revision=v['source_revision'],sha256=v['source_sha256'],blob=v['source_blob'],
                start=v['line_start'],end=v['line_end'],text=v['text'],kind='source_quote')
        else:
            for x in v.values():yield from quotes(x)
    elif isinstance(v,list):
        for x in v:yield from quotes(x)
def flags(v):
    if isinstance(v,dict):
        for k,x in v.items():
            if k.endswith('_certified') or k.endswith('_proven') or k=='proven':yield k,x
            yield from flags(x)
    elif isinstance(v,list):
        for x in v:yield from flags(x)

def verify():
    frozen=load(HERE/'freeze_inputs_pre.json');check(frozen['files']);inputs=load(HERE/'inputs_pre.json')
    check(load(Path(inputs['previous_completion_path']))['files'])
    review=load(HERE/'audit_protocol/review_code_pre.json')
    assert review['exporter_sha256']==sha(HERE/'prepare_export.py') and review['ready_for_export'] is True
    manifest=load(HERE/'export_manifest.json');assert manifest['status']=='fixed_requests_complete'
    assert manifest['file_requests']==3 and manifest['git_commands']==2 and manifest['alternative_requests']==0
    for label in ['revision_type','file_batch']:
        receipt=load(HERE/'raw'/f'{label}.receipt.json')
        assert receipt['returncode']==0
        for kind in ['stdout','stderr']:assert sha(Path(receipt[kind]))==receipt[kind+'_sha256']
        expected=['wsl','-d','Ubuntu','--','git','-C',inputs['repository'],'cat-file']
        expected+=['-t',inputs['revision']] if label=='revision_type' else ['--batch']
        assert receipt['argv']==expected
    assert (HERE/'raw/revision_type.stdout.bin').read_bytes().strip()==b'commit'
    receipt=load(HERE/'raw/file_batch.receipt.json');assert sha(Path(receipt['stdin']))==receipt['stdin_sha256']
    specs=[inputs['revision']+':'+t['source_path'] for t in inputs['targets']]
    assert Path(receipt['stdin']).read_bytes()==('\n'.join(specs)+'\n').encode('ascii')
    raw=Path(receipt['stdout']).read_bytes();offset=0;raw_sources={}
    old=inputs['old_source'];oldraw=Path(old['saved_path']).read_bytes()
    assert hashlib.sha256(oldraw).hexdigest()==old['sha256'] and blob(oldraw)==old['blob_sha1']
    raw_sources[(canonical(old['saved_path']),old['revision'])]=oldraw
    for target,observation,spec in zip(inputs['targets'],manifest['observations'],specs):
        assert observation['source_path']==target['source_path'] and observation['revision']==inputs['revision']
        end=raw.index(b'\n',offset);header=raw[offset:end];offset=end+1
        assert header.decode('ascii')==observation['response_header']
        if observation['status']=='missing':
            assert header==(spec+' missing').encode('ascii');continue
        oid,kind,size=header.split();assert kind==b'blob';size=int(size)
        content=raw[offset:offset+size];assert len(content)==size and raw[offset+size:offset+size+1]==b'\n';offset+=size+1
        assert oid.decode()==observation['blob_sha1']==blob(content)
        assert Path(observation['saved_path']).read_bytes()==content and sha(Path(observation['saved_path']))==observation['sha256']
        raw_sources[(canonical(observation['saved_path']),observation['revision'])]=content
    assert offset==len(raw) and len(manifest['observations'])==3
    card=load(HERE/'binding_card.json')
    assert card['revision']==inputs['revision'] and all(v is False for k,v in flags(card))
    assert len(card['conditions'])==12 and all(c['proven'] is False for c in card['conditions'])
    generated_manifest=(canonical(HERE/'export_manifest.json'),inputs['revision'])
    raw_sources[generated_manifest]=(HERE/'export_manifest.json').read_bytes()
    totals={};unique=set();generated_quote_count=0
    for label,data in [('root_card',card),('independent_semantics',load(HERE/'audit_semantics/review.json')),
                       ('independent_kbuild',load(HERE/'audit_kbuild/review.json'))]:
        count=0
        for q in quotes(data):
            path=canonical(q['path']);content=raw_sources[(path,q['revision'])]
            if (path,q['revision'])==generated_manifest:
                assert q['kind']=='generated_export_manifest';generated_quote_count+=1
            assert hashlib.sha256(content).hexdigest()==q['sha256'] and blob(content)==q['blob']
            lines=content.decode('utf-8').splitlines()
            assert 0<q['start']<=q['end']<=len(lines) and '\n'.join(lines[q['start']-1:q['end']])==q['text']
            count+=1;unique.add((path,q['revision'],q['start'],q['end'],q['text']))
        totals[label]=count
    assert manifest['new_confirmed_cases']==manifest['independent_positive_cases']==0
    return dict(fixed_file_requests=3,git_commands=2,saved_files=manifest['saved_files'],missing_files=manifest['missing_files'],
        quote_records_by_layer=totals,unique_quotes=len(unique),generated_manifest_quote_records=generated_quote_count,
        actual_include_binding_certified=False,actual_build_certified=False,
        new_confirmed_cases=0,independent_positive_cases=0,git_reexecution=False,old_rule_reexecution=False,
        compiler_or_kernel_runs=0,project_model_calls=0,hash_checks_not_semantic_truth=True)
if __name__=='__main__':
    counts=verify();closed=HERE/'completion_manifest.json'
    if '--freeze' in sys.argv:
        assert not closed.exists()
        files=[p for p in sorted(HERE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
        closed.write_text(json.dumps(dict(files=[dict(path=str(p),sha256=sha(p)) for p in files],counts=counts),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    elif closed.exists():
        previous=load(closed);check(previous['files']);assert previous['counts']==counts
    print(json.dumps(counts,ensure_ascii=False))
