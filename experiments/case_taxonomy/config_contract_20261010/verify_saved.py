from pathlib import Path
import hashlib, json
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(name): return json.loads((BASE/name).read_text(encoding='utf-8'))
def verify_quotes(node,text):
    count=0
    if isinstance(node,dict):
        if 'text' in node and 'start_offset' in node and 'end_offset_exclusive' in node:
            assert text[node['start_offset']:node['end_offset_exclusive']]==node['text']
            count+=1
        elif 'text' in node and 'start_line' in node and 'end_line' in node:
            assert '\n'.join(text.splitlines()[node['start_line']-1:node['end_line']])==node['text']
            count+=1
        if 'line' in node and isinstance(node.get('quote'),str):
            assert text.splitlines()[node['line']-1]==node['quote']
            count+=1
        for value in node.values(): count+=verify_quotes(value,text)
    elif isinstance(node,list):
        for value in node: count+=verify_quotes(value,text)
    return count
freeze=load('freeze_pre.json')
for name,digest in freeze['files'].items(): assert sha(BASE/name)==digest
impl=load('implementation_pre.json')
for name,digest in impl['files'].items(): assert sha(BASE/name)==digest
retrieved=load('retrieval_manifest.json')
assert retrieved['source_requests']==8 and retrieved['git_commands']==4
assert retrieved['patch_requests']==retrieved['new_confirmed_cases']==retrieved['independent_positive_cases']==0
sources={s['path']:s for s in retrieved['sources']}
assert len(sources)==8
texts={}
for path,src in sources.items():
    raw=(BASE/src['saved']).read_bytes()
    assert src['status']=='available' and src['revision']==freeze['parent']
    assert len(raw)==src['bytes'] and sha(BASE/src['saved'])==src['sha256']
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==src['blob']
    texts[path]=raw.decode('utf-8')
receipts=load('raw/receipts.json')
assert len(receipts)==4
for r in receipts:
    for stream in ['stdout','stderr']:
        p=BASE/'raw'/(r['label']+'.'+stream+'.bin')
        assert sha(p)==r[stream+'_sha256']
    assert r['stdout_bytes']==(BASE/'raw'/(r['label']+'.stdout.bin')).stat().st_size
    assert r['stdout_bytes']<=2*1024*1024
assert [r['exit'] for r in receipts]==[0,0,0,1]
facts=load('facts.json'); probes=load('probe_results.json')
assert facts['parent']==freeze['parent'] and facts['scope']=='message_informed_development'
assert facts['new_confirmed_cases']==facts['independent_positive_cases']==facts['new_git_commands']==0
assert facts['repair_patch_read'] is False
assert len(facts['c']['references'])==len(facts['c']['supported_guards'])==len(facts['candidates'])==1
qcount=verify_quotes(facts['c'],texts[facts['c']['source']['path']])
for node in facts['kconfig']:
    qcount+=verify_quotes(node,texts[node['source']['path']])
for query in facts['queries']:
    lines=(BASE/'raw'/(query['label']+'.stdout.bin')).read_text(encoding='utf-8').splitlines()
    assert query['truncated'] is False and len(lines)==query['hit_count']==len(query['hits'])
    for hit,line in zip(query['hits'],lines):
        assert line==hit['revision']+':'+hit['path']+':'+str(hit['line'])+':'+hit['text']
        if hit['path'] in texts: assert texts[hit['path']].splitlines()[hit['line']-1]==hit['text']
assert [q['hit_count'] for q in facts['queries']]==[15,1,0]
assert facts['queries'][0]['query_complete_for_all_kconfig_syntax'] is False
for guard in facts['c']['supported_guards']:
    assert guard['cfg_certified'] is guard['preprocessor_value_certified'] is guard['actual_execution_certified'] is False
for candidate in facts['candidates']:
    assert candidate['verdict']=='needs_source_review' and candidate['automatic_replacement'] is None
    assert candidate['runtime_or_compile_error_certified'] is candidate['property_contract_certified'] is False
assert probes['count']==probes['passed']==8 and all(r['passed'] for r in probes['results'])
card=load('authority_card.json')
for quote in card['evidence'].values():
    src=sources[quote['source_path']]
    assert quote['revision']==src['revision'] and quote['blob']==src['blob'] and quote['source_sha256']==src['sha256']
    assert '\n'.join(texts[quote['source_path']].splitlines()[quote['line_start']-1:quote['line_end']])==quote['text']
assert card['new_confirmed_cases']==card['independent_positive_cases']==0
assert load('audit_authority/review.json')['verdict']=='pass_with_boundaries'
old=load('../mechanism_body_path_20261009/completion_manifest.json')
assert sha(BASE.parent/'mechanism_body_path_20261009/completion_manifest.json')==freeze['previous_completion_sha256']
cleanup=json.loads((ROOT/'日志/目录整理-2026-10-10.json').read_text(encoding='utf-8'))
for path,digest in cleanup['protected_experiment_files'].items(): assert sha(ROOT/path)==digest
for path,digest in cleanup['source_code'].items(): assert sha(ROOT/path)==digest
completion=BASE/'completion_manifest.json'
if completion.exists():
    sealed=load('completion_manifest.json')
    for name,digest in sealed['files'].items(): assert sha(BASE/name)==digest
print(json.dumps({'status':'OK','source_objects':8,'git_commands':4,'automatic_references':1,'supported_guards':1,'review_candidates':1,'saved_lexical_quotes':qcount,'synthetic_probes_passed':8,'old_experiment_files_unchanged':len(cleanup['protected_experiment_files']),'old_python_sources_unchanged':len(cleanup['source_code']),'new_confirmed_cases':0,'independent_positive_cases':0},ensure_ascii=False))
