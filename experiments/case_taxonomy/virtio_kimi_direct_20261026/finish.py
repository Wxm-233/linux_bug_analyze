from pathlib import Path
import json, hashlib, re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
MODEL = ROOT / '模型调用测试/2026-10-26/virtio_kimi_dma_chain'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p, value): p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
final = (MODEL/'final.md').read_text(encoding='utf-8')
items = json.loads(re.search(r'```json\s*(.*?)```', final, re.S).group(1))
assert len(items)==11
write(HERE/'model_obligations.json', items)
corrections = {
 'VIN-01': '保留几何/分配前提；旧宿主替身ABI不能代表目标平台，需真实配置、基址和粒度。',
 'VIN-02': '修正范围为事件输入路径。状态路径调用add_outbuf，不能称全驱动只发add_inbuf。原use_indirect确要求total_sg>1，单SG不选indirect；不替代真实协商观测。',
 'VIN-03': '原use_map_api分支已有上一轮局部执行支持，真实feature与Xen值仍需取证。',
 'VIN-04': '保留布局选择为待观测条件，不宣称四种布局均已运行。',
 'VIN-05': '保留父设备属性及实际DMA后端要求，尚未取得真实父设备属性。',
 'VIN-06': '补direct原函数40组及bounce谓词24组条件证据；dma_kmalloc_needs_bounce实际定义在include/linux/dma-map-ops.h。模型所列kernel/dma/iommu.c位置未核实，不当已确认路径。bounce目标与CPU copyback/缓存所有权分开，不能直接判安全。',
 'VIN-07': '拒绝原判定规则。736%64=32，64B尾部恰落边界错误；旧宿主布局64/128B两端均共享。仅128B、仅direct且无bounce过窄，未审IOMMU不能排除。事件同向且CPU不写不能证明内部共享良性，仍需缓存操作与同时所有权证据。不得将宿主反例变成真实架构腐蚀。',
 'VIN-08': '分开源码调用顺序与实际CPU可见性。unmap先于token返回不保证custom/bypass实现的同步效果。读取完整事件而不检查len是源码事实；设备必须写满8字节需规范依据，暂为候选要求。',
 'VIN-09': '保留自定义map语义必须单独核验；尚无实际后端实例证据。',
 'VIN-10': '保留忽略add返回值事实；bypass只绕过映射失败，并不排除队列容量/分配失败。单调萎缩需限定生命周期和恢复条件，无驱动检查不等于系统无日志。待完整路径失败注入。',
 'VIN-11': '保留配对与remove/freeze为待核验要求；当前局部unmap不能替代完整生命周期。'
}
write(HERE/'model_review.json', {
 'review_type':'human_source_and_existing_experiment_audit',
 'receipt_sha256':sha(MODEL/'receipt.json'), 'final_sha256':sha(MODEL/'final.md'),
 'candidate_count':11, 'automatic_unreviewed_adoption':0,
 'dispositions':corrections, 'independent_positive':0,'independent_normal':0,
 'evidence':['../virtio_method_20261026/raw_layouts.json', '../virtio_dma_chain_20261026/source/drivers__virtio__virtio_ring.c', '../virtio_dma_chain_20261026/source/drivers__virtio__virtio_input.c', 'audit.json','bounce_gate_results.json','additional_source.json'],
 'whole_path':'insufficient', 'new_kernel_defects':0})
