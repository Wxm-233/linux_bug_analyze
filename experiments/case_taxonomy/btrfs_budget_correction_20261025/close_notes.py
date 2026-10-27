from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'notes_update.json').exists(),'preserve notes receipt'
delivery=json.loads((HERE/'delivery.json').read_text(encoding='utf-8'))
assert delivery['status']=='response_refused' and delivery['model_calls']==1
before=json.loads((HERE/'notes_before.json').read_text(encoding='utf-8'))['before_sha256']
assert len(before)==3
for n,h in before.items():assert sha(ROOT/n)==h,n
block=(HERE/'conclusion.md').read_text(encoding='utf-8')
for n in before:
 p=ROOT/n;old=p.read_text(encoding='utf-8-sig')
 p.write_text(old.splitlines()[0]+'\n\n文档维护：2026-10-25。预算更正为每次独立1M；已授权原样重试再次refusal，无新增语义结论，消费期限仍不足。\n\n'+block+'\n\n以下为历史记录，预算解释以最新用户澄清为准。\n'+old[old.index('\n## '):],encoding='utf-8')
with (ROOT/'日志/2026-10-25.md').open('a',encoding='utf-8') as f:f.write('\n\n'+block+'\n')
for name in ('obligations.md','README.md'):
 p=HERE.parent/'btrfs_evidence_closure_20261025'/name;old=p.read_text(encoding='utf-8')
 notice='\n\n> 2026-10-25后续更正：用户明确每次调用独立1M，撤回历史累计预算不足解释；随后已明确授权原任务原材料重试，实际再次refusal。当前不自动重发，预算不构成阻碍。最新收据见../btrfs_budget_correction_20261025/delivery.json。下文保留本轮原判断及原停点历史。\n'
 p.write_text(old.splitlines()[0]+notice+old[old.index('\n'):],encoding='utf-8')
p=ROOT/'接口验证后续规划.md';old=p.read_text(encoding='utf-8')
p.write_text(old.splitlines()[0]+'\n\n> 最新调用口径：每次独立1M；10月25日用户授权的Btrfs原样重试再次refusal，当前无新增语义补证。预算不是阻碍，详见当前代办最新停点。\n'+old[old.index('\n'):],encoding='utf-8')
(HERE/'notes_update.json').write_text(json.dumps(dict(before_sha256=before,after_sha256={n:sha(ROOT/n) for n in before}),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Budget correction and actual retry outcome recorded; mirror sync pending')
