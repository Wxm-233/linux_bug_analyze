from pathlib import Path
import hashlib,json,shutil
H=Path(__file__).resolve().parent;R=H.parents[3];D=R/'模型调用测试/2026-10-27/kimi_connection_repair'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if (H/'notes_update.json').exists():raise RuntimeError('preserve round')
network=read(D/'network.json');system=read(D/'minimal_receipt.json');direct=read(D/'direct/minimal_receipt.json');v2=read(D/'v2_minimal/receipt.json');tests=read(D/'test_results.json')
if direct['status']!='complete' or v2['status']!='complete_final_received' or (D/'v2_minimal/final.md').read_text()!='KIMI_DIAG_OK':raise RuntimeError('not verified')
if tests['failures'] or tests['errors']:raise RuntimeError('local tests failed')
summary=dict(date='2026-10-27',purpose='user-authorized transport diagnostics and repair; no new research experiment',findings={
 'network':'DNS/TCP/TLS verified; system proxy and direct unauthenticated GET both return401 promptly',
 'authentication':'authenticated model catalog returns200, Kimi-K3 present',
 'controlled_minimal_payload_sha256':direct['payload_sha256'],
 'identical_minimal_payload':system['payload_sha256']==direct['payload_sha256']==v2['payload_sha256'],
 'system_proxy_elapsed_seconds':system['elapsed_seconds'],'system_proxy_result':system['status'],
 'direct_elapsed_seconds':direct['elapsed_seconds'],'direct_result':direct['status'],
 'repaired_runner_elapsed_seconds':v2['elapsed_seconds'],'connect_seconds':v2['connect_seconds'],'headers_seconds':v2['response_headers_seconds'],
 'causal_limit':'sequential same-payload route contrast shows a current proxy-path anomaly; historical uninstrumented TimeoutError cannot isolate original network phase or prove all failures have same cause',
 'timeout_defect':'old urlopen timeout180 applied inside outer900; repaired connect30/upload60/read-idle600/wall900 with phase receipts'},
 verification=dict(local_test_methods=tests['tests'],network_timeout_subcases=4,completion_gate_subcases=6,minimal_generation_requests=3,completed=2,incomplete=1,visible_reported_tokens_successful_minimals=(direct['usage'] or {})['total_tokens']+v2['visible_reported_tokens'],failed_request_usage='unknown, not zero',original_source_request_resent=False,new_kernel_experiments=0),
 repairs=['entry defaults to direct TLS to fixed ISRC endpoint; system proxy available only by explicit option','split connection/upload/read/wall timeouts','connect/upload/header/SSE/EOF phase accounting','preserve refusal/wrong model/no DONE/no EOF rejection and no automatic retry','preserve historical failed requests and runner backup'],
 evidence_sha256={str(p.relative_to(R)):sha(p) for p in [D/'network.json',D/'minimal_receipt.json',D/'direct/minimal_receipt.json',D/'v2_minimal/receipt.json',D/'test_results.json',D/'run_kimi_review_before.py',R/'模型调用测试/run_kimi_review.py',R/'模型调用测试/kimi_transport.py']})
