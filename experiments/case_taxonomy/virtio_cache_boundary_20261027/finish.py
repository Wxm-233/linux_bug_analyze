from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;R=H.parents[3];M=R/'模型调用测试/2026-10-27/virtio_cache_boundaries'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if (H/'notes_update.json').exists():raise RuntimeError('preserve finished round')
receipt=json.loads((M/'receipt.json').read_text());rows=json.loads((H/'results.json').read_text());bridge=json.loads((H/'layout_trace_results.json').read_text());integrated=json.loads((H/'integrated_results.json').read_text());audit=json.loads((H/'audit.json').read_text());controls=json.loads((H/'controls.json').read_text())
if len(rows)!=168 or len(bridge)!=32 or len(integrated)!=16 or any(r['code'] for r in rows+bridge+integrated):raise RuntimeError('incomplete experiment')
if len(audit['rows'])!=168 or any(r['status']=='rejected' for r in audit['rows']) or any(r['result']['status']!='rejected' for r in controls):raise RuntimeError('incomplete audit')
dump(H/'model_status.json',dict(status=receipt['status'],elapsed_seconds=receipt['elapsed_seconds'],actual_models=receipt['actual_models'],refusal_observed=receipt['refusal_observed'],error=receipt.get('error'),visible_reported_tokens=receipt['visible_reported_tokens'],usage_known=False,final_characters=receipt['final_characters'],automatic_retry=False,adopted_candidates=0,receipt_sha256=sha(M/'receipt.json'),default_route_changed_this_round=False,runner_historical_default_route_changed_field='generic template metadata, not a new route mutation',note='Timeout without response model/body/usage; API acceptance and charge not established; preserve failure, no retry'))
backend=R/'linux_bug_analyze/analysis_out/current_analysis_backend.json';b=json.loads(backend.read_text(encoding='utf-8'))
b['primary_analysis']['latest_attempt']=dict(date='2026-10-27',scope='virtio fixed-source cache boundaries',status=receipt['status'],receipt='模型调用测试/2026-10-27/virtio_cache_boundaries/receipt.json',error_type='TimeoutError',actual_model_unconfirmed=True,semantic_adoption=0,automatic_retry=False)
# latest_receipt and connectivity_status describe the earlier successful task,
# retained alongside this failed attempt; do not rewrite historical success.
dump(backend,b)
dump(H/'method_update.json',{
 'scope':'fixed parent ARM64 boundary control flow; ordinary FROM_DEVICE direct/bounce target conditions',
 'counts':dict(new_pinned_sources=4,successful_aarch64_builds=4,failed_builds=1,general_qemu_user_executions=168,conditional_layout_qemu_user_executions=32,integrated_qemu_user_executions=16,total_qemu_user_executions=216,assess_calls=206,cwg_equal_pairs=84,model_tasks=1,model_completed=0,new_kernel_defects=0,independent_positive=0,independent_normal=0),
 'equations':{'line_bytes':'4 << effective_CTR_DminLine','envelope':'[floor(start/L)*L, ceil((start+size)/L)*L) for registered positive non-overflowing input','partial_invalidation':'partial end first civac; partial start civac; aligned/interior lines ivac; same line may occur twice','clean_alternative':'cvac normally; civac in registered clean-cache workaround projection'},
 'supported_relations':['recorded operation sequence/envelope with DC/DSB fixtures','DminLine determines loop stride; changing only CWG fixture does not change this primitive','host layout first/last overlap conditional on base/ABI','direct original physical object vs bounce physical object cache target before copyback fixture'],
 'manual_dependencies':['authority and semantic use','macro/function extraction','read_ctr/effective value fixture','static clean-cache alternative projection','DC/DSB log adapter and scratch registers','host ABI/base admission','backend and ownership interpretation'],
 'insufficient':['hardware cache effect','real CTR/effective system CTR admission','real ARM64 ABI/base','allocator and bounce target admission','actual copyback in integrated program','concurrency and ownership stability','other DMA backends and queue layouts','whole_path','independent generalization'],
 'evidence_sha256':{n:sha(H/n) for n in ['sources.json','functions.json','builds.json','builds_failed_alternative_macro.json','results.json','audit.py','audit.json','controls.json','layout_trace_results.json','layout_bridge.json','integrated_functions.json','integrated_builds.json','integrated_results.json','model_status.json']}})
