from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;E=H.parent;R=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
review=E/'smmu_chain_20261026/model_review.json';old=json.loads(review.read_text(encoding='utf-8'));assert len(old['dispositions'])==10
updates={
'O1':('smmu_queue_20261026/audit.json','规范及真实模型队列已有对照；QEMU不识别该保留组合，不能作真值'),
'O2':('smmu_range_bounds_20261026/scope_audit.json','已查入口阈值/哨兵，巨大范围不直接可达；其余调用入口和地址上界不完整'),
'O3':('smmu_binding_20261026/granule_results.json','原粒度收敛函数条件证据；实际allocator和同域身份仍需运行证明'),
'O4':('smmu_chain_20261026/chain_results.json','原SVA包装器leaf=false及TTL规则；实际CPU页表层级未观测'),
'O5':('smmu_platform_20261026/platform_admission.json','注册与上游范围补证；当前QEMU SSID0，SVA真实绑定受阻'),
'O6':('smmu_lifecycle_20261026/evidence_packet.json','双domain角色、stage和事务有条件证据；并发/同对象全生命周期不足'),
'O7':('smmu_platform_20261026/stride_results.json','CPU块stride补证不等于io-pgtable unmap walker已执行；后者仍缺'),
'O8':('smmu_queue_20261026/results.json','仿真队列消费证据已有；未建立翻译缓存及真实DMA，不证明失效效果'),
'O9':('smmu_stage_20261026/address_results.json','非块对齐地址已补；通用munmap触发推断已收窄，leaf gather未验证'),
'O10':('smmu_queue_20261026/source_and_binary.json','规范+模型实测分层；物理硬件、完整errata及独立评价仍缺')}
save('obligations_update.json',dict(original_review_sha256=sha(review),main_model_called_this_round=False,items=[dict(id=k,evidence=str((E/p).relative_to(R)),sha256=sha(E/p),assessment=v,status='partial_not_closed') for k,(p,v) in updates.items()]))
p=E/'smmu_range_bounds_20261026/source/mm__memory.c';lines=p.read_text(encoding='utf-8').splitlines();start=next(i for i,l in enumerate(lines) if l.startswith('static vm_fault_t do_wp_page('));end=next(i for i in range(start,len(lines)) if 'vmf->page = vm_normal_page' in lines[i]);snippet='\n'.join(lines[start:end])
save('single_page_trigger.json',dict(source=str(p.relative_to(R)),sha256=sha(p),line=start+1,excerpt=snippet,conditions=['entered do_wp_page under caller protection and lock assumptions','!unshare','userfaultfd_pte_wp branch did not return handle_userfault','userfaultfd_wp(vma)','mm_tlb_flush_pending(mm)'],manual=True,not_exhaustive_callsites=True,runtime='not observed',downstream='flush_tlb_page -> page_nosync -> __flush_tlb_page_nosync -> arch notifier; prior original-function probe covers latter only',additional_conditions=['same mm registered notifier','successful SVA/CD binding','BTM0 for explicit SMMU TLBI','RIL1 for range encoding','supported translation domain and granule']))
body='''## 10月26日 最新进展：SMMU专用判定程序与义务复核

新增checker.py，输入为已登记布局的原始qtest请求/回复及命令字，重算字段规则、RAM逐字一致性、使能与队列状态；未读取上一轮最终判定作为答案。10份原始记录回放：3组保留组合违规，5组历史对照仅通过该条规则，2组控制不适用；9组队列消费、1组错误。whole_path全部不足。没有统一其他接口入口，也没有自动提取契约。

加入4种合成证据控制：缺命令字、缺回复、命令字与RAM读回矛盾、缺规范依据。第一轮14项执行后明确区分encoding（提供的字值）与observed_encoding（完整一致转录关联的字值），第二版再执行同10+4项；四个控制的observed_encoding均不足，不因修改输入字值或模拟器消费而放行。第一版结果保留，当前采用results_v2/controls_v2。总28项程序判定执行不是28个案例或独立样本；规则与适配布局仍人工登记，观测器资格沿用已核模型限制，不接受调用者声称qualified直接提升。

单页触发补证：mm/memory.c的do_wp_page分支需非unshare、未在userfaultfd_pte_wp分支提前返回、userfaultfd_wp且mm_tlb_flush_pending，入口还有调用者锁/保护检查假设。不能把普通写缺页直接当成单页SMMU触发。single_page_trigger.json存源码SHA/行号/原片段及人工条件；不是全调用点自动提取或真实用户程序复现。还需同mm注册、成功绑定/CD、BTM/RIL、翻译域粒度等条件。

把原主分析10项义务逐项映射到后续证据和仍缺项，写obligations_update.json；不修改原模型回答，不将10项标为全部闭合。特别区分CPU块stride与io-pgtable实际unmap walker，前者通过不能代替后者。队列已有模型观测，但真实翻译缓存/设备失效效果及同对象生命周期仍不足。

下一项：针对仍影响判定的O7，核实际io-pgtable unmap→walk失效的范围/粒度/释放顺序，优先复用固定源码原函数并保留分配/页表访问替身边界；不要继续堆SVA任意页数或QEMU消费矩阵。SVA完整运行保留SSID平台缺口；SMMU不结项，virtio随后，表示接口/R3暂缓、VT-d后置不变。

统计：本轮2轮各10份已读原始记录+4个合成控制，共28项判定执行；新编译、模型/内核启动、设备操作、项目主分析、新缺陷均0，独立正例/正常0/0。证据linux_bug_analyze/experiments/case_taxonomy/smmu_decision_20261026/（checker、results_v2、controls_v2、input_manifest、single_page_trigger、obligations_update）。Word未改；日志和三份持续文档同轮维护，WSL镜像以notes_sync.json为准。

以下为历史记录，以本节及用户最新指示为准。

'''
(H/'README.md').write_text('# SMMU专用判定方法，开发中\n\n'+body+'''\n## 当前方法边界

1. 人工登记版本、规范、入口条件及观测适配布局。input_manifest保留证据SHA；不是自动语义推导。
2. checker.assess计算所给NH_VA字值的保留编码规则；无依据则不足，其他opcode不适用该规则。
3. 逐请求对齐回复，核RAM写入/读回、固定队列布局、CR0ACK和生产者。完整一致时才给observed_encoding；缺失或矛盾拒绝关联到实际提交。
4. 独立输出模型消费/错误，不把消费和SYNC当DMA效果。该模型已不具备保留组合判定资格。
5. 不跨实验拼接同一runtime对象；绑定、平台和设备效果缺证保持不足。

可迁移部分：证据身份、输入一致性与缺证层次。专用部分：NH_VA字段规则、qtest布局和触发语义。仍需支持更多输入来源、外部适用条件核验及独立评价，不能将本脚本称为完整自动检测方法。
''',encoding='utf-8')
before=json.loads((H/'notes_before.json').read_text(encoding='utf-8'))['before_sha256'];after={}
for n,d in before.items():
 p=R/n;assert sha(p)==d
 title,rest=p.read_text(encoding='utf-8').split('\n',1);p.write_text(title+'\n\n'+body+rest.lstrip(),encoding='utf-8');after[n]=sha(p)
save('notes_update.json',dict(before_sha256=before,after_sha256=after))
with (R/'日志/2026-10-26.md').open('a',encoding='utf-8') as f:f.write('\n'+body)
save('delivery_manifest.json',{p.name:sha(p) for p in H.iterdir() if p.is_file() and p.name not in ['delivery_manifest.json','notes_sync.json']})
print('SMMU decision method, trigger conditions and 10 obligation dispositions recorded.')
