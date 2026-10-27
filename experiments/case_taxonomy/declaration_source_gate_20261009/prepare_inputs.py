"""Prepare frozen development fixtures and one previously saved candidate."""
from pathlib import Path
from copy import deepcopy
import hashlib,json

HERE=Path(__file__).resolve().parent;BASE=HERE.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def blob(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
def put(name,value):
    p=HERE/name;assert not p.exists(),p;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def doc(revision,path,text):
    raw=text.encode('utf-8')
    return dict(revision=revision,source_path=path,text=text,sha256=hashlib.sha256(raw).hexdigest(),blob_sha1=blob(raw))
def ref(d,start,end):
    return dict(revision=d['revision'],source_path=d['source_path'],sha256=d['sha256'],blob_sha1=d['blob_sha1'],
        start_line=start,end_line=end,text='\n'.join(d['text'].splitlines()[start-1:end]))

closed=BASE/'include_route_20261009/completion_manifest.json'
assert sha(closed)=='3d587fcb06a890bfbbf4ec75d38f98cf69c95413c9ec9d67c08d0e533fcb42fc'
for row in load(closed)['files']:assert sha(Path(row['path']))==row['sha256']
results=BASE/'encoded_length_check_development_20261008/runs/initial/results.json'
assert sha(results)=='19cff1d41dd6a606485f76e0f0b1389b669ddcde17eb3cc1f1b257d9d8cb22dc'
candidate=deepcopy(load(results)['development'][0]['result']['assignments'][0])
assert candidate['variable']=='data_len' and candidate['status']=='candidate'
assert candidate['source_field']['type']=='__be16'
route_card=load(BASE/'include_route_20261009/route_card.json')
real_sources={}
for key in ['old_include','kernel_include','wrapper_guard_and_includes','uapi_tag']:
    q=route_card['source_quotes'][key];p=Path(q['saved_path']);raw=p.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==q['sha256'] and blob(raw)==q['blob_sha1']
    real_sources[q['source_path']]=doc(q['revision'],q['source_path'],raw.decode('utf-8'))
def lightweight(q):return {k:q[k] for k in ['revision','source_path','sha256','blob_sha1','start_line','end_line','text']}
real=dict(documents=list(real_sources.values()),candidate=candidate,
    route=dict(include=lightweight(route_card['source_quotes']['old_include']),expected_include_token='../include/linux/if_pppox.h',
        wrapper_source_path='include/linux/if_pppox.h',wrapper_include=ref(real_sources['include/linux/if_pppox.h'],19,19),
        declaration=lightweight(route_card['source_quotes']['uapi_tag']),
        search_roots=[dict(expression='$(objtree)/include',binding=dict(objtree='.'),
            evidence=lightweight(route_card['source_quotes']['kernel_include']),
            assumptions=['normal final in-source-tree build; objtree equals srctree; LINUXINCLUDE is effective'])]))

rev='synthetic-source-gate-v1'
c=doc(rev,'driver/core/sample.c','#include "../include/linux/packet.h"\nstatic void send(struct packet *item, void *skb)\n{\n int count;\n count = item->len + 4;\n if (skb_tailroom(skb) < count)\n  return;\n}\n')
m=doc(rev,'Makefile','LINUXINCLUDE := -I$(srctree)/include -I$(srctree)/shadow\nexport LINUXINCLUDE\n')
w=doc(rev,'include/linux/packet.h','#ifndef PACKET_H\n#define PACKET_H\n#include <uapi/linux/packet.h>\n#endif\n')
u=doc(rev,'include/uapi/linux/packet.h','struct packet {\n __be16 len;\n char data[0];\n} __attribute__((packed));\n')
synthetic_candidate=dict(variable='count',rhs='item->len + 4',operator='=',status='candidate',representation='encoded_be',conversion=None,
    source_field=dict(object='item',structure='packet',field='len',type='__be16',domain='be',width=16,evidence=[ref(u,2,2),ref(c,2,2)],pointer_origin_certified=False),
    evidence=[ref(c,5,5)],consumers=[dict(api='skb_tailroom',role='comparison_to_host_byte_count',length_expression='count',lexical_only=True,runtime_execution_certified=False,evidence=ref(c,6,6))],
    check_proposal='normalize representation before host-byte-count use; establish full length separately',
    actual_include_binding_certified=False,full_preprocessing_certified=False,length_contract_certified=False,runtime_value_proven=False)
base=dict(documents=[c,m,w,u],candidate=synthetic_candidate,
    route=dict(include=ref(c,1,1),expected_include_token='../include/linux/packet.h',wrapper_source_path=w['source_path'],
        wrapper_include=ref(w,3,3),declaration=ref(u,1,4),
        search_roots=[dict(expression='$(srctree)/include',binding=dict(srctree='.'),evidence=ref(m,1,1),assumptions=['explicit source-relative root; effective compiler command unproved'])]))
fixtures=[]
def add(id,payload,status,reason):fixtures.append(dict(id=id,input=payload,expected=dict(disposition=status,required_reason=reason)))
add('conditional_route',deepcopy(base),'conditional_candidate',None)
v=deepcopy(base);v['documents']=[d for d in v['documents'] if d['source_path']!=w['source_path']]
add('missing_wrapper',v,'insufficient','missing_document')
v=deepcopy(base);v['documents'][-1]['revision']='synthetic-other-revision'
add('mixed_revision',v,'insufficient','mixed_revision')
v=deepcopy(base);v['route']['expected_include_token']='linux/packet.h'
add('complete_token_mismatch',v,'insufficient','include_token_mismatch')
v=deepcopy(base)
shadow=doc(rev,'shadow/include/linux/packet.h','#include <uapi/linux/other.h>\n')
v['documents'].append(shadow)
v['route']['search_roots'].append(dict(expression='$(srctree)/shadow',binding=dict(srctree='.'),evidence=ref(m,1,1),assumptions=['known competing supplied search root']))
add('known_competing_root',v,'insufficient','ambiguous_header_route')
v=deepcopy(base);v['candidate']['source_field']['field']='other_len'
add('declaration_identity_mismatch',v,'insufficient','declaration_identity_mismatch')
v=deepcopy(base);v['documents'][-1]['sha256']='0'*64
add('forged_fingerprint',v,'insufficient','document_fingerprint_mismatch')
v=deepcopy(base);v['route']['actual_preprocessing_certified']=True;v['candidate']['source_field']['pointer_origin_certified']=True
add('claimed_certification',v,'insufficient','unsupported_certification')
assert len(fixtures)==8
put('fixtures_pre.json',dict(scope='synthetic development boundaries; not independent cases',fixtures=fixtures))
put('real_input_pre.json',dict(scope='one previously read parent candidate; attachment only',input=real,
    expected=dict(disposition='conditional_candidate',required_reason=None),
    source_result_path=str(results),source_result_sha256=sha(results),json_pointer='/development/0/result/assignments/0'))
paths=[HERE/'protocol_pre.md',HERE/'prepare_inputs.py',HERE/'fixtures_pre.json',HERE/'real_input_pre.json',closed,results]
paths+=[Path(q['saved_path']) for q in route_card['source_quotes'].values()]
paths=sorted(set(paths))
put('freeze_inputs_pre.json',dict(files=[dict(path=str(p),sha256=sha(p)) for p in paths],synthetic_inputs=8,real_saved_candidates=1,new_rule_runs_before_lock=0))
print(json.dumps(dict(freeze_sha256=sha(HERE/'freeze_inputs_pre.json'),synthetic_inputs=8,real_saved_candidates=1),ensure_ascii=False))
