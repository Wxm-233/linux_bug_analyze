from pathlib import Path
import json,hashlib,shutil
H=Path(__file__).resolve().parent;R=H.parents[3];M=R/'模型调用测试';route=R/'linux_bug_analyze/analysis_out/current_analysis_backend.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
save('notes_before.json',{'before_sha256':{n:sha(R/n) for n in ['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']}})
shutil.copyfile(H.parent/'smmu_stage_20261026/sync_work_notes.py',H/'sync_work_notes.py');shutil.copyfile(route,H/'backend_before.json');shutil.copyfile(R/'AGENTS.md',H/'AGENTS_before.md')
d=json.loads(route.read_text(encoding='utf-8'));d.setdefault('historical_primary_analysis',[]).append(d['primary_analysis']);d['updated']='2026-10-26';d['primary_analysis']=dict(client='Python SSE client',model='Kimi-K3',base_url='https://llmapi.isrc.ac.cn/v1',api_format='OpenAI compatible Chat Completions SSE',credential_profile='kimi-k3-newkey-20261025',credential_injection='external WSL key file through memory/anonymous pipe only',output_root_windows=str(M),runner='模型调用测试/run_kimi_review.py',user_authorized_switch='2026-10-26: all subsequent main analysis uses Kimi',delivery_policy='Require model Kimi-K3, nonempty final, stop, DONE and EOF without refusal/API error/tools; then source and experiment review',connectivity_status='pending_new_virtio_attempt');d['historical_profiles']='Claude/Sonnet routes preserved as history; Kimi-K3 active primary';route.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=R/'AGENTS.md';s=p.read_text(encoding='utf-8');start=s.index('- 项目后续的源码主分析统一使用');end=s.index('## 周报和文稿',start)
s=s[:start]+'''- 用户于2026-10-26明确要求后续主分析统一改为 **Kimi-K3**，使用ISRC平台的OpenAI兼容Chat Completions SSE接口（`https://llmapi.isrc.ac.cn/v1/chat/completions`）。这项新指示替代此前Claude默认路由；本次virtio任务允许转交Kimi，旧Claude两次拒绝记录保留，不改成成功。
- 当前路由见`linux_bug_analyze/analysis_out/current_analysis_backend.json`，调用入口`模型调用测试/run_kimi_review.py`。复用既有`kimi-k3-newkey-20261025`外部凭据配置，密钥仅通过内存/子进程管道注入，禁止写入仓库或忽略目录。
- 输出保存在已忽略的`模型调用测试/`，保留请求、流式正文、最终结果及用量。仅实际模型Kimi-K3、非空正文、stop、DONE和EOF齐备且无错误/refusal才算完整交付；完整返回不等于内容正确，仍需源码和实验复核。
- 出现refusal或调用失败时保留记录，不自动改写恢复拒绝内容，不自动重试；用户新授权优先。历史Claude原生客户端2.1.301/Opus及旧Sonnet配置只作历史，不自动回退。
- 旧轮次、失败、原始回答和未知用量保留；不重发旧请求ID。每次调用独立1M为用户额度口径，不等于模型/平台实际上下文上限；可见用量不是完整账单。DeepSeek初筛与案例主分析是不同入口。

'''+s[end:];p.write_text(s,encoding='utf-8')
template=(M/'2026-10-25/run_kimi_btrfs_helper.py').read_text(encoding='utf-8')
template=template.replace('import hashlib,importlib.util,json,queue,threading,time,urllib.request,urllib.error','import hashlib,importlib.util,json,queue,threading,time,urllib.request,urllib.error,sys')
template=template.replace("HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]","HERE=Path(__file__).resolve().parent;ROOT=HERE.parent")
template=template.replace("OUT=HERE/'btrfs_kimi_helper_closure';assert OUT.is_dir() and not (OUT/'receipt.json').exists()","OUT=Path(sys.argv[1]).resolve();assert HERE in OUT.parents and OUT.is_dir() and not (OUT/'receipt.json').exists()")
template=template.replace('prompt_unchanged=False','prompt_unchanged=True').replace('default_route_changed=False','default_route_changed=True').replace('1800','900')
# Research notes are tracked by this round, not rewritten by the model transport.
a=template.index("notes=['当前代办.md'");b=template.index("spec=importlib",a);template=template[:a]+template[b:]
(M/'run_kimi_review.py').write_text(template,encoding='utf-8')
out=M/'2026-10-26/virtio_kimi_dma_chain';out.mkdir(exist_ok=False);shutil.copyfile(M/'2026-10-26/virtio_dma_chain/prompt.md',out/'prompt.md')
save('route_change.json',dict(user_authorized=True,model='Kimi-K3',same_prompt_sha256=sha(out/'prompt.md'),backend_after_sha256=sha(route),agents_after_sha256=sha(p),runner_sha256=sha(M/'run_kimi_review.py'),credential_contents_read_or_saved=False))
print('Kimi default route and AGENTS updated; original virtio prompt copied unchanged.')
