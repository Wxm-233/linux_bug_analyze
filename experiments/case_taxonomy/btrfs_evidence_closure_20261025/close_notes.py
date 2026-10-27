from pathlib import Path
import json,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'notes_update.json').exists(),'preserve notes update receipt'
r=json.loads((HERE/'results.json').read_text(encoding='utf-8'))
a=json.loads((HERE/'audit.json').read_text(encoding='utf-8'))
assert a['status']=='verified' and a['results_sha256']==sha(HERE/'results.json')
assert r['summary']['replayed_intervals']==8 and r['summary']['new_boots']==0
before=json.loads((HERE/'notes_before.json').read_text(encoding='utf-8'))['before_sha256']
assert len(before)==3
for n,h in before.items():assert sha(ROOT/n)==h,n
block=(HERE/'conclusion.md').read_text(encoding='utf-8')
for n in before:
 p=ROOT/n;old=p.read_text(encoding='utf-8-sig')
 p.write_text(old.splitlines()[0]+'\n\n文档维护：2026-10-25。完成Btrfs统一归档复核与条件缺口清单；4次既有运行重放，未新增启动，消费期限仍不足。\n\n'+block+'\n\n以下为历史记录，按最新停点解释。\n'+old[old.index('\n## '):],encoding='utf-8')
with (ROOT/'日志/2026-10-25.md').open('a',encoding='utf-8') as f:f.write('\n\n'+block+'\n')
p=ROOT/'接口验证后续规划.md';old=p.read_text(encoding='utf-8-sig')
notice='\n\n> 2026-10-25状态校正：下文10月23日停点保留为历史，已被后续恢复覆盖。Btrfs现已有真实历史内核挂载、文件行为、操作数及有限监测证据，并完成统一归档复核入口；完整消费时刻契约仍不足。VT-d后置，表示接口/R3继续暂缓。当前排程以《当前代办》最新章节为准；不得引用下文“无真实挂载”作为现状。\n'
p.write_text(old.splitlines()[0]+notice+old[old.index('\n'):],encoding='utf-8')
(HERE/'notes_update.json').write_text(json.dumps(dict(before_sha256=before,after_sha256={n:sha(ROOT/n) for n in before}),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Three notes, daily log and stale planning notice updated; WSL sync pending')
