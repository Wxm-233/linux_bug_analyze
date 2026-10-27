"""Freeze existing parent source, declarations, card and template; no detector."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
PREV=BASE/'encoded_length_templates_20261008'
OLD=BASE/'encoded_length_check_development_20261008'
CARD=BASE/'encoded_length_contract_20261008/parent_contract.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def put(name,data):
    p=HERE/name;assert not p.exists()
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
closed=PREV/'completion_manifest.json'
assert sha(closed)=='0969b6f45a3495242a3e092670ca32055bafc7a03373d2ffec542f2e69e532e1'
for item in load(closed)['files']:assert sha(Path(item['path']))==item['sha256']
oldinputs=load(OLD/'inputs_pre.json');parent=oldinputs['parent']
sources=[parent['source']]+parent['declarations']
assert len(sources)==2
for src in sources:assert sha(Path(src['saved_path']))==src['sha256']
saved=load(OLD/'runs/initial/results.json')
row=saved['development'][0]
assert row['input']['source']['revision']==parent['source']['revision']
facts=row['result'];assert len(facts['assignments'])==1
a=facts['assignments'][0]
copies=[c for c in a['consumers'] if c['api']=='memcpy']
assert len(copies)==1
card=load(CARD)
writer=[c for c in card['locked_chain'] if c['role']=='encoded-field writer'];assert len(writer)==1
templates=load(PREV/'runs/initial/results.json')
template=next(r for r in templates['outputs'] if r['query_label_outside_generator']=='development:parent')['generated']['records'][0]
put('inputs_pre.json',dict(source=parent['source'],declaration=parent['declarations'][0],
    consumer_function=facts['function'],assignment_facts=a,copy_consumer_facts=copies[0],
    producer_anchor_for_scope_only=writer[0]['line'],anchor_origin=str(CARD),
    template_facts=template,selection='already-read parent; no fix source or labels in extraction',
    bounds=dict(structures=1,producer_chains=1,copy_consumers=1)))
paths=[HERE/'protocol_pre.md',HERE/'prepare_inputs.py',HERE/'inputs_pre.json',closed,
    PREV/'runs/initial/results.json',OLD/'inputs_pre.json',OLD/'runs/initial/results.json',
    OLD/'completion_manifest.json',CARD]+[Path(s['saved_path']) for s in sources]
put('freeze_inputs_pre.json',dict(files=[dict(path=str(p),sha256=sha(p)) for p in paths],
    new_source_queries=0,paid_models=0,already_read_development=True))
print(json.dumps(dict(freeze_inputs_sha256=sha(HERE/'freeze_inputs_pre.json'),saved_sources=2,
    structures=1,producer_chains=1,copy_consumers=1,new_source_queries=0),ensure_ascii=False))
