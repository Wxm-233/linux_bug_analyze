from pathlib import Path
import hashlib,json,shutil
H=Path(__file__).resolve().parent;R=H.parents[3];D=R/'模型调用测试/2026-10-27/kimi_k31_pro_highspeed_trial'
if (H/'notes_before.json').exists():raise RuntimeError('preserve round')
notes=['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']
(H/'notes_before.json').write_text(json.dumps({'before_sha256':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in notes}},ensure_ascii=False,indent=2),encoding='utf-8')
shutil.copyfile(H.parent/'kimi_transport_repair_20261027/sync_work_notes.py',H/'sync_work_notes.py')
for src,name in [('AGENTS.md','AGENTS_before.md'),('接口验证后续规划.md','plan_before.md'),('linux_bug_analyze/analysis_out/current_analysis_backend.json','backend_before.json'),('模型调用测试/run_kimi_review.py','runner_before.py'),('模型调用测试/kimi_transport.py','transport_before.py')]:shutil.copyfile(R/src,H/name)
profile='kimi-k31-pro-highspeed-20261027';dest=R/'linux_bug_analyze/analysis_out'/profile;dest.mkdir(exist_ok=False)
old=R/'linux_bug_analyze/analysis_out/kimi-k3-newkey-20261025/settings.toml';s=old.read_text(encoding='utf-8');s=s.replace('# User-authorized Kimi comparison; not a global primary-model change.','# User-authorized Kimi-K3.1-Pro-HighSpeed trial; existing external credential only.').replace('model = "Kimi-K3"','model = "Kimi-K3.1-Pro-HighSpeed"');(dest/'settings.toml').write_text(s,encoding='utf-8')
D.mkdir(exist_ok=False);(D/'prompt.md').write_text('Connection test. Reply with exactly KIMI_DIAG_OK.',encoding='utf-8')
(H/'authorization.json').write_text(json.dumps({'date':'2026-10-27','user_request':'要不把模型换成最新的：Kimi-K3.1-Pro-HighSpeed吧，你试试','requested_model':'Kimi-K3.1-Pro-HighSpeed','scope':'model catalog and one minimal generation; switch primary default if exact model delivery succeeds; preserve old route and no automatic fallback'},ensure_ascii=False,indent=2),encoding='utf-8');print('snapshots and isolated new profile prepared; no key copied')
