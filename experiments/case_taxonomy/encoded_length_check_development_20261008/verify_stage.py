"""Read-only saved-run, provenance and quote checks; no detector import."""
from pathlib import Path
import hashlib,json,sys

HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def check(records):
    for r in records:assert sha(Path(r['path']))==r['sha256'],r['path']
def quotes(value):
    if isinstance(value,dict):
        if {'saved_path','text','start_line','end_line','sha256','revision'} <= value.keys():yield value
        for child in value.values():yield from quotes(child)
    elif isinstance(value,list):
        for child in value:yield from quotes(child)
def verify():
    check(load(HERE/'freeze_inputs_pre.json')['files'])
    inputs=load(HERE/'inputs_pre.json');fixtures=load(HERE/'probes_pre.json')['cases'];assert len(fixtures)==12
    raw_sources={};unique_actual_paths=set()
    for label in ['parent','fixed']:
        for meta in [inputs[label]['source'],*inputs[label]['declarations']]:
            p=Path(meta['saved_path']);raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==meta['sha256']
            assert len(raw)==meta['byte_count']
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==meta['blob_sha1']
            raw_sources[(str(p.resolve()),meta['revision'])]=raw;unique_actual_paths.add(str(p.resolve()))
            check(meta.get('proof_files',[]))
    reused=inputs['fixed']['declarations'][0]
    assert reused['retrieval_revision']==inputs['parent']['source']['revision']
    assert reused['effective_revision']==reused['revision']==inputs['fixed']['source']['revision']
    old=HERE.parent/'numeric_compare_transfer_20261008';contract=HERE.parent/'encoded_length_contract_20261008'
    old_parent=load(old/'parent_manifest.json')['observations'][0]
    assert (old/'prescreen/20314bacd2f9/parents.stdout.bin').read_text(encoding='utf-8').split()==[old_parent['revision']]
    changed=(old/'prescreen/20314bacd2f9/path_names.stdout.bin').read_text(encoding='utf-8').splitlines()
    assert changed==old_parent['changed_path_names'] and reused['source_path'] not in changed
    assert (contract/'raw/commit_body.stdout.bin').read_text(encoding='utf-8').splitlines()[:2]==[reused['revision'],reused['retrieval_revision']]
    for case in fixtures:
        for kind,key in [('main','source'),('header','declaration')]:
            raw_sources[('synthetic://'+case['id']+'/'+kind,case[key+'_revision'])]=case[key+'_text'].encode('utf-8')
    accepted=load(HERE/'accepted_phase.json');phase=accepted['phase']
    run_count=0;quote_count=0;unique_quotes=set();final=None
    for folder in sorted((HERE/'runs').iterdir()):
        if not folder.is_dir():continue
        freeze=load(folder/'freeze_code_pre.json');check(freeze['files'])
        assert sha(folder/'rule_snapshot.py')==freeze['execution_rule_sha256']
        receipt=load(folder/'receipt.json')
        assert receipt['rule_before_sha256']==receipt['rule_after_sha256']==sha(folder/'rule_snapshot.py')
        for kind in ['stdout','stderr']:assert sha(folder/(kind+'.bin'))==receipt[kind+'_sha256']
        result=load(folder/'results.json');assert sha(folder/'results.json')==receipt['results_sha256']
        assert result['counts']['fixed_synthetic_probes']==12 and result['counts']['revision_queries']==2
        assert {r['id'] for r in result['probes']}=={r['id'] for r in fixtures}
        assert result['counts']['probes_passed']==sum(r['passed'] for r in result['probes'])
        assert result['counts']['development_queries_passed']==sum(r['passed'] for r in result['development'])
        for q in quotes(result):
            path=q['saved_path'] if q['saved_path'].startswith('synthetic://') else str(Path(q['saved_path']).resolve())
            raw=raw_sources[(path,q['revision'])]
            assert hashlib.sha256(raw).hexdigest()==q['sha256']
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==q['blob_sha1']
            lines=raw.decode('utf-8').splitlines();assert '\n'.join(lines[q['start_line']-1:q['end_line']])==q['text']
            quote_count+=1;unique_quotes.add((path,q['revision'],q['start_line'],q['end_line'],q['text']))
        run_count+=1
        if folder.name==phase:
            assert receipt['returncode']==0 and result['counts']['failure_records']==0
            assert result['counts']['probes_passed']==12 and result['counts']['development_queries_passed']==2
            assert sha(folder/'results.json')==accepted['results_sha256']
            assert sha(HERE/'encoded_length_check.py')==sha(folder/'rule_snapshot.py')==accepted['rule_sha256']
            final=result
    assert final is not None
    for r in final['probes']:
        result=r.get('result');assert result['length_contract_certified'] is False and result['whole_function_certified'] is False
        for a in result.get('assignments',[]):assert a['length_contract_certified'] is False
    for r in final['development']:
        assert r['result']['length_contract_certified'] is False and r['result']['whole_function_certified'] is False
    pair={r['revision_label_outside_rule']:r for r in final['development']}
    assert [a['status'] for a in pair['parent']['result']['assignments']]==['candidate']
    assert [a['status'] for a in pair['fixed']['result']['assignments']]==['normal']
    result=dict(accepted_phase=phase,development_interfaces=1,revision_queries_per_run=2,synthetic_probes_per_run=12,
        saved_runs=run_count,accepted_probes_passed=12,accepted_revision_queries_passed=2,real_saved_source_files=len(unique_actual_paths),
        unchanged_header_effective_version_inferred=True,verified_quote_records=quote_count,unique_quotes=len(unique_quotes),
        whole_length_contract_certified=False,new_confirmed_cases=0,independent_positive_cases=0,project_model_calls=0,new_git_calls=0,
        detector_reexecution=False,hash_checks_not_semantic_truth=True)
    return result
if __name__=='__main__':
    result=verify();closed=HERE/'completion_manifest.json'
    if '--freeze' in sys.argv:
        assert not closed.exists()
        files=[dict(path=str(p),sha256=sha(p)) for p in sorted(HERE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
        closed.write_text(json.dumps(dict(files=files,counts=result),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    elif closed.exists():
        saved=load(closed);check(saved['files']);assert saved['counts']==result
    print(json.dumps(result,ensure_ascii=False))
