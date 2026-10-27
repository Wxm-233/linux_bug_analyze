"""Verify saved evidence, raw citations and receipts without executing extraction."""
from pathlib import Path
import hashlib,json,sys

HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def source_path(value):
    p=Path(value)
    if not p.is_absolute():p=HERE.parent/p
    return str(p.resolve())
def check(files):
    for f in files:assert sha(Path(f['path']))==f['sha256'],f['path']
def quotes(value):
    if isinstance(value,dict):
        if {'saved_path','start_line','end_line','text'}<=value.keys():
            yield dict(path=value['saved_path'],revision=value['revision'],sha256=value['sha256'],
                blob=value.get('blob_sha1',value.get('git_blob_sha1')),start=value['start_line'],end=value['end_line'],text=value['text'])
        elif {'saved_path','line_start','line_end','text'}<=value.keys():
            yield dict(path=value['saved_path'],revision=value['source_revision'],sha256=value['source_sha256'],
                blob=value['source_blob'],start=value['line_start'],end=value['line_end'],text=value['text'])
        else:
            for child in value.values():yield from quotes(child)
    elif isinstance(value,list):
        for child in value:yield from quotes(child)
def flags(value):
    if isinstance(value,dict):
        for key,v in value.items():
            if key.endswith('_certified') or key.endswith('_proven') or key=='proven':yield key,v
            yield from flags(v)
    elif isinstance(value,list):
        for child in value:yield from flags(child)

def verify():
    check(load(HERE/'freeze_inputs_pre.json')['files']);inputs=load(HERE/'inputs_pre.json')
    check(load(Path(inputs['previous_completion_path']))['files'])
    raw_sources={}
    for source in inputs['sources']:
        raw=Path(source['saved_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==source['sha256']
        assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==source['blob_sha1']
        raw_sources[(source_path(source['saved_path']),source['revision'])]=raw
    accepted=load(HERE/'accepted_phase.json');folder=HERE/'runs'/accepted['phase']
    check(load(folder/'freeze_code_pre.json')['files']);receipt=load(folder/'receipt.json')
    assert receipt['returncode']==0 and receipt['old_detector_reexecuted'] is False and receipt['old_template_reexecuted'] is False
    assert receipt['extractor_before_sha256']==receipt['extractor_after_sha256']==sha(folder/'extractor_snapshot.py')==accepted['extractor_sha256']
    assert sha(HERE/'composition_extract.py')==accepted['extractor_sha256']
    for kind in ['stdout','stderr']:assert sha(folder/(kind+'.bin'))==receipt[kind+'_sha256']
    assert sha(folder/'results.json')==receipt['results_sha256']==accepted['results_sha256']
    result=load(folder/'results.json');assert result['counts']==json.loads((folder/'stdout.bin').read_bytes())
    assert result['passed'] and all(result['tests'].values()) and result['counts']['failure_records']==0
    e=result['evidence'];facts=e['machine_facts'];p=facts['producer'];model=e['conditional_composition']
    assert len(facts['layout']['fields'])==3 and facts['layout']['conditional_prefix_model']==4
    assert [f['type'] for f in facts['layout']['fields']]==['__be16','__be16','char[0]']
    assert model['payload_model']==dict(constant=2,symbols={'ETH_ALEN':1,'old_tag_len':1})
    assert model['total_object_model']==dict(constant=6,symbols={'ETH_ALEN':1,'old_tag_len':1})
    assert model['unknown_symbols']==['ETH_ALEN','old_tag_len']
    assert p['scalar_store']['width_C_bytes']=='sizeof(unsigned short)'
    assert p['capacity_guard']['inside_old_object_block'] is True and p['capacity_guard']['all_paths_certified'] is False
    assert len(p['tail_array_copies'])==2 and p['symbolic_adjacency']==[1,0]
    assert p['tail_array_copies'][1]['end_model']==p['tail_array_copies'][0]['begin_model']
    assert p['tail_array_copies'][0]['end_model']==model['payload_model']
    assert len(e['condition_evidence_card'])==12 and all(c['proven'] is False for c in e['condition_evidence_card'])
    supported=[c['name'] for c in e['condition_evidence_card'] if c['evidence_level']=='source_supported_under_assumptions_not_certified']
    assert supported==['field_semantic_unit','explicit_component_meaning','complete_length_formula']
    assert all(v is False for key,v in flags(e))
    assert e['new_confirmed_cases']==e['independent_positive_cases']==0
    prior=inputs['prior_template'];rows=load(Path(inputs['prior_template_result_path']))['outputs']
    index=int(inputs['prior_template_pointer'].split('/')[2])
    assert rows[index]['generated']['records'][0]==prior
    assert [c['name'] for c in e['condition_evidence_card']]==[c['name'] for c in prior['applicability_conditions']]
    collections=[('machine',e),('semantic_pre',load(HERE/'audit_semantics/review.json')),('layout_pre',load(HERE/'audit_layout/review.json'))]
    quote_counts={};unique=set()
    for label,data in collections:
        count=0
        for q in quotes(data):
            canonical_path=source_path(q['path'])
            raw=raw_sources[(canonical_path,q['revision'])]
            assert hashlib.sha256(raw).hexdigest()==q['sha256']
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==q['blob']
            lines=raw.decode('utf-8').splitlines()
            assert 0<q['start']<=q['end']<=len(lines)
            assert '\n'.join(lines[q['start']-1:q['end']])==q['text']
            count+=1;unique.add((canonical_path,q['revision'],q['start'],q['end'],q['text']))
        quote_counts[label]=count
    for rel in ['audit_semantics/review_result.json','audit_layout/review_result.json']:
        review=load(HERE/rel)
        # Binding is checked by exact result digest appearing in the saved review.
        assert accepted['results_sha256'] in json.dumps(review,ensure_ascii=False)
    return dict(interface_cases=1,saved_sources=2,evidence_queries_executed=1,accepted_queries_passed=1,
        root_acceptance_checks=len(result['tests']),failure_records=0,
        source_supported_condition_records=3,conditions_all_unproven=12,
        quote_records_by_layer=quote_counts,unique_quotes=len(unique),new_confirmed_cases=0,independent_positive_cases=0,
        actual_layout_certified=False,complete_length_contract_certified=False,extractor_reexecution=False,
        old_detector_reexecution=False,old_template_reexecution=False,new_source_queries=0,project_model_calls=0,
        kernel_or_compiler_runs=0,hash_checks_not_semantic_truth=True)

if __name__=='__main__':
    counts=verify();closed=HERE/'completion_manifest.json'
    if '--freeze' in sys.argv:
        assert not closed.exists()
        files=[p for p in sorted(HERE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
        closed.write_text(json.dumps(dict(files=[dict(path=str(p),sha256=sha(p)) for p in files],counts=counts),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    elif closed.exists():
        manifest=load(closed);check(manifest['files']);assert manifest['counts']==counts
    print(json.dumps(counts,ensure_ascii=False))