backend = ROOT/'linux_bug_analyze/analysis_out/current_analysis_backend.json'
b=json.loads(backend.read_text(encoding='utf-8'))
b['primary_analysis']['connectivity_status']='complete_virtio_source_analysis_received_20261026'
b['primary_analysis']['latest_receipt']='模型调用测试/2026-10-26/virtio_kimi_dma_chain/receipt.json'
b['primary_analysis']['semantic_review']='11 candidates reviewed with corrections; not automatic detection or full platform validation'
write(backend,b)
section = '''## 10月26日 最新进展：主分析切换Kimi，virtio direct/bounce条件补证

用户明确要求以后主分析均用Kimi，已更新AGENTS.md及current_analysis_backend.json，默认Kimi-K3/ISRC Chat Completions SSE，密钥仅仓库外读入内存；旧Claude拒绝与路由保留。本次使用原virtio任务原文，SHA一致，无自动重试。439.61秒收到完整正文12483字符，实际模型Kimi-K3、stop、DONE与EOF均成立，无refusal；可见用量147398 token，usage_known=false，不当完整账单。每调用独立1M。

新增direct原map/unmap/CPU同步函数1次编译40次执行，覆盖direct、bounce、失败、coherent与skip/MMIO控制；同步回调顺序审核通过。补取固定父版dma-map-ops.h，原bounce安全/大小谓词2次编译24次执行：在明确的ARCH_DMA_MINALIGN=128、缓存粒度64及roundup替身假设下，配置启用且非coherent、FROM_DEVICE、size8触发bounce。谓词不检查结构内指针偏移，字段对齐不能替代bounce判定。合计3次编译64次执行；后端、分配器及架构维护为替身，不证明真实DMA地址、copyback、缓存效果或完整设备运行。swiotlb辅助函数被调用也不等于实际发生bounce拷贝。

Kimi交付11条候选义务，已逐项人工复核，未直接自动采纳。纠正关键错误：其736偏移在64B边界的计算错误（余32），旧宿主布局64/128B两端均共享；“事件内部同向所以安全”“仅128B且direct无bounce才危险”均无充分依据。状态队列实际使用add_outbuf；unmap调用先后不能替代所有后端CPU可见性保证；完整8字节要求仍需规范。IOMMU、bounce copyback、内部事件并行所有权均保持开放。原模型正文不改写，纠正另存model_review.json。

接口判定现推进到：事件对象/用途→use_map_api与实际后端→direct/bounce条件→同步调用顺序，不能仅靠布局判好坏。程序目前验证这些局部分支与条件，契约语义和证据绑定仍依赖人工；未建统一自动推导器，未发现新Linux缺陷，独立正例/正常仍0/0。

下一项：在固定版本补get_buf→detach/unmap→CPU读取→重新入队的原函数路径及失败分支，核对共享事件不同所有权窗口；随后补实际后端的copyback/架构缓存维护依据与合法平台条件。避免继续堆布局组合。virtio不结项；SMMU保留开放缺口、表示接口/R3暂缓、VT-d后置。未来主分析使用Kimi，不再以旧Claude拒绝阻止已授权的新路由，遇新失败仍保存而不自动改写重试。

证据：linux_bug_analyze/experiments/case_taxonomy/virtio_kimi_direct_20261026/（functions、results、audit、additional_source、bounce_gate_results、model_obligations、model_review）；完整模型记录在模型调用测试/2026-10-26/virtio_kimi_dma_chain/。本轮无内核/QEMU启动、真实设备DMA或独立样本。日志与三份工作文档同轮更新，Windows/WSL镜像以本轮notes_sync.json为准，Word未改。

以下为历史记录，以本节及用户最新指示为准。

'''
(HERE/'README.md').write_text('# virtio Kimi主分析与direct/bounce条件验证\n\n'+section,encoding='utf-8')
before=json.loads((HERE/'notes_before.json').read_text(encoding='utf-8'))
after={}
for name,digest in before['before_sha256'].items():
 p=ROOT/name
 assert sha(p)==digest, name
 old=p.read_text(encoding='utf-8')
 title,sep,body=old.partition('\n')
 p.write_text(title+'\n\n'+section+body.lstrip('\n'),encoding='utf-8')
 after[name]=sha(p)
write(HERE/'notes_update.json',dict(before,after_sha256=after))
with (ROOT/'日志/2026-10-26.md').open('a',encoding='utf-8') as f: f.write('\n\n'+section)
print(json.dumps({'reviewed':len(items),'notes_updated':len(after),'model_status':'complete_final_received'}))
