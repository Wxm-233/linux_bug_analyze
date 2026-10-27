from pathlib import Path
import hashlib,json,shutil
H=Path(__file__).resolve().parent;R=H.parents[3]
if (H/'notes_before.json').exists():raise RuntimeError('preserve round')
names=['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']
(H/'notes_before.json').write_text(json.dumps({'before_sha256':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in names}},ensure_ascii=False,indent=2),encoding='utf-8');shutil.copyfile(H.parent/'virtio_cache_boundary_20261027/sync_work_notes.py',H/'sync_work_notes.py')
for name,local in [('接口验证后续规划.md','plan_before.md'),('AGENTS.md','AGENTS_before.md'),('linux_bug_analyze/analysis_out/current_analysis_backend.json','backend_before.json')]:shutil.copyfile(R/name,H/local)
out=R/'模型调用测试/2026-10-27/kimi_connection_repair/v2_minimal';out.mkdir(exist_ok=False);(out/'prompt.md').write_text('Connection test. Reply with exactly KIMI_DIAG_OK.',encoding='utf-8')
(H/'authorization.json').write_text(json.dumps({'date':'2026-10-27','user_request':'你可以先确认一下kimi是什么原因连不上尝试修复一下？','scope':'connectivity diagnostics, client transport repair and bounded verification; preserves old failed requests; no automated retries','research_experiment':False},ensure_ascii=False,indent=2),encoding='utf-8');print('repair round prepared')
