"""Correct one pre-execution competing-root fixture, preserve original lock."""
from pathlib import Path
import hashlib,json,posixpath

HERE=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
original=load(HERE/'freeze_inputs_pre.json')
for row in original['files']:assert sha(Path(row['path']))==row['sha256']
data=load(HERE/'fixtures_pre.json')
case=data['fixtures'][4];assert case['id']=='known_competing_root'
payload=case['input']
make=next(d for d in payload['documents'] if d['source_path']=='Makefile')
make['text']=make['text'].replace('-I$(srctree)/shadow\n','-I$(srctree)/shadow/include\n')
raw=make['text'].encode('utf-8');make['sha256']=hashlib.sha256(raw).hexdigest()
make['blob_sha1']=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
payload['route']['search_roots'][1]['expression']='$(srctree)/shadow/include'
for root in payload['route']['search_roots']:
    q=root['evidence'];q.update(sha256=make['sha256'],blob_sha1=make['blob_sha1'],text=make['text'].splitlines()[0])
token=payload['route']['expected_include_token']
assert posixpath.normpath(posixpath.join('shadow/include',token))=='shadow/include/linux/packet.h'
target=HERE/'fixtures_pre_v2.json';assert not target.exists()
target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
paths=[Path(row['path']) for row in original['files']]+[HERE/'freeze_inputs_pre.json',HERE/'input_errata_pre.md',HERE/'revise_inputs_pre.py',target]
lock=HERE/'freeze_inputs_v2_pre.json';assert not lock.exists()
lock.write_text(json.dumps(dict(files=[dict(path=str(p),sha256=sha(p)) for p in sorted(set(paths))],synthetic_inputs=8,real_saved_candidates=1,
    active_fixture_path=str(target),original_lock_sha256=sha(HERE/'freeze_inputs_pre.json'),reason='one pre-execution fixture geometry correction',new_rule_runs_before_lock=0),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(active_input_lock_sha256=sha(lock),original_input_lock_sha256=sha(HERE/'freeze_inputs_pre.json'),changed_fixture='known_competing_root',rule_runs=0),ensure_ascii=False))
