"""Resume only on explicit user instruction, preserving interrupted request."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
old=HERE.parent/'btrfs_stability_inventory_20261024'
checkpoint=json.loads((old/'checkpoint.json').read_text(encoding='utf-8'))
assert checkpoint['status']=='paused_by_user'
assert checkpoint['conservative_accounted_tokens']+200000<=1000000
materials=json.loads((old/'supplement_materials.json').read_text(encoding='utf-8'))
for doc in materials['documents']:
    assert hashlib.sha256(Path(doc['path']).read_bytes()).hexdigest()==doc['sha256']
source=Path(materials['output_directory'])/'prompt.md'
assert hashlib.sha256(source.read_text(encoding='utf-8').encode()).hexdigest()==materials['prompt_sha256']
out=ROOT/'模型调用测试/2026-10-24/btrfs_interval_stability_resumed'
out.mkdir(exist_ok=False)
(out/'prompt.md').write_bytes(source.read_bytes())
names=['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']
(HERE/'notes_before.json').write_text(json.dumps({'before_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
plan=dict(user_instruction='继续刚才的实验吧',prior_checkpoint=str(old/'checkpoint.json'),
    previous_accounted=checkpoint['conservative_accounted_tokens'],new_reservation=200000,
    cumulative_reserved=checkpoint['conservative_accounted_tokens']+200000,
    output=str(out),prompt_sent_sha256=materials['prompt_sha256'],
    old_request_id_reused=False,interrupted_partial_used=False,
    note='User-requested new CLI task using unchanged supplemental source prompt; prior interruption was user cancellation, not refusal.')
(HERE/'resume_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(plan,ensure_ascii=False))
