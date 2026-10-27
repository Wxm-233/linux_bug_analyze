from pathlib import Path
import hashlib,json,shutil
H=Path(__file__).resolve().parent;R=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
names=['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']
before={n:sha(R/n) for n in names};save('notes_before.json',dict(before_sha256=before))
sources={}
for n in ['smmu_range_result.json','virtio_dma_layout_result.json']:
 p=H.parent/n;d=json.loads(p.read_text(encoding='utf-8'))
 assert len(d['cases'])==d['cases_total']
 sources[n]=dict(sha256=sha(p),fix=d['fix'],evidence_level=d['evidence_level'],historical_test_combinations=d['cases_total'])
save('material_inventory.json',sources)
body='''## 10月26日 用户确认的排程调整：转向其他接口

用户指出不应持续聚焦CPU/Btrfs，并确认先积累其他接口判定机制。**本节替代此前“下一项CPU信息导出”的安排。** CPU拓扑与Btrfs标为阶段收束，保留期限、对象、适用条件等缺口，不代表完整自动检测已完成；只有补证能解决明确判定问题时再回访。

### 当前待办顺序

1. **下一项：SMMU范围失效接口。** 先核已有源码、函数测试与判定依据，分开请求范围覆盖、命令字段组合合法性、leaf/non-leaf用途及硬件能力条件。提取规范来源、适用范围、事实提取、合法正常/边界对照和程序/模型/人工分工；先形成有界方法闭环，再决定是否需要新执行。现有smmu_range_result.json记录336组历史函数测试组合，使用记录命令队列的替身，没有真实设备执行；SVA/io-pgtable调用者为源码追踪，非已执行。组合数不计缺陷数或独立样本。硬件约定须核权威依据，不能将测试内置断言自行当作规范证明。
2. **随后：virtio DMA布局与缓存隔离。** 已有virtio_dma_layout_result.json记录16组历史布局组合（含构造变体），使用类型替身编译；尚无DMA执行。整理首尾边界隔离、缓存粒度、分配与DMA后端适用条件，区分布局成立与真实设备安全。不因与数据表示有关就恢复已暂缓的表示接口分支；若范围交叉，先记录边界。
3. **后续候选：CPU身份与启动范围、固件/平台接口。** 按证据充分度和机制差异再排序。CPU信息导出保留为候选，撤回其紧接CPU拓扑的优先级；不声称这些方向已完成新分析。
4. **保留暂缓：** 表示接口、shmem R3继续暂缓，VT-d继续后置；不借本次排程自动恢复。

各类统一记录用途与依据、适用条件、提供者保证、目标关系、事实证据、合法对照、可解释判定和人工依赖。先积累有差异的机制，再比较公共表示与适配成本；不以同类案例数量或统一入口代码代替研究成熟度。长期目标仍见最终研究目标与阶段推进原则.md，不创建会话级目标。

本轮仅核对现有材料层级并更新排程，未重跑336/16组历史测试，未开展新的SMMU或virtio实验。模型调用/构建/内核运行/新缺陷均0；独立正例/正常样本仍0/0。证据定位：linux_bug_analyze/experiments/case_taxonomy/smmu_range_probe.py、smmu_range_result.json、cross_arch_smmu_source_20261013.json；virtio_dma_layout_probe.py、virtio_dma_layout_result.json、cross_arch_virtio_source_20261013.json。盘点摘要及SHA见interface_queue_20261026/material_inventory.json。

日志、待办、进展和交接说明同轮更新；三份Windows/WSL镜像以interface_queue_20261026/notes_sync.json为准。Word和旧研究结果不改。

以下为历史记录，以本节及用户最新指示为准。

'''
after={}
for n,d in before.items():
 p=R/n;assert sha(p)==d
 title,rest=p.read_text(encoding='utf-8').split('\n',1)
 p.write_text(title+'\n\n'+body+rest.lstrip(),encoding='utf-8');after[n]=sha(p)
save('notes_update.json',dict(before_sha256=before,after_sha256=after))
with (R/'日志/2026-10-26.md').open('a',encoding='utf-8') as f:f.write('\n'+body)
shutil.copyfile(H.parent/'cpu_method_20261026/sync_work_notes.py',H/'sync_work_notes.py')
print('Queue updated: SMMU, then virtio; previous pauses retained.')
