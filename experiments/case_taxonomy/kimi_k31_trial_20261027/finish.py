from pathlib import Path
import hashlib,json,copy
H=Path(__file__).resolve().parent;R=H.parents[3];D=R/'模型调用测试/2026-10-27/kimi_k31_pro_highspeed_trial';target='Kimi-K3.1-Pro-HighSpeed'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if (H/'notes_update.json').exists():raise RuntimeError('preserve completed round')
receipt=read(D/'receipt.json');catalog=read(D/'catalog.json');tests=read(D/'model_gate_tests.json')
if receipt['status']!='complete_final_received' or receipt['actual_models']!=[target] or (D/'final.md').read_text()!='KIMI_DIAG_OK' or not catalog['requested_model_present'] or tests['failures'] or tests['errors']:raise RuntimeError('qualification failed; do not change default')
backend=R/'linux_bug_analyze/analysis_out/current_analysis_backend.json';b=read(backend)
previous=copy.deepcopy(b['primary_analysis']);previous['superseded']='2026-10-27 user requested Kimi-K3.1-Pro-HighSpeed after exact-model minimal qualification';b.setdefault('historical_primary_analysis',[]).append(previous)
p=b['primary_analysis'];p.update(model=target,credential_profile='kimi-k31-pro-highspeed-20261027',user_authorized_switch='2026-10-27 user requested Kimi-K3.1-Pro-HighSpeed; exact-model minimal verified',delivery_policy='Require exact requested model Kimi-K3.1-Pro-HighSpeed, nonempty final, stop, DONE and EOF with no API error/refusal/tools; source and experiment review afterward',connectivity_status='k31_pro_highspeed_direct_minimal_complete_20261027',latest_receipt='模型调用测试/2026-10-27/kimi_k31_pro_highspeed_trial/receipt.json',latest_receipt_scope='minimal connectivity only',latest_connectivity_receipt='模型调用测试/2026-10-27/kimi_k31_pro_highspeed_trial/receipt.json',connectivity_note='Catalog present; one minimal exact model completion in5.422s; not full-source stability or quality evidence',semantic_review='No source analysis yet for this model; historical K3 source review preserved in historical_primary_analysis',source_analysis_delivery_status='not_attempted_for_new_model',latest_attempt=dict(date='2026-10-27',scope='minimal exact-model qualification',status='complete_final_received',actual_model=target,visible_reported_tokens=receipt['visible_reported_tokens'],automatic_retry=False))
p['transport']['version']=3;b['updated']='2026-10-27';b['python_runner_consumes_primary_analysis_record']=True;b['historical_profiles']='Claude and Kimi-K3 preserved as history; Kimi-K3.1-Pro-HighSpeed active primary';dump(backend,b)
ag=R/'AGENTS.md';s=ag.read_text(encoding='utf-8')
old='- 用户于2026-10-26明确要求后续主分析统一改为 **Kimi-K3**，使用ISRC平台的OpenAI兼容Chat Completions SSE接口（`https://llmapi.isrc.ac.cn/v1/chat/completions`）。这项新指示替代此前Claude默认路由；本次virtio任务允许转交Kimi，旧Claude两次拒绝记录保留，不改成成功。'
new='- 用户于2026-10-27要求主分析改用 **Kimi-K3.1-Pro-HighSpeed**，ISRC模型目录及一次精确模型最小调用已验证（5.422秒、stop/DONE/EOF）。使用同一OpenAI兼容Chat Completions SSE接口（`https://llmapi.isrc.ac.cn/v1/chat/completions`）。10月26日Kimi-K3默认路由和更早Claude配置保留为历史；短测不代表完整源码分析稳定或语义正确。'
if old not in s:raise RuntimeError('unexpected AGENTS source')
s=s.replace(old,new).replace('复用既有`kimi-k3-newkey-20261025`外部凭据配置','当前使用`kimi-k31-pro-highspeed-20261027`配置，复用既有仓库外凭据文件，旧`kimi-k3-newkey-20261025`配置保留').replace('仅实际模型Kimi-K3、非空正文','仅实际模型Kimi-K3.1-Pro-HighSpeed与请求完全匹配、非空正文').replace('历史Claude原生客户端2.1.301/Opus及旧Sonnet配置只作历史，不自动回退。','历史Kimi-K3及Claude原生客户端2.1.301/Opus、旧Sonnet配置只作历史，不自动回退。')
s=s.replace('当前路由见`linux_bug_analyze/analysis_out/current_analysis_backend.json`，调用入口`模型调用测试/run_kimi_review.py`。','当前路由见`linux_bug_analyze/analysis_out/current_analysis_backend.json`，调用入口`模型调用测试/run_kimi_review.py`，该Python入口现在读取JSON中的主模型与凭据配置，并按请求模型严格核验响应。')
ag.write_text(s,encoding='utf-8')
dump(H/'qualification.json',dict(requested_model=target,catalog_present=True,actual_models=receipt['actual_models'],elapsed_seconds=receipt['elapsed_seconds'],stop=receipt['finish_reasons'],done=receipt['done_marker'],eof=receipt['network_eof'],visible_reported_tokens=receipt['visible_reported_tokens'],usage_known=False,default_switched=True,source_analysis_completed=False,original_failed_cache_task_resent=False,model_calls=1,catalog_gets=1,local_model_gate_tests=4,independent_positive=0,independent_normal=0,evidence_sha256={str(p.relative_to(R)):sha(p) for p in [D/'catalog.json',D/'receipt.json',D/'model_gate_tests.json',R/'模型调用测试/kimi_transport.py',R/'模型调用测试/run_kimi_review.py',backend,ag]}))
section='''## 10月27日 最新维护：主分析切换Kimi-K3.1-Pro-HighSpeed，最小实测通过

按用户“模型换成Kimi-K3.1-Pro-HighSpeed，试试”的新指示执行。ISRC直连认证模型目录200、三项中包含该精确标识；发送1次最小请求，5.422秒完整交付KIMI_DIAG_OK，actual_models仅Kimi-K3.1-Pro-HighSpeed、stop/DONE/EOF齐备，无refusal或错误。可见用量161 token，usage_known=false，不当完整账单；每调用独立1M口径不变。这里只确认平台有该模型且可调用，不独立宣称全球最新版本或分析质量更高。

已将AGENTS和current_analysis_backend主模型更新为Kimi-K3.1-Pro-HighSpeed，独立配置kimi-k31-pro-highspeed-20261027仅引用原仓库外密钥文件；没有复制密钥。K3完整旧路由、成功研究结果与失败/未知费用保留在历史。仍采用证书校验HTTPS直连、连接30秒/上传60秒/读空闲600秒/墙钟900秒，不修改系统代理或ccSwitch，无自动回退/重试。

入口改为读取主路由JSON的model和credential_profile；传输器按请求的精确模型验证响应，不再硬编码只认K3。4项本地模型门控测试通过：新名匹配成功、旧响应不得算新模型成功、反向错配也拒判、历史K3仍可显式验证；这些不调用API。本轮只有1次模型生成及1次目录GET，未重跑旧缓存源码任务，无新内核实验、接口结论或缺陷，独立正例/正常0/0。

下一项仍是virtio限定用途方法评审。新模型的大源码任务尚未执行，旧缓存补充任务失败停点保留，不能将短测写成研究分析完成。后续新授权范围内的主分析默认使用此精确模型，仍需源码/实验复核。

证据：模型调用测试/2026-10-27/kimi_k31_pro_highspeed_trial/（catalog、prompt、call_plan、events、final、receipt、model_gate_tests）；linux_bug_analyze/experiments/case_taxonomy/kimi_k31_trial_20261027/（authorization、qualification、README及旧路由/代码/工作文档备份）。规划及当日日志、待办、进展、交接同步维护，三份WSL镜像以notes_sync成功收据为准，Word未改。

以下为历史记录，以本节及用户最新指示为准。

'''
(H/'README.md').write_text('# Kimi-K3.1-Pro-HighSpeed最小调用资格与默认切换\n\n'+section,encoding='utf-8');(D/'README.md').write_text('# Kimi-K3.1-Pro-HighSpeed最小调用资格与默认切换\n\n'+section,encoding='utf-8')
plan=R/'接口验证后续规划.md';s=plan.read_text(encoding='utf-8').replace('后续源码主分析Kimi-K3，每调用独立1M','后续源码主分析Kimi-K3.1-Pro-HighSpeed（10/27最小调用已验证），每调用独立1M');s+='\n## 2026-10-27 主模型更新\n\n用户指定Kimi-K3.1-Pro-HighSpeed，目录与精确模型最小SSE调用通过，已切为主分析默认；新模型源码分析仍未执行，不增加接口完成或独立评价。证据模型调用测试/2026-10-27/kimi_k31_pro_highspeed_trial/。\n';plan.write_text(s,encoding='utf-8')
before=read(H/'notes_before.json')['before_sha256'];after={}
for name,d in before.items():
 p=R/name
 if sha(p)!=d:raise RuntimeError('working note changed '+name)
 title,_,body=p.read_text(encoding='utf-8').partition('\n');p.write_text(title+'\n\n'+section+body.lstrip('\n'),encoding='utf-8');after[name]=sha(p)
dump(H/'notes_update.json',dict(before_sha256=before,after_sha256=after))
with (R/'日志/2026-10-27.md').open('a',encoding='utf-8') as f:f.write('\n\n'+section)
print(json.dumps({'default_model':target,'qualification':'complete_exact_model_minimal','source_analysis_completed':False}))
