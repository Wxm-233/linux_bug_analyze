from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;R=H.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if (H/'notes_update.json').exists():raise RuntimeError('preserve finished round')
rows=json.loads((H/'results.json').read_text());bounce=json.loads((H/'bounce_results.json').read_text());failed=json.loads((H/'results_failed_indirect_stub.json').read_text())
audit=json.loads((H/'audit.json').read_text());controls=json.loads((H/'controls.json').read_text())
if len(rows)!=54 or len(bounce)!=27 or any(r['code'] for r in rows+bounce):raise RuntimeError('incomplete results')
if len(audit)!=54 or any(a['status']!='observed_object_publication_recycle' for a in audit) or len(controls)!=6 or any(a['result']['status']!='rejected' for a in controls):raise RuntimeError('incomplete audit')
dump(H/'method_update.json',{
 'source_parent':'db191ba0c8564ff84877e5b1c9553e991feca239','scope':'ordinary split, single 8-byte input SG, no premapping, attrs0; lowmem bounce copy primitive separately',
 'original_functions':{'chain':19,'bounce':3},
 'counts':{'successful_compiles':3,'failed_compiles':0,'extractor_failures':1,'final_chain_executions':54,'final_bounce_executions':27,'prior_chain_executions':len(failed),'prior_script_aborts':sum(r['code']!=0 for r in failed),'trace_assess_calls':60,'model_calls':0,'kernel_boots':0,'new_kernel_defects':0,'independent_positive':0,'independent_normal':0},
 'evidence_sha256':{n:sha(H/n) for n in ['functions.json','build.json','build_before_stub_fix.json','results.json','results_failed_indirect_stub.json','checker.py','audit.json','controls.json','bounce_functions.json','bounce_build.json','bounce_results.json']},
 'verified_local_relations':['failed map produces no avail index publication','descriptor/token/avail set before barrier callback, index advances afterward','object matched across simulated used, unmap, token, CPU read, re-add','single SG never allocates indirect table, but feature-enabled detach visits empty cleanup','copyback copies entire mapped range; initialized unwritten bytes survive simulated partial device writes','sync then unmap SKIP avoids second copy; SKIP-only suppresses copy'],
 'manual_dependencies':['pinned source selection','ordinary split dispatcher adapter','requirements/state machine','synthetic backend and physical translation','admission and interpretation'],
 'insufficient':['real device DMA target/effect','architecture cache maintenance','hardware ordering','packed/in-order','actual IRQ/RCU or concurrency','whole path','independent generalization']})
