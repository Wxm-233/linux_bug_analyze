from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;R=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
body='''## 10月26日 最新闭环：virtio DMA布局、首尾隔离与后端条件

完成virtio DMA接口有界方法分析。WSL重新编译并执行16组既有布局探针（旧/修复及两种构造变体×64/63事件×64/128假设粒度），结果与历史JSON逐字段一致。保存实际C、编译环境/参数及原始偏移；5份布局源码与旧归档全文/Git blob一致，固定版本DMA文档和事件提交源码另核身份/引文。使用类型替身和主机ABI，没有完整内核或设备运行。

**判定结论：**必须分别检查首尾维护单元隔离。64事件的长度恰为所测粒度整数倍，使仅首标注变体通过；63事件时该变体尾部共享。旧版四组均首尾共享，仅尾标注四组仍首共享，修复四组均首尾隔离。63事件及部分标注是构造开发输入，不是历史合法配置、独立样本或新缺陷。单事件8字节经SG提交，整个数组边界隔离不能冒称整数组一次DMA或证明内部事件的所有权交互。

**自动化与前提：**新audit.py独立从原始偏移算首尾关系，再核旧结果；仍使用人工登记的区间模型。另枚举四个修复布局的384种合成基址余数，验证相对偏移结论依赖基址假设；失配基址可能违反C对象对齐，不是合法运行或修复缺陷。实际基址、有效维护粒度、真实DMA写目标、后端/bounce及所有权时段须分别绑定；本轮actual_base、actual_dma_target、ownership_interval和whole_path均不足。DMA文档提供规范依据，但未由此证明命名平台实际暴露。

**机制积累：**virtio增加空间隔离、后端实际目标和所有权时段的联合要求，与CPU集合/资格/阶段、Btrfs几何裁剪、SMMU覆盖/编码/层级形成不同机制。证据身份、条件表达与缺证流程可复用，字段布局及后端追踪仍为专用适配；未实现统一入口，未完成自动要求推导或独立有效性验证。

**下一项：**本接口布局方法阶段收束，保留真实目标ABI/分配、DMA后端、维护及设备证据缺口，不继续堆布局组合。接下来盘点CPU身份/启动范围与固件/平台既有材料，选定机制有差异且证据足够的一项，先明确依据和人工适配再补实验。CPU信息导出不恢复为默认优先；CPU拓扑/Btrfs/SMMU缺口挂账，表示接口/shmem R3暂缓，VT-d后置。

统计：新增16次布局编译与16次探针执行、384个合成算术余数检查；新内核构建/启动、DMA操作、项目模型调用、新缺陷均0。独立正例/正常样本仍0/0。证据入口linux_bug_analyze/experiments/case_taxonomy/virtio_method_20261026/（README、results、raw_layouts、source_audit、relation_audit、builds、environment及16份C）。Word未改；日志、待办、进展和交接同轮更新，三份WSL镜像以本目录notes_sync.json为准。

以下为历史记录，以本节及用户最新指示为准。

'''
before=json.loads((H/'notes_before.json').read_text(encoding='utf-8'))['before_sha256'];after={}
for n,d in before.items():
 p=R/n;assert sha(p)==d
 title,rest=p.read_text(encoding='utf-8').split('\n',1)
 p.write_text(title+'\n\n'+body+rest.lstrip(),encoding='utf-8');after[n]=sha(p)
save('notes_update.json',dict(before_sha256=before,after_sha256=after))
with (R/'日志/2026-10-26.md').open('a',encoding='utf-8') as f:f.write('\n'+body)
save('delivery_manifest.json',{p.name:sha(p) for p in H.iterdir() if p.is_file() and p.name not in ['delivery_manifest.json','notes_sync.json']})
print('Virtio method and all working notes saved.')
