from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;R=H.parents[3];M=R/'模型调用测试/2026-10-27/virtio_k31_cache_large';B=R/'模型调用测试/2026-10-27/virtio_k31_chain_large'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if (H/'notes_update.json').exists():raise RuntimeError('preserve round')
plan=read(H/'frozen_plan.json');receipt=read(M/'receipt.json');limits=read(M/'model_limits.json')
if receipt['status']=='started':raise RuntimeError('model still running')
if sha(M/'prompt.md')!=plan['tasks'][0]['prompt_sha256']:raise RuntimeError('prompt changed')
if (B/'receipt.json').exists():raise RuntimeError('second task unexpectedly started')
if receipt['status']!='incomplete_or_error' or receipt['finish_reasons']!=['length'] or receipt['actual_models']!=['Kimi-K3.1-Pro-HighSpeed']:raise RuntimeError('review unexpected outcome before finishing')
dump(B/'not_started.json',dict(status='not_started',reason='first frozen task incomplete at length limit; stop-on-failure policy',model_requests=0,prompt_sha256=plan['tasks'][1]['prompt_sha256']))
semantic=[dict(c,status='not_evaluable_no_complete_final' if c['task']=='cache' else 'not_started',source_and_experiment_audit='not scored as model output',model_candidate_adoption=0) for c in plan['frozen_semantic_checks']]
dump(H/'semantic_review.json',dict(checks=semantic,semantic_effect='not_evaluable_without_final',complete_candidate_adoption=0,no_quality_or_accuracy_claim=True,old_model_errors_not_attributed_to_new_model=True))
report=dict(model=receipt['model'],request_prompt_bytes=plan['tasks'][0]['bytes'],request_payload_bytes=receipt['request_bytes'],prompt_sha256=receipt['prompt_sha256'],unchanged_original_prompt=True,source_task_count=1,complete_source_tasks=0,second_frozen_task='not_started_after_first_failure',elapsed_seconds=receipt['elapsed_seconds'],connect_seconds=receipt['connect_seconds'],headers_seconds=receipt['response_headers_seconds'],http_status=receipt['http_status'],actual_models=receipt['actual_models'],finish_reasons=receipt['finish_reasons'],done_marker=receipt['done_marker'],network_eof=receipt['network_eof'],refusal_observed=receipt['refusal_observed'],client_error=receipt.get('error'),visible_body_characters=receipt['text_characters'],usage=receipt['usage'],visible_reported_tokens=receipt['visible_reported_tokens'],usage_known=False,model_limits_advertised=limits.get('advertised_limits'),connection_observation='direct TLS/SSE remained active and reached clean DONE/EOF; not a network/refusal failure',delivery_observation='24576 completion-token setting was exhausted, 24573 reported reasoning tokens; no final analysis',effect='not evaluable; no candidate adoption',stability='one incomplete source attempt does not establish repeatability or reliable full delivery',automatic_retries=0,new_request_ids_reused=False,evidence_sha256={n:sha(M/n) for n in ['prompt.md','receipt.json','model_limits.json']})
dump(H/'model_delivery_review.json',report)
matrix=read(H/'review_matrix.json');matrix['stage']='bounded_method_review_complete';matrix['new_model_semantics']='no complete final; not adopted';matrix['stage_result']='method card and support boundaries archived; no real-platform/full-family/independent claim';dump(H/'review_matrix.json',matrix)
stability='''# 新模型大源码调用观察

本轮按用户授权，冻结两份不同旧任务及14项人工内容核验问题；第一份172602字节prompt逐字复用，未加入既有答案或删改源码。第二份408232字节任务已准备，未发请求。

Kimi-K3.1-Pro-HighSpeed第一份请求在0.219秒建连、19.188秒取得HTTP200，持续SSE到463.735秒结束，实际模型匹配、DONE/EOF齐全。结束原因为length，不是网络超时或refusal。平台报告prompt53812、completion24576、其中reasoning24573、total78388 token；未取得正文。这些是平台可见计数，不是完整账单。

本次证明直连可维持长请求到结束，但未实现大源码分析完整交付。原K3客户端沿用的24576输出上限不足以容纳这次新模型推理加正文；用户每次独立1M额度不等于API max_tokens、上下文或推理上限。平台/models目录没有声明相关限制，不能自行声称支持某个更大上限。

按调用前冻结的失败即停规则，未自动重试、改写请求、切模型或发送第二任务。6项缓存语义问题无完整正文可评分；8项全链问题未调用。不能据此宣称模型内容正确、错误或比旧模型更好。已读开发案例也不构成独立评价。

后续大请求先核平台可接受的输出/推理参数并显式登记；本次失败任务保持原样停点。后续重试需要用户新指示。virtio方法评审继续依据已核源码和已有实验，单列模型未交付。
'''
(H/'model_stability.md').write_text(stability,encoding='utf-8');(M/'README.md').write_text(stability,encoding='utf-8')
backend=R/'linux_bug_analyze/analysis_out/current_analysis_backend.json';b=read(backend);p=b['primary_analysis'];p.setdefault('attempt_history',[]).append(p['latest_attempt']);p['latest_attempt']=dict(date='2026-10-27',scope='frozen 172602-byte cache-boundary source task',status=receipt['status'],receipt='模型调用测试/2026-10-27/virtio_k31_cache_large/receipt.json',actual_model=receipt['model'],stop_reason='length',visible_reported_tokens=receipt['visible_reported_tokens'],automatic_retry=False)
p['source_analysis_delivery_status']='incomplete_length_no_body_20261027';p['large_source_ready']=False;p['large_source_constraint']='Observed completion cap24576 consumed; provider catalog advertises no limits; verify explicit output/reasoning parameters before future large task';p['semantic_review']='New-model large source task no body, adoption0; prior K3 and manual/local evidence preserved';dump(backend,b)
ag=R/'AGENTS.md';s=ag.read_text(encoding='utf-8');line='- 2026-10-27新模型大源码实测：172602字节prompt，463.735秒正常连接到DONE/EOF，但finish_reason=length、输出上限24576几乎全用于推理，无分析正文。大源码尚未验证完整交付；后续大请求先核平台可接受的输出/推理参数并显式登记，不将用户独立1M额度当API实际上限。本次失败不自动重试，旧记录保留。\n';needle='- 出现refusal或调用失败时保留记录'
if line not in s:s=s.replace(needle,line+needle);ag.write_text(s,encoding='utf-8')
section='''## 10月27日 最新进展：virtio限定方法评审完成；新模型大源码触输出上限

按待办完成virtio_input事件缓冲的有界方法评审，形成method_card、11项review_matrix和四机制比较。源码依据→提供者/实际目标→维护范围→对象/阶段→可观察判定逐层登记；区分组外隔离与组内事件所有权、请求字节与维护包络、map成功与实际发布、callback顺序与CPU可见性。阶段结果是限定开发方法可归档，不是virtio/DMA家族完整验证。

19份固定源码重新核Git blob，73项工件登记SHA，25个已有记录SHA逐项核验；旧add/缓存两限定判定器对266份原始记录及旧控制回验通过。没有重跑这些内核/编译/设备实验，旧记录不计本轮新样本；哈希工件数不当独立证据数。方法比较表指出CPU集合/期限、Btrfs数值裁剪、SMMU编码/提交与DMA目标/影响范围各有专用语义，共同证据组织不能替代接口适配。未建立统一检查器，规范/用途、对象角色、准入和关系仍人工提供。

评审把缺口分开：实际ABI/基址、协商后端/一致性、有效维护信息、设备DMA与并发时段会阻止真实平台判定；packed/IN_ORDER、完整IOMMU/custom及关闭生命周期不在当前限定支持域，扩展主张时再补；自动要求推导和独立评价仍缺。whole_path保持insufficient。不能仅凭布局或bounce就判整个接口满足，也不将缺证当正常。表示/R3暂缓、VT-d后置、SMMU开放缺口不变。

同时按用户要求核新模型的大源码稳定性与效果：调用前冻结两份旧prompt及14项内容问题。先以Kimi-K3.1-Pro-HighSpeed原样发送172602字节缓存任务，0.219秒连接、19.188秒HTTP200，463.735秒收到DONE/EOF；模型名准确、无refusal/传输错误，停止原因length。平台报告prompt53812、completion24576（reasoning24573）、total78388，无正文。因此长连接完成，但分析交付失败，内容效果无法评价，采纳候选0，不称稳定或比旧模型更好。独立1M额度不是24576 API输出限制；目录GET未提供实际模型上限，不猜更大值已受支持。

按事前失败即停规则，第二份408232字节全链prompt只准备未发送；无自动改写/重试或回退。原K3缓存超时和旧成功任务均保留。14项内容检查中6项无完整结果可评、8项未调用，不报告准确率。主模型仍Kimi-K3.1-Pro-HighSpeed；后续大请求先核平台输出/推理设置并显式登记，失败任务保持停点，不能偷偷重发。

下一项：转入既有CPU信息导出的来源资格与版本化用途政策，先重构政策/来源/配置的判定关系及正常资格，再做组件回验和横向比较。next_source_qualification_scope仅为准备，未开展新模型/启动。特别保留旧文档允许fallback、修复双原生来源成组政策不能追认为旧ABI禁令，以及静态配置不能替运行补有效来源的边界。大模型调用参数问题单独跟踪，不阻断不依赖新模型交付的已有材料复核。

本轮统计：1次新模型源码任务（未完整交付）、1次只读模型目录GET，0次新编译/内核或QEMU运行、0个新Linux缺陷，独立正例/正常仍0/0；78388为可见平台计数，usage_known=false，不当完整账单。证据linux_bug_analyze/experiments/case_taxonomy/virtio_review_20261027/（frozen_plan、evidence_index、archive_replay、method_card、review_matrix、mechanism_comparison、model_delivery_review、semantic_review、model_stability、next_source_qualification_scope）；模型原件模型调用测试/2026-10-27/virtio_k31_cache_large/，第二任务未发见virtio_k31_chain_large/not_started.json。

已在接口验证后续规划.md登记DMA限定用途阶段评审及剩余缺口；当日日志、待办、进展、交接同轮更新，三份WSL镜像以notes_sync收据为准，Word未改。

以下为历史记录，以本节及用户最新指示为准。

'''
(H/'README.md').write_text('# virtio_input DMA限定方法评审与新模型大源码观察\n\n'+section,encoding='utf-8')
planning=R/'接口验证后续规划.md';s=planning.read_text(encoding='utf-8');s=s.replace('当前深入分析，不结项','限定开发方法阶段评审完成；真实平台及全家族验证未完成');s=s.replace('实际后端与平台、架构缓存维护边界、其他队列布局及完整生命周期','实际后端/ABI/平台维护信息和并发效果；其他队列布局、完整生命周期及独立评价')
entry='| 2026-10-27 | DMA／virtio_input事件缓冲限定判定方法 | 阶段评审完成：规范/目标/维护范围/对象阶段/观察能力11项矩阵；linux_bug_analyze/experiments/case_taxonomy/virtio_review_20261027/ | whole_path仍不足；真实平台/并发和独立评价未完成。新模型大源码length无正文，候选0；语义与准入仍人工 |\n\n'
s=s.replace('\n\n## 当前执行顺序','\n'+entry+'## 当前执行顺序')
a=s.index('## 当前执行顺序');z=s.find('\n## ',a+4)
new='''## 当前执行顺序

DMA/virtio限定方法阶段评审已归档，真实平台缺口继续挂账。下一项整理CPU信息导出的来源资格与版本化用途政策，限定已有die等开发材料，核政策依据、实际配置及正常路径，比较可复用部分与专用适配。next_source_qualification_scope只作下一项范围，尚未执行。表示/R3暂缓、VT-d后置不变；不自动启动新内核矩阵。

新主模型大源码首测连接完成但触24576输出上限，没有正文；第二冻结任务未调用。后续大请求先核平台实际输出/推理参数并显式登记，保留本次失败停点，无自动重试。平台目录没有声明上限，用户独立1M额度不能直接当API上限。
'''
s=s[:a]+new+(s[z:] if z!=-1 else '')
planning.write_text(s,encoding='utf-8')
before=read(H/'notes_before.json')['before_sha256'];after={}
for name,digest in before.items():
 p=R/name
 if sha(p)!=digest:raise RuntimeError('working note changed '+name)
 title,_,body=p.read_text(encoding='utf-8').partition('\n');p.write_text(title+'\n\n'+section+body.lstrip('\n'),encoding='utf-8');after[name]=sha(p)
dump(H/'notes_update.json',dict(before_sha256=before,after_sha256=after))
with (R/'日志/2026-10-27.md').open('a',encoding='utf-8') as f:f.write('\n\n'+section)
print(json.dumps(dict(bounded_review='complete',whole_path='insufficient',source_model_tasks=1,source_deliveries=0,stop='length',second_task='not_started')))
