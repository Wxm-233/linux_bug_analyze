from pathlib import Path
import json,hashlib,shutil
H=Path(__file__).resolve().parent;R=H.parents[3]
if (H/'notes_before.json').exists():raise RuntimeError('preserve round')
notes=['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']
(H/'notes_before.json').write_text(json.dumps({'before_sha256':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in notes}},ensure_ascii=False,indent=2),encoding='utf-8')
for name,dest in [('接口验证后续规划.md','plan_before.md'),('linux_bug_analyze/analysis_out/current_analysis_backend.json','backend_before.json')]:shutil.copyfile(R/name,H/dest)
shutil.copyfile(H.parent/'kimi_k31_trial_20261027/sync_work_notes.py',H/'sync_work_notes.py')
tasks=[]
for name,old in [('virtio_k31_cache_large','2026-10-27/virtio_cache_boundaries'),('virtio_k31_chain_large','2026-10-26/virtio_kimi_dma_chain')]:
 source=R/'模型调用测试'/old/'prompt.md';out=R/'模型调用测试/2026-10-27'/name;out.mkdir(exist_ok=False);shutil.copyfile(source,out/'prompt.md')
 tasks.append(dict(name=name,output=str(out.relative_to(R)),original_prompt=str(source.relative_to(R)),prompt_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),bytes=len(source.read_bytes()),policy='one new-model attempt per frozen distinct task; stop on failure; no rewritten request or automatic retry'))
frozen_checks=[
 ('A01','cache','DminLine determines the maintenance stride; CWG and allocation alignment have separate roles'),
 ('A02','cache','partial-end before partial-start invalidation; same partial line can receive two CIVACs'),
 ('A03','cache','clean-cache workaround can turn CVAC into CIVAC'),
 ('A04','cache','direct original object vs bounce object maintenance; copyback and maintenance are separate'),
 ('A05','cache','ARCH_DMA_MINALIGN128 is not ARCH_KMALLOC_MINALIGN8 or a measured runtime line size'),
 ('A06','cache','no real DMA damage/platform/cache-effect claim from local function evidence'),
 ('B01','chain','event add_inbuf vs status add_outbuf distinction'),
 ('B02','chain','single SG does not allocate indirect table; enabled feature can still visit empty detach cleanup'),
 ('B03','chain','no incorrect 736%64 boundary claim or invented actual target ABI'),
 ('B04','chain','use_map_api feature/Xen selection and custom vs standard parent-device mapping'),
 ('B05','chain','bypass mapping does not eliminate all add failures'),
 ('B06','chain','no unqualified internal-event-sharing safety assertion'),
 ('B07','chain','unmap callback order does not itself establish all backend CPU visibility'),
 ('B08','chain','full8-byte write requirement needs protocol authority if not provided')]
plan=dict(user_authorization='2026-10-27: 进行下一步待办，可以顺便验证大源码分析稳定性及效果',model='Kimi-K3.1-Pro-HighSpeed',proxy_mode='direct',max_output_tokens=24576,tasks=tasks,frozen_semantic_checks=[dict(id=i,task=t,question=q) for i,t,q in frozen_checks],grading='manual source/archived evidence review: supported, qualified, error, not_addressed; not independent evaluation or accuracy',stability='report only number of completed consecutive distinct large tasks, timings and phase/usage; no reliability percentage or general stability claim',independent_positive=0,independent_normal=0)
(H/'frozen_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'frozen_tasks':tasks,'semantic_checks':len(frozen_checks)},ensure_ascii=False))
