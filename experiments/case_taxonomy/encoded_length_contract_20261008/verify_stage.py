"""Read-only artifact/quote/arithmetic verification; never import the detector."""
from pathlib import Path
import hashlib,json,re,sys

HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(n):return json.loads((HERE/n).read_text(encoding='utf-8'))
def records(rs):
    for r in rs:assert sha(Path(r['path']))==r['sha256'],r['path']
def verify():
    first=load('freeze_declaration_pre.json');records(first['files'])
    second=load('freeze_parent_contract_pre.json');records(second['files'])
    assert first['new_header_exports']==first['patch_exports']==second['patch_exports_before_freeze']==0
    target=first['target'];old=HERE.parent/'numeric_compare_transfer_20261008'
    parent=json.loads((old/'parent_manifest.json').read_text(encoding='utf-8'))['observations'][0]['sources'][0]
    header=load('header_manifest.json');assert header['attempts']==1 and header['status']=='saved'
    unseal=load('unseal_manifest.json');assert unseal['patch_exports']==1 and unseal['header_exports']==0
    sources=[parent,header['source'],unseal['fixed_source']]
    for source in sources:
        raw=Path(source['saved_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==source['sha256']
        assert len(raw)==source['byte_count']
        assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==source['blob_sha1']
    commands=load('header_commands.json')+load('unseal_commands.json')
    wanted=[['show',target['parent']+':'+target['header_path']],['rev-parse',target['parent']+':'+target['header_path']],
        ['show','-s','--format=%H%n%P%n%aI%n%cI%n%B',target['commit']],
        ['show','--format=','--no-ext-diff','--no-renames',target['commit'],'--',target['c_path']],
        ['show',target['commit']+':'+target['c_path']],['rev-parse',target['commit']+':'+target['c_path']]]
    if unseal['fixes_anchor']:
        wanted.append(['show','-s','--format=%H%n%P%n%aI%n%cI%n%s',unseal['fixes_anchor']['reference']])
    assert [c['argv'][7:] for c in commands]==wanted
    for c in commands:
        assert c['argv'][:7]==['wsl','-d','Ubuntu','--','git','-C','/root/repos/linux']
        assert c['returncode']==0 or c['missing_allowed']
        for kind in ['stdout','stderr']:assert sha(Path(c[kind]))==c[kind+'_sha256']
    card=load('parent_contract.json');assert card['parent_revision']==target['parent'] and card['allow_selected_commit_unseal']
    quotes=[];metadata_quotes=[]
    for p in sorted(HERE.rglob('*.json')):
        if p.name=='completion_manifest.json':continue
        value=json.loads(p.read_text(encoding='utf-8'))
        if isinstance(value,dict):
            quotes.extend(value.get('source_quotes',[]));metadata_quotes.extend(value.get('metadata_quotes',[]))
    permitted={Path(s['saved_path']).resolve():s for s in sources}
    for quote in quotes:
        path=Path(quote['saved_path']).resolve();assert path in permitted
        assert path.read_text(encoding='utf-8').splitlines()[quote['line']-1]==quote['text']
    permitted_metadata={Path(c['stdout']).resolve() for c in commands if c['argv'][7:9]==['show','-s']}
    for quote in metadata_quotes:
        path=Path(quote['saved_path']).resolve();assert path in permitted_metadata
        assert path.read_text(encoding='utf-8').splitlines()[quote['line']-1]==quote['text']
    projection=load('projection_results.json');assert projection['lengths_prelocked']==[0,1,8,255,256,257,0x1234,0xffff]
    rows=projection['cases'];assert len(rows)==16
    expected_pairs={(order,n) for order in ['little','big'] for n in projection['lengths_prelocked']}
    assert {(r['host_order'],r['length_input']) for r in rows}==expected_pairs
    observed={o:{v:0 for v in ['raw_plus_header','decode_plus_header','decode_without_header']} for o in ['little','big']}
    for r in rows:
        n=r['length_input'];raw=((n&255)<<8)|(n>>8) if r['host_order']=='little' else n
        assert r['raw_host_read']==raw and r['expected_byte_count']==n+4
        assert r['encoded_storage_hex']==f'{n:04x}'
        assert r['variants']==dict(raw_plus_header=raw+4,decode_plus_header=n+4,decode_without_header=n)
        for variant,value in r['variants'].items():
            assert r['mismatches'][variant]==(value!=n+4)
            observed[r['host_order']][variant]+=int(value!=n+4)
    assert observed==projection['mismatch_counts']
    receipt=load('projection_receipt.json');assert receipt['returncode']==0
    for kind in ['stdout','stderr']:assert sha(HERE/('projection.'+kind+'.bin'))==receipt[kind+'_sha256']
    assert receipt['projection_sha256']==sha(HERE/'projection.py')
    post=load('post_review.json');assert post['corresponds_to_locked_parent_target'] is True
    assert post['new_confirmed_cases']==post['independent_positive_cases']==0
    oldlines=Path(parent['saved_path']).read_text(encoding='utf-8').splitlines()
    fixedlines=Path(unseal['fixed_source']['saved_path']).read_text(encoding='utf-8').splitlines()
    assert len(oldlines)==len(fixedlines)
    assert [i+1 for i,(a,b) in enumerate(zip(oldlines,fixedlines)) if a!=b]==post['changed_physical_lines']==[73]
    assert oldlines[72]=='\tdata_len = tag->tag_len + TAG_HDR_LEN;'
    assert fixedlines[72]=='\tdata_len = be16_to_cpu(tag->tag_len) + TAG_HDR_LEN;'
    body=(HERE/'raw/commit_body.stdout.bin').read_text(encoding='utf-8').splitlines()
    assert body[0]==target['commit'] and body[1]==target['parent']
    dimensions=post['teacher_dimensions']
    assert dimensions['fix_author_date']==body[2] and dimensions['fix_commit_date']==body[3]
    if unseal['fixes_anchor'] and unseal['fixes_anchor']['metadata_saved']:
        from datetime import datetime,timezone
        anchor=(HERE/'raw/first_fixes_metadata.stdout.bin').read_text(encoding='utf-8').splitlines()
        assert dimensions['introduction']['fixes_anchor_sha']==anchor[0]
        dates=[datetime.fromisoformat(s).astimezone(timezone.utc).date() for s in [anchor[3],body[3]]]
        assert dimensions['fixes_to_fix_commit_utc_calendar_days']==(dates[1]-dates[0]).days
    assert dimensions['discovery_date'] is None
    assert dimensions['introduction_to_discovery_days'] is None and dimensions['discovery_to_fix_days'] is None
    result=dict(source_files=3,new_parent_declaration_files=1,new_fixed_c_files=1,
        git_commands=len(commands),source_quote_records=len(quotes),
        unique_source_quotes=len({(str(Path(q['saved_path']).resolve()),q['line'],q['text']) for q in quotes}),
        metadata_quote_records=len(metadata_quotes),
        projection_runs=1,synthetic_value_host_pairs=16,mismatch_counts=observed,
        detector_runs=0,new_confirmed_cases=0,independent_positive_cases=0,project_model_calls=0,
        bytes_and_arithmetic_not_runtime_proof=True)
    return result
if __name__=='__main__':
    result=verify();p=HERE/'completion_manifest.json'
    if '--freeze' in sys.argv:
        assert not p.exists()
        files=[dict(path=str(f),sha256=sha(f)) for f in sorted(HERE.rglob('*')) if f.is_file() and '__pycache__' not in f.parts]
        p.write_text(json.dumps(dict(files=files,counts=result),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    elif p.exists():
        closed=load('completion_manifest.json');records(closed['files']);assert closed['counts']==result
    print(json.dumps(result,ensure_ascii=False))
