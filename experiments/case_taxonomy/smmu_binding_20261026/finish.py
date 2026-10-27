from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;R=H.parents[3];S=H.parent/'smmu_chain_20261026/source'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
anchors=[]
for p,needle,claim in [
(H/'source/drivers__iommu__iommu.c','domain->mm = mm;','generic SVA domain stores mm'),
(S/'03_drivers__iommu__arm__arm-smmu-v3__arm-smmu-v3-sva.c','struct iommu_domain *domain = iommu_get_domain_for_dev(dev);','driver obtains device translation domain separately'),
(S/'03_drivers__iommu__arm__arm-smmu-v3__arm-smmu-v3-sva.c','smmu_mn->domain = smmu_domain;','notifier stores translation domain'),
(H/'source/mm__mmu_notifier.c','subscription->mm = mm;','generic registration stores mm'),
(S/'00_drivers__iommu__arm__arm-smmu-v3__arm-smmu-v3.c','domain->pgsize_bitmap = pgtbl_cfg.pgsize_bitmap;','finalise copies narrowed bitmap'),
(S/'06_drivers__iommu__io-pgtable-arm.c','cfg->pgsize_bitmap &= page_sizes;','restrict narrows granule family')]:
 lines=p.read_text(encoding='utf-8').splitlines();hits=[i+1 for i,l in enumerate(lines) if needle in l];assert hits
 anchors.append(dict(path=str(p.relative_to(R)),sha256=sha(p),needle=needle,lines=hits,researcher_registered_claim=claim))
save('binding_evidence.json',dict(anchors=anchors,source_semantics='researcher reviewed follow-up to prior model obligations; not automatically extracted',roles=['generic_sva_domain','device_translation_domain','notifier','shared_cd','mm'],whole_path='insufficient'))
body='''## 10月26日 最新进展：SMMU页粒度收敛与SVA对象/注册关系补证

继续上一轮主分析未决项，不转新接口、不声称SMMU完成。本轮新取固定父版5份通用IOMMU/页表/注册源码并核Git blob，结合原驱动补证；没有新增项目模型调用或自动语义推导。

**对象链纠正：**通用IOMMU_DOMAIN_SVA对象保存mm及PASID绑定，驱动set_dev_pasid取mm后，__arm_smmu_sva_bind另从iommu_get_domain_for_dev取得设备翻译域。notifier保存的是后者。不能按domain变量同名合并这两个角色，也不能用SVA对象type证明设备翻译域stage=S1。binding_evidence.json记录带源码SHA/行号的人工语义锚点，不伪称自动别名分析。

**页粒度条件得到补证：**设备bitmap→可变pgtbl_cfg→LPAE restrict_pgsizes→domain回填的源码链已核。3份原收敛函数程序执行51组输入，24组含CPU页时最终最小粒度均等于CPU页，27组页条件不通过/前提控制不能当合法正常SVA平台。bitmap仍可多位，不要求仅有CPU页位。该结论依赖所核分配路径成功且消费同一翻译域；真实allocator/finalise/CD硬件写入尚未执行。

**注册时序与失败补证：**原notifier_get函数另编译执行7条成功/分配失败/注册失败/CD写失败/同mm复用/不同mm新建分支。字段在register前准备，CD写失败时已调用注册，随后put且不加入驱动列表。因此注册发生不是绑定完成，失败返回也不能排除此前的可回调窗口。通用注册源码发布subscription->mm、回调按同mm列表分派，提供身份联系依据，但实验的注册/列表/内存/CD/释放为替身，没有真实RCU/SRCU并发证明。

**stage仍未闭合：**SVA能力/使能检查没有直接stage约束；默认零初始化且S1枚举为0不能排除finalise改stage或identity bypass。s1_cfg/s2_cfg为union，不能假设非S1时s1cdmax必为0以证明写CD会拒绝。attach在SVA已使能时拒绝更换域是稳定性门禁线索，仍需核其他成功/释放路径和锁前提。保留真实合法profile、S1全路径和设备效果不足。

**下一步仍留在SMMU：**针对设备翻译域stage与SVA合法附着做有界资格审计，核初始化/附着/功能使能路径和锁门禁，区分前端拒绝、外部条件及未知；不通过自建S1对象宣布可达。基于有证据的输入范围再补非大块对齐地址、字段宽度及命令覆盖。virtio实际DMA目标/后端/所有权随后继续；CPU身份/固件扩展不启动，表示接口/R3暂缓、VT-d后置不变。

统计：4次成功局部编译、58次函数执行（51收敛+7注册分支），另1次测试脚手架编译失败；失败因puts符号冲突和缩进警告，失败C/脚本保留，修脚手架后通过，原函数体不改。无新内核构建/启动、设备操作、项目模型或新缺陷，独立正例/正常仍0/0。材料在linux_bug_analyze/experiments/case_taxonomy/smmu_binding_20261026/（README、source_manifest、granule_results、notifier_results、binding_evidence）。Word及旧实验不改；日志、待办、进展、交接已维护，三份WSL镜像以本轮notes_sync.json成功回执为准。

以下为历史记录，以本节及用户最新指示为准。

'''
before=read(H/'notes_before.json')['before_sha256'];after={}
for n,d in before.items():
 p=R/n;assert sha(p)==d
 title,rest=p.read_text(encoding='utf-8').split('\n',1);p.write_text(title+'\n\n'+body+rest.lstrip(),encoding='utf-8');after[n]=sha(p)
save('notes_update.json',dict(before_sha256=before,after_sha256=after))
with (R/'日志/2026-10-26.md').open('a',encoding='utf-8') as f:f.write('\n'+body)
save('delivery_manifest.json',{p.name:sha(p) for p in H.iterdir() if p.is_file() and p.name not in ['delivery_manifest.json','notes_sync.json']})
print('Binding evidence and working notes saved; SMMU remains in progress.')