section='''## 10月27日 最新进展：virtio原入队发布—回收联动与bounce回写

继续既定virtio任务，本轮复用已核固定父版源码，未新增模型调用。提取19个原函数接通普通split、非IN_ORDER、单8字节输入SG的map→描述符/avail发布→模拟used→detach/unmap→CPU读取→重新add。普通add_inbuf原入口使用premapped=false、attr=0；layout分派固定为该split适配器，DMA后端、SG/类型、锁/屏障及设备完成为替身。54组最终执行覆盖9情形×绕过/标准API/自定义API×indirect特性开关；不是54个设备配置或案例。

原add实际生成：broken时EIO、容量不足时ENOSPC均在映射前；标准/自定义后端映射失败后返回ENOMEM且不发布avail，不消耗空闲描述符。正常map后先设置描述符/token/avail数组，再调用屏障，随后推进avail索引；这里只观测C执行和屏障替身，不证明硬件内存序。正常回收后重投在本脚手架无需新增容量；上轮人为注入ENOSPC不再被当作普通重投真实可达的证明。

首个对象重投映射失败时原驱动继续第二对象，失败对象没有再次发布；两对象均失败时仅本轮有限路径内不再有可消费项。额外恢复场景由测试显式再次调用queue函数后成功，不声称原驱动自带恢复。两轮成功场景保留对象代次关系。broken在回调内变化是构造控制，不升级关闭竞态。队列状态/空闲计数与原描述符实际发布联系已补，未运行真实DMA。

本轮纠正脚手架：首次提取因unsigned返回类型遗漏在编译前停止；之后19组运行被abort，原因是把indirect清理整个函数误设为不可达。改用原detach_indirect_split后54组全部通过。启用indirect特性且单SG不分配间接表，但回收仍进入清理函数并因NULL表指针返回；“不分配间接表”不等于“清理函数不可达”。初始脚本、54份旧结果（35成功/19中止）及其构建收据保留，不算Linux缺陷或独立控制。

另提取swiotlb_bounce、CPU sync和unmap三个原函数，27组低端内存拷贝实验覆盖3种回写方式×3偏移×0/4/8字节模拟设备写入。原拷贝确实读写宿主字节；合成pool/slot/物理地址、对齐和释放均为替身，高端内存/分配器未执行。先按原map路径所用的拷贝原语预填8字节，再模拟写入；正常unmap或先CPU sync后SKIP unmap均回写完整8字节一次，SKIP-only控制不回写。短写未覆盖字节保留原值，映射范围外字节不变。此证据是CPU拷贝范围，不代表cache line安全、实际DMA或并发正确。

新限定检查器以对象状态、映射结果、发布索引和回收顺序关联54份轨迹，6份篡改控制（发布前缺屏障顺序、错对象token、缺unmap、未完成先复用、失败却已发布、缺结束）全部拒判。合计60次assess调用。该检查器仍仅支持本轮登记语义；真实CPU可见性、设备效果和whole_path均为不足。语义规则/对象、布局准入及适配器人工提供，未建立统一自动推导方法。

统计：3次成功编译（旧脚手架1、修正链1、bounce1）、0次编译失败、1次编译前提取失败；最终81次程序执行通过，另54次旧脚手架执行单列。82次事件读取、136次发布是54份最终链轨迹内部事件，不当案例数。无模型请求、内核/QEMU启动、真实设备操作或新Linux缺陷，独立正例/正常仍0/0。证据linux_bug_analyze/experiments/case_taxonomy/virtio_add_recycle_20261027/（functions、build、results、audit/controls、bounce_functions/results、method_update、README及失败原件）。

下一项：核固定版本ARM64缓存维护原语的实际范围与边界操作，再把direct/bounce维护对象与事件/元数据的所有权窗口对应；只补影响判定的路径。实际平台coherent/后端/维护粒度及packed/IN_ORDER仍未闭合，virtio保持进行中；随后按方法提纲做有界评审，不能将局部执行当完整家族验证。SMMU缺口、表示/R3暂缓、VT-d后置不变；后续主分析仍Kimi。已更新《接口验证后续规划.md》的子阶段记录，本轮非完整接口结项。日志、待办、进展、交接同轮维护，三份WSL镜像以notes_sync回执为准，Word未改。

以下为历史记录，以本节及用户最新指示为准。

'''
(H/'README.md').write_text('# virtio原入队发布与回收、低端内存bounce回写\n\n'+section,encoding='utf-8')
plan=R/'接口验证后续规划.md';s=plan.read_text(encoding='utf-8')
s=s.replace('维护日期：2026-10-26。','维护日期：2026-10-27。')
s=s.replace('本轮补PCI modern reset顺序','已补PCI modern reset及原add发布/回收、低端内存bounce回写')
s=s.replace('原add真实失败/发布路径、copyback与缓存维护边界、实际平台、其他队列布局','实际后端与平台、架构缓存维护边界、其他队列布局及完整生命周期')
marker='## 当前执行顺序'
entry='| 2026-10-27 | DMA／virtio_input普通split发布回收及bounce回写 | 子任务完成：54组原函数链及27组低端内存拷贝；linux_bug_analyze/experiments/case_taxonomy/virtio_add_recycle_20261027/ | 整个接口分析仍进行中；6种轨迹篡改拒判；缓存维护、真实设备、其他布局不足，规则与映射/观测适配人工提供 |\n\n'
s=s.replace(marker,entry+marker)
s=s.replace('原add错误生成/成功发布→后端copyback与维护范围→对象所有权与适用平台证据→方法评审','固定版架构缓存维护范围及边界→direct/bounce对象所有权与适用平台证据→方法评审（原add与低端内存copyback局部证据已补，真实设备仍缺）')
# Keep the new row in the existing table: remove the blank directly above it.
s=s.replace('\n\n'+entry,'\n'+entry)
plan.write_text(s,encoding='utf-8')
before=json.loads((H/'notes_before.json').read_text(encoding='utf-8'))['before_sha256'];after={}
for n,digest in before.items():
 p=R/n
 if sha(p)!=digest:raise RuntimeError('working note changed '+n)
 title,_,body=p.read_text(encoding='utf-8').partition('\n');p.write_text(title+'\n\n'+section+body.lstrip('\n'),encoding='utf-8');after[n]=sha(p)
dump(H/'notes_update.json',dict(before_sha256=before,after_sha256=after))
log=R/'日志/2026-10-27.md'
with log.open('a',encoding='utf-8') as f:
 if log.stat().st_size==0:f.write('# 2026-10-27 实验日志\n')
 f.write('\n\n'+section)
print('round evidence, plan, three working notes and daily log updated')
