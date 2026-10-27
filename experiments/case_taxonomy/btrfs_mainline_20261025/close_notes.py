from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
assert not (HERE/'notes_update.json').exists(),'preserve receipt'
r=read(HERE/'results.json');assert (r['intent_matches'],r['intent_mismatches'])==(8,12)
assert read(HERE/'diagnostic_control.json')['status']=='unchanged_real_diagnostics'
before=read(HERE/'notes_before.json')['before_sha256'];assert len(before)==3
for n,h in before.items():assert sha(ROOT/n)==h,n
block=(HERE/'conclusion.md').read_text(encoding='utf-8')
for n in before:
 p=ROOT/n;old=p.read_text(encoding='utf-8-sig')
 p.write_text(old.splitlines()[0]+'\n\n文档维护：2026-10-25。按用户要求回归接口分析→自动分析程序；新增候选接口意图检查并接原核心，旁支不再默认推进。\n\n'+block+'\n\n以下为历史记录，下一步以最新主线安排为准。\n'+old[old.index('\n## '):],encoding='utf-8')
with (ROOT/'日志/2026-10-25.md').open('a',encoding='utf-8') as f:f.write('\n\n'+block+'\n')
p=ROOT/'接口验证后续规划.md';old=p.read_text(encoding='utf-8')
p.write_text(old.splitlines()[0]+'\n\n> 2026-10-25最新主线：接口分析→候选要求→自动程序。Btrfs接口卡及结构化候选意图检查已建立，下一步接模型结构化输出与事实提取；撤销默认深挖设备清理/日志callee的安排，详见当前代办最新章节。历史调用停点不再作为当前总排程。\n'+old[old.index('\n'):],encoding='utf-8')
(HERE/'notes_update.json').write_text(json.dumps(dict(before_sha256=before,after_sha256={n:sha(ROOT/n) for n in before}),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Mainline plan, daily log and three notes updated; WSL sync pending')
