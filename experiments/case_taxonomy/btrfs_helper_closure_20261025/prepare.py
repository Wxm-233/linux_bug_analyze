from pathlib import Path
import json,hashlib,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE.parent
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):(HERE/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
out=ROOT/'模型调用测试/2026-10-25/btrfs_kimi_helper_closure';out.mkdir(exist_ok=False)
old=BASE/'btrfs_path_closure_20261025';oldmat=read(old/'materials.json')
for d in oldmat['documents']:assert sha(Path(d['path']))==d['sha256']
previous=ROOT/'模型调用测试/2026-10-25/btrfs_kimi_k3_longwait/prompt.md'
assert sha(previous)==oldmat['prompt_sha256']
old_sections='\n## DOCUMENT '+previous.read_text(encoding='utf-8').split('\n## DOCUMENT ',1)[1]
inventory=BASE/'btrfs_stability_inventory_20261024';inv=read(inventory/'inventory.json')['versions'][0]
assert inv['mode']=='parent'
for name in ('fs/btrfs/disk-io.c','fs/btrfs/volumes.c'):
 item=inv['files'][name];assert sha(inventory/item['artifact'])==item['sha256']
raw=ROOT/'linux_bug_analyze/analysis_out/btrfs-consumer-observation-20261024'
entry=read(raw/'manifest.json')[0];assert entry['mode']=='parent'
assert sha(raw/'parent/kernel.config')==entry['artifacts']['kernel.config']
selection=[('new_disk',inventory/'source_inventory/parent/fs/btrfs/disk-io.c',[(2544,2736),(3264,3320)]),
 ('new_vfs',old/'source/fs/super.c',[(652,675),(939,1010)]),
 ('new_super',old/'source/fs/btrfs/super.c',[(1329,1387),(1655,1737)]),
 ('new_volumes',inventory/'source_inventory/parent/fs/btrfs/volumes.c',[(398,423),(530,605),(1230,1264),(1310,1319)]),
 ('new_ctree',old/'source/fs/btrfs/ctree.h',[(1623,1634),(2380,2440),(3630,3650),(3827,3855)]),
 ('actual_config',raw/'parent/kernel.config',[(535,545),(1207,1217)]),
 ('review_facts',BASE/'btrfs_kimi_longwait_20261025/review_facts.json',None)]
docs=[];sections=[]
for ident,p,spans in selection:
 lines=p.read_text(encoding='utf-8').splitlines();spans=spans or [(1,len(lines))]
 docs.append(dict(id=ident,path=str(p),sha256=sha(p),spans=spans))
 sections.append('\n## DOCUMENT '+ident)
 for lo,hi in spans:
  assert 1<=lo<=hi<=len(lines)
  sections.append('\n'.join(f'{n}: {lines[n-1]}' for n in range(lo,hi+1)))
task='''这是用户授权的Kimi-K3第二轮Btrfs源码主分析，仍为已读开发案例，不是盲测。父版0d977e0eba234e01a60bdde27314dc21374201b3、实际ARM64 64K构建、单设备、成功新挂载、flags=0且选项只有max_inline=2048/8192。附件保留旧原材料并补充指定缺口。请直接给可复核分析，不输出隐藏思维过程。
前轮纠错：实际kernel.config明确CONFIG_BLK_DEV_ZONED未启用，btrfs_is_zoned函数体仍存在；不能由helper存在推配置y，不能由预处理推单一机器指令。observer:788缓存保存、789消费、795后采样是不同事件；原C要求消费时刻的参考值，绝不能把deadline改为采样时刻。函数名不是副作用证明。
已有实验范围：父/修复及诊断合计8个完整parse区间，登记虚拟地址上的sectorsize/指针槽无写记录，正控制有自然max_inline写；只有单CPU TCG调试执行。该范围不能排除别名/DMA，也不证明未登记入口；不要重复建议同格观察点，除非提出与既有监测不同且有必要性的区间缺口。
本轮任务：
1.依据新提供的btrfs_validate_mount_super/validate_super完整函数体，逐项划分目标字段/对象的直接效果、callee作用和外部语义假设。指出成功路径上是否仍可能执行warn/logging，哪些具体作用需要补证；不得只因命名是validate而判只读，也不要无区别追索所有内核函数。
2.核do_emergency_remount_callback/do_thaw_all_callback及fill_super→open_ctree链；说明是否闭合原G1/调用边，各自依赖哪些条件。核forget_devices及stale_devices路径能否影响正在挂载的fs_info/super_copy，缺对象关系则保留未知。
3.严格区分[复制完成→parse入口]、[parse入口→缓存消费]、[消费→后采样]三段。对每段列对象/目标字段、已有保证、正常内核执行假设、仍缺证据。不要把扩大时间范围当成原C的必要条件，也不要缩短原消费期限。
4.给出有限候选检查表：某缺口已补/仍不足/不适用及引用。可以提出有显式前提的条件性结论，但前提未验证就不能写无条件supported。分别回答已有局部关系、原C、whole_path能判到哪一级，指出真正最小下一步。
只引用DOCUMENT已提供行，不猜省略段。新引用可用new_disk:L2544等格式。正文建议聚焦在上述三项缺口和三段区间，不复述全部旧分析。返回完整可读正文，无需强制JSON。
'''
prompt=task+old_sections+'\n'.join(sections)
(out/'prompt.md').write_text(prompt,encoding='utf-8',newline='\n')
save('materials.json',dict(old_materials=oldmat['documents'],new_documents=docs,prompt_sha256=sha(out/'prompt.md'),output=str(out),manual_selection=True))
template=(ROOT/'模型调用测试/2026-10-25/run_kimi_btrfs_longwait.py').read_text(encoding='utf-8')
template=template.replace("OUT=HERE/'btrfs_kimi_k3_longwait';OUT.mkdir(exist_ok=False)","OUT=HERE/'btrfs_kimi_helper_closure';assert OUT.is_dir() and not (OUT/'receipt.json').exists()")
template=template.replace("source=HERE/'btrfs_actual_path_closure_authorized_retry/prompt.md'","source=OUT/'prompt.md'").replace('prompt_unchanged=True','prompt_unchanged=False')
runner=ROOT/'模型调用测试/2026-10-25/run_kimi_btrfs_helper.py';assert not runner.exists();runner.write_text(template,encoding='utf-8')
names=['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']
save('notes_before.json',dict(before_sha256={n:sha(ROOT/n) for n in names}))
shutil.copyfile(BASE/'new_input_contract_trial_20261017/sync_work_notes.py',HERE/'sync_work_notes.py')
print(json.dumps(dict(new_documents=len(docs),prompt_bytes=len(prompt.encode()),prompt_sha256=sha(out/'prompt.md'))))
