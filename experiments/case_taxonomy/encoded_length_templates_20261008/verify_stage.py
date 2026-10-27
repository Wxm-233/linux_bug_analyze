"""Read-only source, evidence, condition and receipt verification; no generators."""
from pathlib import Path
import hashlib,json,sys

HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def check(files):
    for f in files:assert sha(Path(f['path']))==f['sha256'],f['path']
def quotes(value):
    if isinstance(value,dict):
        if {'saved_path','revision','sha256','blob_sha1','start_line','end_line','text'}<=value.keys():yield value
        else:
            for child in value.values():yield from quotes(child)
    elif isinstance(value,list):
        for child in value:yield from quotes(child)
def flags(value):
    if isinstance(value,dict):
        for k,v in value.items():
            if k.endswith('_certified') or k.endswith('_proven') or k in ('certified','proven'):yield k,v
            yield from flags(v)
    elif isinstance(value,list):
        for child in value:yield from flags(child)
def quote_key(q):return json.dumps(q,ensure_ascii=False,sort_keys=True)

def verify():
    frozen=load(HERE/'freeze_inputs_pre.json');check(frozen['files'])
    inputs=load(HERE/'inputs_pre.json')
    previous=Path(inputs['previous_completion_path']).parent
    check(load(Path(inputs['previous_completion_path']))['files'])
    inherited=load(previous/'inputs_pre.json')
    raw_sources={};actual_paths=set()
    for label in ['parent','fixed']:
        for s in [inherited[label]['source']]+inherited[label]['declarations']:
            raw=Path(s['saved_path']).read_bytes()
            assert hashlib.sha256(raw).hexdigest()==s['sha256']
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==s['blob_sha1']
            raw_sources[(s['saved_path'],s['revision'])]=raw;actual_paths.add(s['saved_path'])
            if s.get('proof_files'):
                check(s['proof_files']);assert s['retrieval_revision']!=s['effective_revision']==s['revision']
    fixtures=load(previous/'probes_pre.json')['cases']
    for c in fixtures:
        raw_sources[(f"synthetic://{c['id']}/main",c['source_revision'])]=c['source_text'].encode('utf-8')
        raw_sources[(f"synthetic://{c['id']}/header",c['declaration_revision'])]=c['declaration_text'].encode('utf-8')
    old=load(Path(inputs['saved_result_path']))
    upstream_quotes={quote_key(q) for q in quotes(old)}
    accepted=load(HERE/'accepted_phase.json');folder=HERE/'runs'/accepted['phase']
    check(load(folder/'freeze_code_pre.json')['files'])
    receipt=load(folder/'receipt.json')
    assert receipt['returncode']==0 and receipt['old_detector_reexecuted'] is False
    assert receipt['generator_before_sha256']==receipt['generator_after_sha256']==sha(folder/'generator_snapshot.py')==accepted['generator_sha256']
    assert sha(HERE/'template_generator.py')==accepted['generator_sha256']
    for name in ['stdout','stderr']:assert sha(folder/(name+'.bin'))==receipt[name+'_sha256']
    assert sha(folder/'results.json')==receipt['results_sha256']==accepted['results_sha256']
    result=load(folder/'results.json')
    assert result['counts']==load_json_bytes(folder/'stdout.bin')
    assert not result['failures'] and len(result['outputs'])==14
    templates=0;refused=0;qcount=0;qset=set();unproven=0;candidate=0;normal=0
    for entry,row in zip(result['outputs'],inputs['queries']):
        assert entry['query_label_outside_generator']==row['query_label_outside_generator']
        assert entry['input_json_pointer']==row['json_pointer'] and entry['saved_result_sha256']==inputs['saved_result_sha256']
        assert entry['passed'] and all(entry['tests'].values())
        original=old[row['group']][row['index']]['result'];g=entry['generated']
        assert g['disposition']==row['expected_query_disposition']
        assert len(g['records'])==len(original['assignments'])
        assert all(v is False for k,v in flags(g))
        for output_record,assignment in zip(g['records'],original['assignments']):
            assert output_record['upstream_representation_status']==assignment['status']
            if output_record['disposition']=='refused':
                refused+=1;assert assignment['status']=='insufficient';continue
            assert output_record['disposition']=='conditional_template'
            templates+=1;candidate+=assignment['status']=='candidate';normal+=assignment['status']=='normal'
            relation=output_record['relation'];rhs=relation['rhs'];field=assignment['source_field']
            assert relation['semantic_domain']=='mathematical_reference_not_C_expression'
            assert relation['truth_at_runtime']=='unknown' and relation['normative_complete_length_formula'] is False
            assert relation['lhs']['declared_c_type']==assignment['local_declaration']['type']
            assert rhs['domain']=='unbounded_nonnegative_integers'
            assert rhs['base']['snapshot_time']=='original_assignment'
            assert rhs['base']['field_reference']==field['object']+'->'+field['field']
            assert rhs['base']['byte_order']==field['domain'] and rhs['base']['width_bits']==field['width']
            assert rhs['base']['type_bound_only']==[0,(1<<field['width'])-1]
            assert [t['value'] for t in rhs['terms']]==[c['value'] for c in assignment['length_components']]
            assert all(t['semantic_unit']=='unknown' and t['semantic_role']=='unknown' and t['required_by_complete_contract'] is False for t in rhs['terms'])
            assert output_record['consumer_evidence']==assignment['consumers']
            assert output_record['first_lexical_consumer']==assignment['first_lexical_consumer']
            assert output_record['observed_assignment']['rhs']==assignment['rhs']
            assert output_record['observed_assignment']['field']==field
            assert len(output_record['applicability_conditions'])==12
            assert len({c['name'] for c in output_record['applicability_conditions']})==12
            assert all(c['proven'] is False for c in output_record['applicability_conditions']);unproven+=12
            assert output_record['unresolved']['complete_length_contract']=='unproved'
            assert output_record['unresolved']['missing_addends_inferred'] is False
        for q in quotes(g):
            assert quote_key(q) in upstream_quotes
            raw=raw_sources[(q['saved_path'],q['revision'])]
            assert hashlib.sha256(raw).hexdigest()==q['sha256']
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==q['blob_sha1']
            lines=raw.decode('utf-8').splitlines()
            assert '\n'.join(lines[q['start_line']-1:q['end_line']])==q['text']
            qcount+=1;qset.add(quote_key(q))
    nohead=next(o for o in result['outputs'] if o['query_label_outside_generator']=='probes:matching_decode_without_header')
    assert nohead['generated']['records'][0]['relation']['rhs']['terms']==[]
    multi=next(o for o in result['outputs'] if o['query_label_outside_generator']=='probes:local_multiple_assignments')
    assert len(multi['generated']['records'])==2 and all(a['disposition']=='refused' for a in multi['generated']['records'])
    assert templates==6 and refused==7 and candidate==normal==3 and unproven==72
    assert result['counts']['queries_passed']==14 and result['counts']['failure_records']==0
    assert result['counts']['old_detector_reexecutions']==0 and result['counts']['project_model_calls']==0
    return dict(saved_queries=14,queries_passed=14,generated_templates=6,
        upstream_candidate_templates=3,upstream_local_normal_templates=3,
        refused_assignment_records=7,insufficient_queries=1,no_eligible_assignment_queries=1,
        template_conditions_all_unproven=72,verified_quote_records=qcount,unique_quotes=len(qset),
        real_saved_source_files=len(actual_paths),old_detector_reexecution=False,generator_reexecution=False,
        new_confirmed_cases=0,independent_positive_cases=0,complete_length_contract_certified=False,
        reviewer_is_implementer=True,hash_checks_not_semantic_truth=True)

def load_json_bytes(p):return json.loads(p.read_bytes())

if __name__=='__main__':
    counts=verify();closed=HERE/'completion_manifest.json'
    if '--freeze' in sys.argv:
        assert not closed.exists()
        paths=[p for p in sorted(HERE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
        closed.write_text(json.dumps(dict(files=[dict(path=str(p),sha256=sha(p)) for p in paths],counts=counts),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    elif closed.exists():
        manifest=load(closed);check(manifest['files']);assert manifest['counts']==counts
    print(json.dumps(counts,ensure_ascii=False))
