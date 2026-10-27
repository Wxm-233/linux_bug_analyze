"""Lock already saved sources and one prior parent template; no new retrieval."""
from pathlib import Path
import hashlib,json

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def check(files):
    for f in files:assert sha(Path(f['path']))==f['sha256'],f['path']
def put(name,data):
    p=HERE/name;assert not p.exists()
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

previous=BASE/'encoded_length_templates_20261008'
closure=previous/'completion_manifest.json'
assert sha(closure)=='0969b6f45a3495242a3e092670ca32055bafc7a03373d2ffec542f2e69e532e1'
check(load(closure)['files'])
prior=BASE/'encoded_length_check_development_20261008'
source_inputs=load(prior/'inputs_pre.json')['parent']
sources=[source_inputs['source'],source_inputs['declarations'][0]]
for s in sources:assert sha(Path(s['saved_path']))==s['sha256']
card=BASE/'encoded_length_contract_20261008/parent_contract.json'
templates=previous/'runs/initial/results.json';rows=load(templates)['outputs']
n=next(i for i,r in enumerate(rows) if r['query_label_outside_generator']=='development:parent')
template=rows[n]['generated']['records'][0]
put('inputs_pre.json',dict(sources=sources,structure=template['observed_assignment']['field']['structure'],
    producer_function='nat25_db_handle',consumer_function='__nat25_add_pppoe_tag',
    prior_template_result_path=str(templates),prior_template_result_sha256=sha(templates),
    prior_template_pointer=f'/outputs/{n}/generated/records/0',prior_template=template,
    prior_parent_card_path=str(card),prior_parent_card_sha256=sha(card),
    previous_completion_path=str(closure),previous_completion_sha256=sha(closure),
    expected=dict(structure_fields=3,conditional_header_prefix=4,producer_encoded_length_writes=1,
        tail_array_copies=2,indirect_scalar_stores=1,selected_handoff_calls=1,selected_object_start_copies=1,
        capacity_guard_syntax_sites=1,unknown_symbols=['ETH_ALEN','old_tag_len'],all_conditions_proven=False),
    known_read_development=True,new_confirmed_cases=0,independent_positive_cases=0))
paths=[HERE/'protocol_pre.md',HERE/'prepare_inputs.py',HERE/'inputs_pre.json',templates,closure,card,
    prior/'inputs_pre.json',*[Path(s['saved_path']) for s in sources]]
put('freeze_inputs_pre.json',dict(files=[dict(path=str(p),sha256=sha(p)) for p in paths],
    purpose='one already-read parent composition source input; no detector replay or new retrieval'))
print(json.dumps(dict(input_freeze_sha256=sha(HERE/'freeze_inputs_pre.json'),saved_sources=2,
    interface_cases=1,new_source_queries=0),ensure_ascii=False))
