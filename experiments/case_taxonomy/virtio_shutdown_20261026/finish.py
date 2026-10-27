from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;R=H.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
plan='''# 接口验证后续规划

维护日期：2026-10-26。本文按用户要求作为接口家族总览及阶段完成登记入口；具体当前任务以《当前代办.md》为准。原规划完整保存在linux_bug_analyze/experiments/case_taxonomy/virtio_shutdown_20261026/plan_before.md，其旧模型、预算、挂载状态和排程不再作为当前指示。

## 组织层次与统计口径

区分四层：接口家族→具体接口及公共用途→案例载体→判定机制。Btrfs、virtio_input等是案例载体，不是与DMA同层的大类；集合覆盖、期限、来源资格等是机制。家族允许重叠，以下不是接口普查或完备分类，不据行数统计缺陷或已完成接口数量。

最终目标仍为统一入口、统一契约表示、统一证据与判定流程，允许不同事实提取及观测适配器。当前先积累可复用的判定机制，不急于拼装统一检查器。后续源码主分析Kimi-K3，每调用独立1M；模型候选需复核。详见AGENTS.md和《最终研究目标与阶段推进原则.md》。

## 接口家族与验证计划

| 家族/边界 | 具体用途与案例载体 | 已有证据与机制 | 未完成与后续计划 | 当前状态 |
| --- | --- | --- | --- | --- |
| CPU拓扑、枚举与属性接口 | s390拓扑准备、die信息导出、SPARC等身份/范围 | 历史x86/s390运行、局部函数与组件；集合覆盖、准备资格/期限、来源资格、编号域/数量限制 | 拓扑精确消费与锁对象/稳定窗口；导出政策适用范围；身份路径真实启动及正常资格。不同用途分别登记 | 拓扑阶段方法已整理；其他用途有不同深度材料，非全家族完成 |
| 内存几何与分配约束接口 | Btrfs页/磁盘几何到选项及文件行为；shmem页几何 | Btrfs真实历史挂载、裁剪操作数与持久布局；数值一致、准备期限及用途门禁；shmem旧ARM64/64K内部链 | Btrfs同对象同期限的权威参考；shmem修复/正常配对。页大小配置不直接等于CPU架构 | Btrfs阶段方法已整理，缺口挂账；shmem R3暂缓 |
| DMA映射、同步与缓冲区所有权接口 | virtio_input事件缓冲→virtqueue→DMA后端→回收重投 | 布局、后端分支、direct/bounce谓词、普通split回收时序及错误轨迹检查；本轮补PCI modern reset顺序 | 原add真实失败/发布路径、copyback与缓存维护边界、实际平台、其他队列布局；不把字段对齐或回调调用当完整安全证明 | 当前深入分析，不结项 |
| IOMMU地址转换、权限与失效接口 | VT-d权限；SMMU范围失效、域变化、walk删除与split/gather | VT-d真实内核PTE读回；SMMU原函数、命令队列观察与专用顺序检查；权限/编码/范围/中间状态 | SMMU硬件完成、并发及SVA平台；VT-d设备DMA/IOTLB。设备模式不等于CPU架构 | SMMU有界阶段评审已完成；VT-d后置 |
| 数据表示与ABI边界 | bcachefs、OCFS2及其他共享格式案例 | bcachefs四格真实编译、OCFS2条件链与局部表示判定；端序、类型及角色关系 | 完整生成/读写/消费、实际路径、可复用事实提取与独立评价；NUMA未决不列新阳性 | 整体暂缓 |
| 固件与平台信息接口 | ACPI来源/政策、Xen CPU枚举条件 | 部分真实启动或原函数投影；来源资格、政策版本与阶段传播 | 完整历史入口与平台配对、实际接受/枚举结果；与CPU用途交叉，不重复计案例 | 保留辅助机制材料，未完成家族验证 |
| 尚未形成项目验证的其他家族 | CPU页表/TLB、内存序/原子、通用IRQ、计时、uaccess等 | 不将官方规范或设备IOMMU材料计作这些家族已验证 | 只有形成明确问题、依据和可行对照后再立项；当前不为凑覆盖开新项 | 未系统开展 |

## 完成标准与后续登记规则

1. 每次完成一个具体接口用途的阶段分析，在下表追加记录，写清家族、接口用途、案例、判定关系、证据、人工依赖、未决项和下一步；同时更新家族表。不能仅写“CPU完成”或“DMA完成”。
2. “阶段方法已整理”表示有依据的关系、检查步骤、对照作用和边界已成文，可以保留不足并转下一机制；不等于完整检测完成。失败、暂停及未完成保留真实状态。
3. “声明范围验证完成”需该范围的要求/提供者/消费关系及合法对照支持结论，有可复现检查和明确人工分工；“独立方法评价完成”另需未用于开发的材料、公平比较、错误与拒判报告。
4. 当前没有任何家族达到整体自动检测与独立评价完成。正式独立正例/正常仍0/0；运行格、局部函数组合、候选数量不计作案例数。
5. 规范权威、角色和关系目前仍有人工输入。案例结论要提炼可复用要求，并通过其他调用者/同用途材料检验，不能只累积专用脚本。

## 阶段记录（首次登记复用既有成果，不计本轮新增实验）

| 日期 | 家族／具体用途 | 阶段结论、证据入口 | 边界与下一步 |
| --- | --- | --- | --- |
| 2026-10-26 | CPU／拓扑集合供锁用途消费 | 集合覆盖×准备资格×阶段；linux_bug_analyze/experiments/case_taxonomy/cpu_method_20261026/ | 阶段方法已整理；消费期限、锁别名与稳定性不足；人工用途/角色摘要 |
| 2026-10-26 | 内存几何／Btrfs参数裁剪和inline用途 | 区分准备c=d、行为min(r,c)=min(r,d)及文件结果；linux_bug_analyze/experiments/case_taxonomy/btrfs_method_20261026/ | 阶段方法已整理；离线几何不代替消费期限参考；正常资格/关系人工登记 |
| 2026-10-26 | IOMMU／SMMU失效用途与提交证据 | 范围/编码×对象发布状态×事件顺序；linux_bug_analyze/experiments/case_taxonomy/smmu_review_20261026/ | 有界评审完成；真实硬件完成、并发、SVA仍缺；适配器与语义分类人工 |
| 2026-10-26 | DMA／virtio_input缓冲 | 分支与时序补证进行中；virtio_dma_chain_20261026、virtio_kimi_direct_20261026、virtio_recycle_20261026、virtio_shutdown_20261026（均在上述case_taxonomy目录） | 未标完成；本轮reset补证不证明真实并发安全，继续原add和缓存维护 |

## 当前执行顺序

先完成virtio所需的有界判定方法：原add错误生成/成功发布→后端copyback与维护范围→对象所有权与适用平台证据→方法评审。关闭同步只补足影响判定的条件，不无限追踪整个驱动。随后按机制差异和可行性评审下一接口用途；不自动恢复表示接口或R3，不绕过VT-d后置安排。三份工作文档和每日日志继续按AGENTS维护；本文在阶段完成或计划实质变化时同步更新。
'''
(R/'接口验证后续规划.md').write_text(plan,encoding='utf-8')
ag=R/'AGENTS.md';s=ag.read_text(encoding='utf-8');needle='- 研究主线及下一项以`当前代办.md`为准；'
addition='- 用户于2026-10-26要求以`接口验证后续规划.md`维护接口家族总览；每完成一个具体接口用途的阶段分析，追加阶段记录并更新状态，区分家族、案例和机制，不将阶段完成写成全家族或独立验证完成。\n'
if addition not in s:s=s.replace(needle,addition+needle);ag.write_text(s,encoding='utf-8')
source=H.parent/'virtio_dma_chain_20261026/source/drivers__virtio__virtio_ring.c'
dump(H/'add_source_review.json',{'source_sha256':sha(source),'scope':'manual pinned source review, no original add execution this round','branches':[{'lines':'623-626','condition':'broken','result':'-EIO before mapping'},{'lines':'657-669','condition':'num_free < descs_used','result':'-ENOSPC before mapping; notify only if out_sgs'},{'lines':'700-702,772-791','condition':'single input SG map failure','result':'-ENOMEM, no available publication; first-SG failure has no earlier descriptor to unmap'},{'lines':'734-765','condition':'successful mapping','result':'consume free entries/store token/write avail then barrier and index publication'}],'limits':['prior injected add errors do not prove real reachability','after detach a free descriptor exists; ENOSPC after ordinary requeue needs other consumption or further evidence','no real allocation/mapping/queue publication executed'], 'next':'execute original add with bounded mapping backend and connect to recycle trace'})
section='''## 10月26日 最新进展：家族规划重整与virtio关闭同步补证

按用户要求重整《接口验证后续规划.md》，区分家族、接口用途、案例与机制；列六个已有材料家族/边界及未系统开展家族，登记CPU拓扑、Btrfs和SMMU既有阶段成果，virtio保持进行中。原规划完整备份于本轮plan_before.md；旧Claude、累计预算、Btrfs无挂载及旧VT-d排程不再作当前指示。AGENTS增加阶段完成后维护该文档的约定，未改变暂停项或独立评价口径。

继续virtio：新取固定父版四份virtio核心、PCI modern/common及MMIO源码并核blob，执行4个原函数（reset、synchronize_cbs、PCI reset及vector同步）。2次编译、32组局部执行通过：HARDEN开/关×同步回调有/无×INTx开/关×MSI-X 0/2×状态延迟0/2。状态读写、IRQ/RCU、AVQ清理为替身；包含无vector及无回调的构造分支，不冒充32个合法PCI设备配置。

关键结果：PCI modern reset写0后循环读至0，随后AVQ清理、vector同步再返回；开启HARDEN还会先break并同步回调（无回调时RCU fallback），关闭HARDEN不等于PCI路径不做同步。上轮ready变化控制不能推出关闭竞态。这里只证原函数调用顺序，未证明真实中断等待效果、input注销安全、所有transport或真实并发。MMIO源码另有synchronize_irq及del_vqs/free_irq，未执行，不套用PCI结论。

原add源码复核补明broken返回EIO、容量不足ENOSPC均在映射前；单输入SG映射失败走ENOMEM回滚，首项失败没有先前映射需要解除，且不发布avail；成功后才登记token与avail并在屏障后更新索引。上一轮注入ENOSPC只能证明驱动反应；detach已经增加空闲描述符，普通重投实际触发容量不足仍需额外条件。原add本轮尚未编译执行，不写成真实失败链已验证。

下一项保持原add/描述符发布与回收联动验证，再补DMA copyback/缓存维护边界，形成限定用途的方法评审；virtio不结项。本轮无模型调用、真实设备运行或新缺陷，独立正例/正常0/0；用途与源码判读仍人工。本轮证据linux_bug_analyze/experiments/case_taxonomy/virtio_shutdown_20261026/（sources、functions、builds、results、add_source_review、README）；日志、待办、进展、交接同步维护，三份WSL镜像以notes_sync为准，Word未改。

以下为历史记录，以本节及用户最新指示为准。

'''
(H/'README.md').write_text('# virtio关闭同步补证与接口家族规划\n\n'+section,encoding='utf-8')
before=json.loads((H/'notes_before.json').read_text(encoding='utf-8'))['before_sha256'];after={}
for n,d in before.items():
 p=R/n
 if sha(p)!=d:raise RuntimeError('changed: '+n)
 title,_,body=p.read_text(encoding='utf-8').partition('\n');p.write_text(title+'\n\n'+section+body.lstrip('\n'),encoding='utf-8');after[n]=sha(p)
dump(H/'notes_update.json',{'before_sha256':before,'after_sha256':after})
with (R/'日志/2026-10-26.md').open('a',encoding='utf-8') as f:f.write('\n\n'+section)
print('planning, AGENTS, 3 notes and log updated')