section='''## 10月27日 最新进展：ARM64维护边界与direct/bounce对象补证，Kimi补充任务超时

按待办新增固定父版db191ba0c8564ff84877e5b1c9553e991feca239的cache.S、assembler.h、cache.h和cacheflush.h，均核Git blob。原C包装、两段缓存汇编函数体及四个宏接入AArch64执行；read_ctr返回值、DC/DSB和异常表为替身，clean-cache alternative按开/关静态投影，不运行内核动态补丁或真实缓存指令。首轮替身把GAS条件拆在多个macro中导致编译失败，失败脚本/收据保留；改为在原workaround宏内静态投影后通过，原源码不改。

四次成功AArch64构建，216次QEMU用户态执行：168组边界/方向/CTR/clean-cache对照、32组旧宿主布局接线、16组direct/swiotlb_map/CPU同步解除映射与ARM64边界联动。不是216次内核启动、真实缓存操作或独立案例。168与32条记录审核及6份篡改控制共206次assess；16条联动另按地址/顺序核验。84组只变CWG的成对记录相同。

判定事实：dcache_line_size从read_ctr提供的有效CTR中取DminLine[19:16]，步长4<<DminLine；CWG、ARCH_DMA_MINALIGN=128与ARCH_KMALLOC_MINALIGN=8各有职责，不能混为实际维护步长。read_ctr可能取系统安全值而非本CPU原始CTR；本轮仅构造DminLine=4/5、CWG=4/5，不声称所有组合都是合法实机。clean按覆盖区间逐行cvac；clean-cache workaround改为civac。invalidate先处理部分尾行，再处理首行和中间行：部分行civac、完整/对齐循环ivac，末尾dsb。8字节首尾同处未对齐行时，该地址可出现两次civac；这是操作序列，不是已证明的损坏或重复回写故障。CPU TO_DEVICE同步原包装直接返回。

维护范围接线：在固定旧宿主ABI和基址0x10000假设下，旧事件组首/尾8字节的维护行在64/128两种步长均越过组边界，尾行含lock；修复宿主布局的首尾不越界。此项不等于真实ARM64布局或设备目标；组内其他事件仍可同行，其各自映射/消费阶段需要单独判定。不能从整组隔离推导内部所有权已经正确。

16条原direct与swiotlb_map联动记录中，attrs0的非coherent direct维护原缓冲，force-bounce维护所给bounce地址，先完成CPU维护序列再调用copyback替身，最后释放替身；coherent控制不调用这段架构维护。pool分配、翻译、copyback/释放为标签与回调，不能把上轮独立字节拷贝结果冒充本程序实际DMA效果。该补证将“维护哪个对象/覆盖哪些行/何时发生”分开登记，硬件效果及whole_path继续不足。

本轮Kimi新固定源码补充任务181.234秒TimeoutError，actual_models为空，无正文、stop/DONE/EOF或用量；无refusal字段事件。不是模型拒答，也无法确认服务端是否接受/计费。原请求及失败收据保留在模型调用测试/2026-10-27/virtio_cache_boundaries/；采纳候选0，无自动改写或重试。旧10/26成功任务保留，当前默认仍Kimi；本轮程序/人工源码复核不写成Kimi完成。每调用1M口径不变，未知费用不记为0。

下一项：对virtio限定用途做有界方法评审，汇总规范依据→对象/后端→维护范围→发布/回收阶段→可观察判定，并列出真实平台、并发、packed/IN_ORDER及独立评价缺口，明确哪些缺口改变判定、哪些应挂账；不再无限扩同类组合。Kimi本次失败停点保留，不自动重试。接口仍进行中，尚无完整独立验证；表示/R3暂缓、VT-d后置、SMMU缺口保留。

本轮新Linux缺陷0，独立正例/正常0/0。证据linux_bug_analyze/experiments/case_taxonomy/virtio_cache_boundary_20261027/（sources、functions、results/audit、controls、layout_bridge、integrated_results、model_status、method_update、README及失败原件）。已在接口验证后续规划.md登记本子阶段；日志、待办、进展、交接同轮更新，三份WSL镜像以notes_sync回执为准；Word未改。

以下为历史记录，以本节及用户最新指示为准。

'''
(H/'README.md').write_text('# ARM64维护边界与DMA对象：限定执行证据\n\n'+section,encoding='utf-8')
plan=R/'接口验证后续规划.md';s=plan.read_text(encoding='utf-8');s=s.replace('固定版架构缓存维护范围及边界→direct/bounce对象所有权与适用平台证据→方法评审（原add与低端内存copyback局部证据已补，真实设备仍缺）','virtio限定用途方法评审→按会改变判定的缺口决定补证或挂账（原add、低端内存copyback、ARM64边界及direct/bounce对象局部证据已补，真实设备/并发仍缺）')
row='| 2026-10-27 | DMA／ARM64维护边界与virtio映射对象 | 子任务完成：216次带DC/DSB日志替身的AArch64 QEMU用户态执行；linux_bug_analyze/experiments/case_taxonomy/virtio_cache_boundary_20261027/ | DminLine/CWG分开；宿主布局接线有条件；Kimi补充任务超时、候选0，不自动重试；真实缓存效果与平台仍不足，下一项有界方法评审 |\n\n'
s=s.replace('\n\n## 当前执行顺序','\n'+row+'## 当前执行顺序');plan.write_text(s,encoding='utf-8')
before=json.loads((H/'notes_before.json').read_text(encoding='utf-8'))['before_sha256'];after={}
for n,d in before.items():
 p=R/n
 if sha(p)!=d:raise RuntimeError('working note changed '+n)
 title,_,body=p.read_text(encoding='utf-8').partition('\n');p.write_text(title+'\n\n'+section+body.lstrip('\n'),encoding='utf-8');after[n]=sha(p)
dump(H/'notes_update.json',dict(before_sha256=before,after_sha256=after))
with (R/'日志/2026-10-27.md').open('a',encoding='utf-8') as f:f.write('\n\n'+section)
print('evidence, route attempt, plan, notes and log updated')
