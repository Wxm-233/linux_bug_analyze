from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;R=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 if (H/n).exists():
  assert json.loads((H/n).read_text(encoding='utf-8'))==v;return
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
rows=json.loads((H/'results.json').read_text()); checks=[]
for row in rows:
 events=[l.split() for l in row['stdout'].splitlines() if l.startswith(('publish ','set ','remove ','erase '))]
 for e in events:
  if e[0] in ['set','remove']:assert e[2:]==['1','1']
 if row['mode'] in [1,2,3,8]:
  assert [int(e[1]) for e in events if e[0]=='remove']==[0,1,2]
  assert events[-1][0]=='erase'
 checks.append({'mode':row['mode'],'events':events,'transaction_scope':'pass','whole_path':'insufficient'})
if not (H/'trace_audit.json').exists():save('trace_audit.json',checks)
anchors=[]
for folder,file,needles in [
 ('smmu_binding_20261026','drivers__iommu__iommu-sva.c',['caller must hold a reference to mm_users','domain->users++','iommu_attach_device_pasid(domain','The device should','requests for this PASID must','if (--domain->users == 0)']),
 ('smmu_chain_20261026','00_drivers__iommu__arm__arm-smmu-v3__arm-smmu-v3.c',['static void arm_smmu_remove_dev_pasid','domain = iommu_get_domain_for_dev_pasid','if (master->sva_enabled)']),
 ('smmu_chain_20261026','03_drivers__iommu__arm__arm-smmu-v3__arm-smmu-v3-sva.c',['if (!WARN_ON(!bond)','smmu_mn->domain = smmu_domain','mmu_notifier_register','arm_smmu_write_ctx_desc','iommu_get_domain_for_dev(dev)'])]:
 p=H.parent/folder/'source'/file;lines=p.read_text().splitlines()
 for needle in needles:
  hits=[{'line':i+1,'text':v} for i,v in enumerate(lines) if needle in v];assert hits,needle
  anchors.append({'source':str(p.relative_to(R)),'sha256':sha(p),'needle':needle,'hits':hits,'method':'researcher-selected literal anchors; not semantic extraction'})
save('source_anchors.json',anchors)
save('evidence_packet.json',{
 'scope':'pinned parent 0bb80ecc33a8fb5a682236443c1e740d5c917d1d; heterogeneous local probes, not one runtime instance',
 'roles':{'sva_domain':'mm/PASID binding and generic users','translation_domain':'device domain; notifier domain; page bitmap and stage','notifier':'links mm, CD and translation domain'},
 'obligations':[
 {'id':'object_identity','evidence':'binding_evidence and source_anchors','status':'source-supported; no runtime joined identity'},
 {'id':'granule','evidence':'smmu_binding_20261026/granule_results.json','status':'conditional original-function evidence; allocation success and same translation-domain required'},
 {'id':'stage','evidence':'smmu_stage_20261026/results.json','status':'conditional S1 finalise; sva_enabled alone insufficient'},
 {'id':'registration_cd','evidence':'smmu_binding_20261026/notifier_results.json','status':'register precedes CD write; failure does not exclude callback window'},
 {'id':'group_transaction','evidence':'trace_audit.json','status':'local original-function pass; all-device rollback before mapping erase'},
 {'id':'caller_mm_lifetime','evidence':'source_anchors.json','status':'external mm_users prerequisite; actual caller unobserved'},
 {'id':'device_quiescence','evidence':'source_anchors.json','status':'external no-new-transaction and drained-page-requests prerequisite; actual device unobserved'},
 {'id':'concurrent_callback_lifetime','evidence':None,'status':'insufficient'},
 ],'whole_path':'insufficient','automatic_requirement_derivation':False,'independent_positive_normal':[0,0]})
body='''## 10月26日 最新进展：SMMU组附着事务与解绑前置条件

继续深入SMMU生命周期，未切新接口。固定父版原始group set/remove与PASID attach/detach四函数编译后，9种分支通过：正常附着、三个位置失败、已有映射、插入失败、无group、无set操作、正常解绑。结果保存逐事件映射存在性及模拟锁状态；回滚对全部组成员调用remove，再删除PASID映射。驱动remove通过该映射取得通用SVA对象，因此发布/清理/撤销顺序属于对象可查找性的要求，不能只检查最终返回值。

源码补证：generic SVA复用增加domain->users，仅最后一次unbind触发detach/free；API要求bind调用者持有mm_users引用，unbind前设备不得再发该PASID事务且未完成页请求须已清空。这些是外部生命周期前提，局部函数返回不能补出。SMMU remove在找不到bond时WARN_ON并跳过释放；本轮remove回调是替身，未执行该驱动分支，未把人工三设备组称为真实可达故障或新缺陷。

evidence_packet.json将通用SVA域、设备翻译域、notifier/CD、页粒度、stage与事务/释放义务分开登记。跨轮结果是异构有界证据，不能拼成一次真实运行的同对象事实。trace_audit.py逻辑位于finish.py，从原始事件核set/remove期间映射和锁、全组清理先于erase；全部whole_path仍为insufficient。对象角色/要求由人工选定，非自动N1或统一检查器。

统计：本轮1次成功局部编译、9次程序执行；另2次失败编译（首次提取误匹配API注释且输出GBK解码失败，第二次诊断重现），失败脚本/C/build保留；记录脚本另有2次字面锚点断言失败，未写工作文档，按实际变量名修正；改提取锚点与字节捕获后原函数体不改。无新内核启动、设备、项目模型调用或新缺陷；独立正例/正常0/0。证据linux_bug_analyze/experiments/case_taxonomy/smmu_lifecycle_20261026/。

下一步仍为SMMU：优先核真实mm失效范围来源与可达宽度、编码截断条件；生命周期还缺实际调用者的mm引用、设备静默、并发回调/CD释放及真实合法组配置，不能由上述回放填补。virtio深分析随后，其他扩展暂缓，表示接口/R3暂缓、VT-d后置不变。Word未改。日志、待办、进展、交接同轮维护，WSL三镜像以notes_sync.json为准。

以下为历史记录，以本节及用户最新指示为准。

'''
body=body.replace('trace_audit.py逻辑位于finish.py','事件审核逻辑位于finish.py')
(H/'README.md').write_text('# SMMU附着/撤销生命周期有界补证\n\n'+body+'\n运行：Windows Python run.py（首轮生成）、finish.py（一次性审核与记录）。保留 run_failed.py/transaction_failed.c/function_manifest.json 为失败材料，采用 function_manifest_fixed.json。设备回调、xarray、锁、列表均为替身，锁状态不是并发证明。\n',encoding='utf-8')
before=json.loads((H/'notes_before.json').read_text(encoding='utf-8'))['before_sha256'];after={}
for n,d in before.items():
 p=R/n;assert sha(p)==d
 title,rest=p.read_text(encoding='utf-8').split('\n',1);p.write_text(title+'\n\n'+body+rest.lstrip(),encoding='utf-8');after[n]=sha(p)
save('notes_update.json',dict(before_sha256=before,after_sha256=after))
with (R/'日志/2026-10-26.md').open('a',encoding='utf-8') as f:f.write('\n'+body)
save('delivery_manifest.json',{p.name:sha(p) for p in H.iterdir() if p.is_file() and p.name not in ['delivery_manifest.json','notes_sync.json']})
print('Evidence packet and three working notes updated; whole path insufficient.')

