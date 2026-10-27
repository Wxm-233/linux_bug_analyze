from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;E=H.parent;R=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
areas=[
('编码与规范','smmu_chain_20261026/authority.json','已核指定版本保留组合/范围公式；不能泛化全部架构版本/errata'),
('上游触发','smmu_range_bounds_20261026/scope_audit.json','原入口及参数变化已核；任意页数不是普通munmap已证触发'),
('对象资格','smmu_lifecycle_20261026/evidence_packet.json','角色、粒度、stage、注册/事务条件证据；非同一真实运行对象'),
('walk删除','smmu_unmap_20261026/obligation_O7_update.json','限定原walker及编码链已执行；设备walk-cache完成未证'),
('split/leaf gather','smmu_split_20261026/method_update.json','原split/安装/gather分支已测；原子竞争注入非真实并发'),
('观测器资格','smmu_queue_20261026/audit.json','模型不识别目标保留组合，不作为这条规则的正确性真值'),
('真实平台','smmu_platform_20261026/platform_admission.json','所测QEMU SSID0，完整SVA绑定受阻；需不同合格平台'),
('自动判定','smmu_review_20261026/regression.json','有界qtest适配器时间顺序修正；依赖人工规则/字段语义')]
save('review_matrix.json',dict(status='bounded_method_reviewed_not_full_interface_complete',independent_positive_normal=[0,0],automatic_N1=False,automatic_N2=False,areas=[dict(area=a,path=str((E/p).relative_to(R)),sha256=sha(E/p),assessment=d) for a,p,d in areas]))
save('virtio_next_scope.json',dict(status='next_deep_analysis_prepared_no_new_virtio_experiment',fix='95c7b0ad6c69d1c0608ff0bbd358a546856beaf3',parent='db191ba0c8564ff84877e5b1c9553e991feca239',previous_evidence_sha256=sha(E/'virtio_method_20261026/source_audit.json'),questions=['event allocation/base alignment and target ABI','sg_init_one single 8-byte event -> virtqueue mapping direction','virtqueue DMA API bypass/use and negotiated feature conditions','direct/IOMMU/bounce actual target and cache maintenance','get_buf/unmap/requeue and CPU/device ownership windows'],first_sources=['drivers/virtio/virtio_input.c','drivers/virtio/virtio_ring.c','include/linux/virtio_config.h','kernel/dma/mapping.c','kernel/dma/direct.h','kernel/dma/swiotlb.c'],main_analysis_route='new scoped source main-analysis task via native Claude Code AWS-Claude-Opus-5.5; not invoked this round',limits='do not treat previous layout-only closure as current completion; do not replay layout matrix as new mechanism evidence'))
body='''## 10月26日 最新进展：SMMU有界方法评审与时间证据修正

完成SMMU当前方法阶段评审，review_matrix逐项绑定8个方面的证据SHA及缺口：规范/编码、上游触发、对象资格、walk删除、split/leaf gather、观测器资格、真实平台和自动判定。结论是限定开发方法已有实质证据，可按既定顺序转入virtio深入；不是SMMU完整接口分析/独立检测完成，也不撤销真实运行、并发、硬件完成和独立评价缺口。停止继续扩张同一家族组合，SMMU保留开放跟踪。

评审实际发现并修正我们自己的检查器问题：旧checker用按地址字典汇总，忽略事件顺序，构造“PROD先于命令写入”的记录仍可给observed_encoding。新checker严格匹配已登记qtest布局的写入→读回→配置/使能→PROD→状态读取顺序，拒绝额外写入及不支持消费者状态。关键输入校验用显式条件而非assert；10份旧有序记录结论保持，4种顺序/读回/缺失控制均拒绝观测关联，并在Python -O下再次验证4项控制仍拒判。旧checker/旧结果保留，当前qtest判定入口改为smmu_review_20261026/checker.py；它仍不支持任意转录，不是通用验证器。

这体现接口方法所需的“事实是什么、属于哪个对象、发生在什么时候”三项联系，不能只凑齐字段。原始提供字值的局部规则与实际提交证据继续分开，QEMU消费不覆盖规范违规，whole_path始终不足。本轮修的是研究检查器，不是发现新Linux缺陷。N1尚未自动推导，N2对照仍人工登记；独立正例/正常0/0。

下一项明确转入virtio深分析：先固定父/修复源码，追event分配及基址→单个8字节SG→virtqueue选择DMA API/绕过→实际后端/目标→回收重投及所有权。优先弄清feature条件、direct/IOMMU/bounce和维护时段，不重复此前布局矩阵。virtio_next_scope.json已登记材料和问题，仅准备范围，不算新virtio实验。新的源码主分析仍使用AGENTS指定Windows原生Claude Code/AWS-Claude-Opus-5.5，遵守原有拒绝记录，不将本轮程序评审称为项目模型分析。

统计：10份开发回放、4项构造控制、4项优化解释器控制，以及旧/新检查器各1次问题复现比较，共20次assess调用；无编译、内核/QEMU启动、设备操作、项目模型调用或新缺陷。证据linux_bug_analyze/experiments/case_taxonomy/smmu_review_20261026/（checker、regression、control_inputs、optimized_controls、review_matrix、virtio_next_scope）。日志、待办、进展、交接同轮维护，三份WSL镜像以notes_sync.json为准，Word未改。表示接口/R3暂缓、VT-d后置不变。

以下为历史记录，以本节及用户最新指示为准。

'''
(H/'README.md').write_text('# SMMU方法阶段评审\n\n'+body+'\n## 留档与恢复条件\n\n- 使用合格SVA平台时恢复绑定/实际单页触发与设备失效实验；所测QEMU不满足SSID前提。\n- 新用途/新输入若超出当前原函数支持域，应先补适用条件，不能沿用旧局部通过。\n- 引入独立样本前冻结规则、暴露史和评价口径；本阶段全部是开发材料。\n- 时间顺序问题只影响不受支持/矛盾转录；原10份严格有序观测经新入口重算保持。\n',encoding='utf-8')
before=json.loads((H/'notes_before.json').read_text(encoding='utf-8'))['before_sha256'];after={}
for n,d in before.items():
 p=R/n;assert sha(p)==d
 title,rest=p.read_text(encoding='utf-8').split('\n',1);p.write_text(title+'\n\n'+body+rest.lstrip(),encoding='utf-8');after[n]=sha(p)
save('notes_update.json',dict(before_sha256=before,after_sha256=after))
with (R/'日志/2026-10-26.md').open('a',encoding='utf-8') as f:f.write('\n'+body)
save('delivery_manifest.json',{p.name:sha(p) for p in H.iterdir() if p.is_file() and p.name not in ['delivery_manifest.json','notes_sync.json']})
print('Bounded review complete; SMMU limitations retained; virtio deep analysis next.')
