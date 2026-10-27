from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;R=H.parents[3];S=H.parent/'smmu_chain_20261026/source'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
anchors=[]
for name,needles in [('00_drivers__iommu__arm__arm-smmu-v3__arm-smmu-v3.c',['.tlb\t\t= &arm_smmu_flush_ops,','.tlb_flush_walk = arm_smmu_tlb_inv_walk,','return ops->unmap_pages(ops, iova, pgsize, pgcount, gather);']),('06_drivers__iommu__io-pgtable-arm.c',['.unmap_pages\t= arm_lpae_unmap_pages,','io_pgtable_tlb_flush_walk(iop, iova + i * size, size,','} else if (!iommu_iotlb_gather_queued(gather)) {']),('07_include__linux__io-pgtable.h',['if (iop->cfg.tlb && iop->cfg.tlb->tlb_flush_walk)','iop->cfg.tlb->tlb_flush_walk(iova, size, granule, iop->cookie);'])]:
 p=S/name;lines=p.read_text(encoding='utf-8').splitlines()
 for needle in needles:
  hits=[dict(line=i+1,text=l) for i,l in enumerate(lines) if needle in l];assert hits,needle
  anchors.append(dict(source=str(p.relative_to(R)),sha256=sha(p),needle=needle,hits=hits,method='manual source anchors'))
save('dispatch_anchors.json',anchors)
save('obligation_O7_update.json',dict(status='partial_original_walker_executed',new=['unmap_pages guard and recursive descent','nonleaf level2 table deletion invokes walk then frees actual host child allocation','callback sees parent PTE zero','queued nonleaf still invokes immediate walk','walker-derived request passed into S1/S2 old/fixed and encoded coverage'],remaining=['block splitting helper abort-only and not executed','concurrent table install/race','complete original allocator/map and driver dispatch runtime','DMA sync/barrier semantics','same runtime domain identity','hardware walk-cache invalidation completion'],counterexample_role='known development table-shape control; not independent normal sample'))
body='''## 10月26日 最新进展：SMMU原unmap/walk/释放链及自动顺序检查

本轮连续完成原walker执行、queued/清零观测、下游命令核验和顺序检查四项。从固定源码提取7个原函数及几何/描述符宏：iopte_leaf、物理地址编码/解码、clear、递归free、递归unmap、unmap_pages。3种页配置执行66组：单/双非叶删除、表尾限制、遇空项部分返回、叶删除及queued跳过收集、递归页删除、空项、非法页大小、零count和IAS越界。原函数体未改；宿主页表分配/地址映射、结构布局、DMA同步及失效回调为替身，split helper为abort且本轮不触发。

增强观测再编译3份执行12组：walk回调当场确认父PTE已清零，记录返回后free；非coherent先调用同步替身。queued非叶仍立即walk失效并释放，不能把leaf分支的queued延迟条件套到非叶；递归删除一个leaf也不意味着自动回收上级表。支持范围为level2→level3子表删除，未执行split分配/竞争或多层嵌套free。

把原walker双表删除实际输出的6条范围（3页配置各2条）送入父/修复×S1/S2链，共24次下游执行及24次编码投影调用。范围大小为该层block，granule为基础页，非leaf TTL=0；24组命令字均精确覆盖请求且无目标保留组合。这是同后端不同调用用途的有据对照，不是新正常独立样本。参数跨程序传递，未伪装为同一运行domain；S1/S2沿用早期脚手架逻辑标签，非真实枚举初始化证明。

新增audit.py审核12份增强事件和4项构造控制：释放提前、缺清零证据、缺同步证据、错误粒度分别给违反或不足。通过仅表示本地事件序列，hardware_visibility/whole_path仍不足。源码dispatch_anchors另核驱动unmap→ops、配置flush_ops及通用helper非空回调门禁；这些是带SHA/行号的人工锚点，运行中helper/回调仍是替身。不能把回调返回当设备完成。

原主分析O7由“walker未执行”更新为“原walker限定分支已执行”；仍缺split路径、分配/竞争、实际页表构建、同对象完整驱动链和设备walk-cache完成。首批3次编译有原函数unused参数和脚手架缩进警告，保留build输出；增强脚手架修缩进、对原unused参数定向关闭警告并启用Werror，未改原函数体。未调用新的项目主分析模型。

下一项：继续沿实际unmap补block split路径的分配失败、成功安装、安装竞争及失效收集条件，明确哪些回调可归入walk、哪些属于leaf gather，再决定是否具备方法阶段评审条件。保持SVA真实平台SSID缺口和物理设备完成缺证；SMMU不结项，virtio深分析随后，表示接口/R3暂缓、VT-d后置不变。

统计：12次局部编译；126次函数/编码程序执行（66基础walker+12增强walker+24下游+24编码），另12份事件审核+4个合成控制。无新模型/内核启动、设备操作、项目模型、新缺陷，独立正例/正常0/0。证据linux_bug_analyze/experiments/case_taxonomy/smmu_unmap_20261026/（function_manifest、builds、results、observed_results、consume_results、sequence_audit、dispatch_anchors、obligation_O7_update）。Word未改；日志、待办、进展和交接同轮维护，WSL镜像以notes_sync.json为准。

以下为历史记录，以本节及用户最新指示为准。

'''
(H/'README.md').write_text('# SMMU io-pgtable原unmap机制小闭环\n\n'+body+'''\n## 复核入口与分支

- run.py：提取原源码/宏并生成unmap.c；mode 0单表、1双表、2表尾、3第二项空、4叶、5queued叶、6递归页、7空项、8非法大小、9零count、10IAS越界。
- extend.py：增加回调入口清零观测和mode11 queued非叶，保留首轮文件。
- consume.py：只替换早期SMMU链测试main，接入walker实参；调用已有编码投影前核二进制SHA。
- audit.py：研究者登记的level2删除顺序及几何检查，缺证控制不作真实错误。

清零→同步（非coherent）→walk回调→返回→free的本地顺序得到补证；DMA可见性及设备同步完成尚未证明。页表分配/物理直映、ops布局和回调仍是假设边界，不能据本轮证明完整内核路径可达。
''',encoding='utf-8')
before=json.loads((H/'notes_before.json').read_text(encoding='utf-8'))['before_sha256'];after={}
for n,d in before.items():
 p=R/n;assert sha(p)==d
 title,rest=p.read_text(encoding='utf-8').split('\n',1);p.write_text(title+'\n\n'+body+rest.lstrip(),encoding='utf-8');after[n]=sha(p)
save('notes_update.json',dict(before_sha256=before,after_sha256=after))
with (R/'日志/2026-10-26.md').open('a',encoding='utf-8') as f:f.write('\n'+body)
save('delivery_manifest.json',{p.name:sha(p) for p in H.iterdir() if p.is_file() and p.name not in ['delivery_manifest.json','notes_sync.json']})
print('Walker, queued controls, encoded consumers and sequence checker recorded; O7 still partial.')