dump(H/'diagnosis.json',summary);dump(D/'diagnosis.json',summary)
backend=R/'linux_bug_analyze/analysis_out/current_analysis_backend.json';b=read(backend);b['updated']='2026-10-27'
primary=b['primary_analysis'];primary['transport']=dict(version=2,default_proxy_mode='direct',tls_certificate_verification=True,connect_timeout_seconds=30,write_timeout_seconds=60,read_idle_timeout_seconds=600,wall_timeout_seconds=900,automatic_retries=0,diagnostic='模型调用测试/2026-10-27/kimi_connection_repair/diagnosis.json')
primary['connectivity_status']='direct_v2_minimal_verified_20261027'
primary['latest_connectivity_receipt']='模型调用测试/2026-10-27/kimi_connection_repair/v2_minimal/receipt.json'
primary['connectivity_note']='Direct minimal complete Kimi-K3/stop/DONE/EOF; original large source task not resent, previous failed research attempt retained; short test not stability proof'
dump(backend,b)
ag=R/'AGENTS.md';s=ag.read_text(encoding='utf-8');needle='- 输出保存在已忽略的`模型调用测试/`'
line='- 2026-10-27连通诊断后，`run_kimi_review.py`默认以证书校验的HTTPS直连ISRC，绕过本入口的系统代理；不修改系统代理或ccSwitch。`--proxy-mode system`仅显式诊断时使用，无自动回退。传输实现`模型调用测试/kimi_transport.py`，连接30秒、上传60秒、读空闲600秒、总墙钟900秒，并保存连接/上传/响应头/SSE阶段；旧180秒内层超时及历史失败保留。两次直连最小请求完成不代表大源码分析或长期稳定性已验证。\n'
if line not in s:s=s.replace(needle,line+needle);ag.write_text(s,encoding='utf-8')
section='''## 10月27日 最新维护：Kimi连通诊断与传输入口修复

按用户“确认kimi为何连不上并尝试修复”要求，暂先处理工具连接，不启动新内核实验。DNS/TCP/TLS正常（直连约0.203秒），系统代理和直连无认证GET均快速401；既有密钥认证模型目录200，Kimi-K3存在。无密钥、认证头或完整代理凭据写入仓库；凭据仍仓库外经内存读取。

同一195字节最小请求、同一payload SHA的顺序对照：系统代理127.0.0.1:7892路径62.25秒TimeoutError，无HTTP/正文；禁用本入口代理后15.672秒完整Kimi-K3/stop/DONE/EOF，正文KIMI_DIAG_OK。修复入口再次直连实测45.266秒完成，建连0.187秒、响应头45.234秒。表明当前代理路径有异常，认证/模型可用；顺序对照仍可能受服务时变影响，不断言所有历史超时都由代理造成。原181.234秒失败没有阶段日志，无法事后精确定位其连接/上传/响应头环节。

修复：保留旧runner备份，将run_kimi_review.py改用kimi_transport.py；默认证书校验直连ISRC，本机系统代理与ccSwitch未改。允许显式--proxy-mode system诊断，不自动切换/重试。旧urlopen的180秒限制位于外层900秒内，可提前中断；新设置分开连接30秒、上传60秒、读空闲600秒、总墙钟900秒，并记录connect/upload/response_headers/sse_read/EOF及时间。出现refusal、错误模型、缺正文/stop/DONE/EOF仍不算完整交付；隐藏推理不保存，错误不输出认证信息。

验证：6个本地测试方法通过，含4个超时阶段及6种完成门控子场景、拒绝后正常结束仍拒判、坏SSE/结束后追加数据、旧收据保护、保密与keepalive。没有向API发这些单元测试。实际生成请求共3个：1个系统代理失败，2个直连成功；成功请求可见用量143+168=311 token，失败用量未知，不计0，也不当完整账单。2次认证目录GET及无认证网络检查另列，不计生成请求。原172602字节缓存源码prompt和失败收据未改、未重发；原大任务仍未由修复入口验证完成。

这轮属于分析工具维护，不新增接口结论、模型要求、内核实验或Linux缺陷，独立正例/正常仍0/0。研究下一项仍是virtio限定用途方法评审；Kimi缓存补充分析的原失败停点保留，未来调用使用修复入口，已有短测不能充大源码稳定性证明。主模型仍Kimi-K3，预算每调用独立1M，旧Claude记录不变。

证据：模型调用测试/2026-10-27/kimi_connection_repair/（network、两路径minimal_receipt、v2_minimal、test_results、runner备份、diagnosis）；linux_bug_analyze/experiments/case_taxonomy/kimi_transport_repair_20261027/（authorization、diagnosis、README、notes收据及维护前文档）。AGENTS、路由和规划已同步维护；日志、待办、进展、交接同轮更新，三份WSL镜像以notes_sync成功收据为准，Word未改。

以下为历史记录，以本节及用户最新指示为准。

'''
(H/'README.md').write_text('# Kimi连接诊断及传输入口修复\n\n'+section,encoding='utf-8');(D/'README.md').write_text('# Kimi连接诊断及传输入口修复\n\n'+section,encoding='utf-8')
plan=R/'接口验证后续规划.md';s=plan.read_text(encoding='utf-8');s+='\n## 2026-10-27 工具维护记录\n\nKimi入口已默认HTTPS直连ISRC，并拆分超时及阶段日志；系统代理最小生成请求失败、两次直连最小请求完整完成。证据模型调用测试/2026-10-27/kimi_connection_repair/。这是连接修复，未重发原缓存源码任务，不增加接口完成或独立评价；研究下一项仍为virtio方法评审。\n';plan.write_text(s,encoding='utf-8')
before=read(H/'notes_before.json')['before_sha256'];after={}
for n,digest in before.items():
 p=R/n
 if sha(p)!=digest:raise RuntimeError('working note changed '+n)
 title,_,body=p.read_text(encoding='utf-8').partition('\n');p.write_text(title+'\n\n'+section+body.lstrip('\n'),encoding='utf-8');after[n]=sha(p)
dump(H/'notes_update.json',dict(before_sha256=before,after_sha256=after))
with (R/'日志/2026-10-27.md').open('a',encoding='utf-8') as f:f.write('\n\n'+section)
print(json.dumps(dict(transport='direct_v2_verified',local_test_methods=6,minimal_generations=3,complete_minimals=2,original_large_task_resent=False)))
