from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;R=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
rows=json.loads((H/'results.json').read_text(encoding='utf-8'));audit=[]
for r in rows:
 lines=r['stdout'].splitlines();mode=r['mode'];result=list(map(int,lines[-1].split()[1:]));done,alloc,install,adds,frees,barrier,init_sync,install_sync,clear_sync,warnings=result
 if mode==1:assert install==barrier==frees==done==0 and 'ALLOC_FAIL' in lines
 else:
  assert lines.index('BARRIER_CALL')<next(i for i,l in enumerate(lines) if l.startswith('INSTALL '))
  if mode in [2,3]:assert lines.index('INSTALL 0')<lines.index('FREE_PRIVATE') and frees==1
  else:assert 'INSTALL 1' in lines and frees==0
 if mode==2 and r['queued']:assert adds==0
 if mode in [0,4]:assert adds==(1 if mode==4 else 2)
 audit.append(dict(shift=r['shift'],mode=mode,coherent=r['coherent'],queued=r['queued'],local_branch='pass',free_role='unpublished_private_table' if frees else 'no_free',walk_invalidation_required_for_this_private_free=False if frees else None,hardware_ordering='insufficient',whole_path='insufficient'))
save('branch_audit.json',audit)
save('method_update.json',dict(rule='Classify table publication state and mapping purpose before applying release/invalidation requirements',paths={'nonleaf_removal':'published child: clear parent -> walk flush return -> free (previous round)','split_install_success':'initialize remaining mappings -> barrier call -> install -> leaf ADD; no walk callback in tested level2 split','split_install_loss':'free unpublished new table; reuse observed winner table and recurse if table','allocation_failure':'zero bytes unmapped, old block preserved','gather':'adjacent same-size ADD accumulates; explicit sync emits leaf=true, disjoint/granule change syncs previous range'},scope='level2-to-level3 split; cmpxchg interleavings injected not real concurrency; DMA barriers mocked',not_a_new_defect=True))
body='''## 10月26日 最新进展：SMMU block split、安装分支与leaf gather闭环

继续上一轮原walker：新增原__arm_lpae_init_pte、arm_lpae_install_table、arm_lpae_split_blk_unmap函数体，保留原unmap递归。3种页配置×5分支×coherent/queued执行60组，覆盖成功安装、分配失败、模拟其他表已安装、模拟目标变空及表尾截断；逐项检查保留下来的每个页描述符映射以及应删除的空项。cmpxchg结果是定点注入，非真实并发；分配、DMA屏障/同步、地址映射和回调仍替身。原install中的barrier调用先于cmpxchg已观察，不证明硬件内存序。

机制结论：成功split安装后直接调用页级ADD（本路径即使queued也调用）；遇已有表则释放未发布的私有新表，再递归unmap，queued会影响递归leaf的ADD；观察到非表时释放私有新表并返回0。分配失败返回0且原block保持。此处私有表从未成功发布，其释放不能套用上一轮“已发布子表删除前先walk失效”的规则。规则必须绑定对象发布状态和调用用途，不是只匹配free函数名。

随后提取原gather init/sync/disjoint/add_range/add_page及SMMU page_nosync/iotlb_sync，另编译1份，执行30组来自split的实际ADD序列及2项构造边界。连续同粒度ADD在最终显式sync之前不调用范围失效；最终sync转换为leaf=true、inclusive end减start加1的范围并重置gather。不连续/粒度变化先同步旧范围。页级ADD不等于立即发命令，queued字段也不是通用add_page内部的直接拒收条件。范围失效末端为观测替身，未执行设备命令/全内核调用者。

自动核验新增branch_audit.json（60组）和method_update.json：区分published child删除、unpublished private分配清理、成功split的leaf gather，保留hardware_ordering/whole_path不足。未合并成统一检查器，仍依赖人工语义分类。gather提取脚本首次因跨行bool签名未匹配而在编译前停止，失败脚本保留，修正提取匹配后通过；没有修改原函数体或重算成独立发现。

下一项：对SMMU方法做有界阶段评审，汇总已覆盖的SVA单页、walk删除、split/leaf gather用途及对象/阶段/观测器前提，检查是否仍有会改变判定的局部缺口；输出明确支持范围和剩余真实平台成本，再决定是否转入virtio深分析。不是宣告接口全完成，不继续无限扩大函数组合。SVA真实绑定受现有SSID平台限制，物理设备完成、实际并发、完整allocator/map仍缺；表示接口/R3暂缓、VT-d后置不变。

统计：4次局部编译、92次程序执行（60 split+30派生gather+2构造边界），另60项分支审核。无新QEMU/内核启动、设备操作、项目主分析调用或新缺陷，独立正例/正常0/0。证据linux_bug_analyze/experiments/case_taxonomy/smmu_split_20261026/（manifest、builds、results、gather_build、gather_results、branch_audit、method_update）。Word未改；日志、待办、进展、交接同轮维护，WSL三镜像以notes_sync.json为准。

以下为历史记录，以本节及用户最新指示为准。

'''
(H/'README.md').write_text('# SMMU block split与leaf gather\n\n'+body+'\n模式：0成功，1分配失败，2比较交换观察已有表，3比较交换观察空项，4表尾截断。模拟竞争仅固定一次比较交换返回；未验证锁自由并发正确性。宿主PTE容器及比较交换替身不能作真实物理地址/架构运行证据。\n',encoding='utf-8')
before=json.loads((H/'notes_before.json').read_text(encoding='utf-8'))['before_sha256'];after={}
for n,d in before.items():
 p=R/n;assert sha(p)==d
 title,rest=p.read_text(encoding='utf-8').split('\n',1);p.write_text(title+'\n\n'+body+rest.lstrip(),encoding='utf-8');after[n]=sha(p)
save('notes_update.json',dict(before_sha256=before,after_sha256=after))
with (R/'日志/2026-10-26.md').open('a',encoding='utf-8') as f:f.write('\n'+body)
save('delivery_manifest.json',{p.name:sha(p) for p in H.iterdir() if p.is_file() and p.name not in ['delivery_manifest.json','notes_sync.json']})
print('Split, install and gather mechanism recorded; published/private role distinction added.')
