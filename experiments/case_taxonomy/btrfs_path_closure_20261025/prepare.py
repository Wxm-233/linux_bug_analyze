from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
prior=json.loads((HERE.parent/'btrfs_stability_resume_20261024/results.json').read_text(encoding='utf-8'))
assert prior['cumulative_conservative_accounting']+200000<=1000000
out=ROOT/'模型调用测试/2026-10-25/btrfs_actual_path_closure';out.mkdir(parents=True,exist_ok=False)
selection={'fs/btrfs/super.c':[(564,606),(775,801),(1538,1557),(1638,1805),(2390,2430)],
 'fs/btrfs/ctree.h':[(224,275),(1033,1040),(1420,1450),(1623,1634),(2390,2410),(3690,3715)],
 'fs/btrfs/free-space-cache.c':[(3930,3975)],'fs/btrfs/zoned.h':[(65,102),(230,260),(280,320)],
 'fs/super.c':[(200,250),(380,430),(570,745),(780,850),(950,1010),(1480,1540)],
 'fs/fs_context.c':[(590,650)],'fs/namespace.c':[(970,1048)],
 'include/asm-generic/unaligned.h':[(1,80)],'lib/string.c':[(655,700)],
 'lib/parser.c':[(30,180),(350,370)],'lib/cmdline.c':[(138,182)]}
manifest=json.loads((HERE/'manifest.json').read_text());docs=[];sections=[]
def add(docid,p,spans,expected=None):
 raw=p.read_bytes();h=hashlib.sha256(raw).hexdigest()
 if expected:assert h==expected
 lines=raw.decode('utf-8').splitlines();spans=[(lo,min(hi,len(lines))) for lo,hi in spans]
 for lo,hi in spans:assert 1<=lo<=hi<=len(lines)
 docs.append(dict(id=docid,path=str(p),sha256=h,spans=spans))
 sections.append('\n## DOCUMENT '+docid+'\n')
 for lo,hi in spans:sections.append('\n'.join(f'{n}: {lines[n-1]}' for n in range(lo,hi+1)))
for item in manifest:add(item['path'].replace('/','__'),HERE/'source'/item['path'],selection[item['path']],item['sha256'])
old=HERE.parent/'btrfs_stability_inventory_20261024'
add('disk',old/'source_inventory/parent/fs/btrfs/disk-io.c',[(2968,3018),(3188,3340),(3515,3585)])
raw=ROOT/'linux_bug_analyze/analysis_out/btrfs-consumer-observation-20261024/parent'
add('observer',raw/'super.observed.c',[(780,805)])
add('preprocessed',raw/'super.i',[(57000,57090),(63285,63310),(68100,68160)])
intro='''你是Linux接口契约研究的主源码分析者。本轮只研究父版0d977e0eba234e01a60bdde27314dc21374201b3在实际ARM64/64K构建、单设备、成功新挂载、用户传入max_inline=2048或8192且flags=0时，缓存消费到后采样磁盘参考的稳定性。已有init源SHA、initrd和boot绑定；选项无前置其他用户选项，不由cache=4096推断路径。先前模型提出“cache=4096可排除remount”已被研究者拒绝，禁止复用。
本轮提供实际路径前置helper、unaligned完整宏、VFS访问与legacy挂载链新材料，预处理片段来自同一父版观测构建。observer先缓存request/cache并min写回，再读super_copy磁盘sectorsize。全局无写者尚未证明；不要预设所有引用者都可访问或都被锁阻塞，不把const/static inline等同全局无副作用。省略区间未提供，不得填补成事实。
任务：1.逐段闭合getter到读取指令语义及parse前置实际分支，区分源文件和实际配置预处理；哪些helper只读、哪些写不同字段、哪些仍未知，逐项引证。2.从legacy_get_tree、btrfs_mount、vfs_kern_mount/fc_mount/sget到parse梳理新对象绑定、登记、锁保持及可访问入口，指出哪些锁与SB_BORN机制可实际排除所列入口，哪些入口未覆盖。3.给出有限审计范围下可支持的最强参考稳定性结论，不要求假想任意内存破坏不存在作为无穷追索，但要明确正常内核执行假设和审计范围。4.必要的最小下一实验：是否单次写观察点值得做；监控哪些地址/区间、如何验证无漏报与身份；不要用点值相等推断无中间写入。5.给出机器检查准入表，严格分来源证据/研究者语义/条件假设/仍不足，明确是否足以提升C的消费期限状态。
每条实质判断引用DOCUMENT原行号。输出紧凑结论表、证据、最小剩余缺口；只给可复核结论和简洁理由，不输出隐藏思维过程。不得把本例算独立发现或完整自动分析。
'''
prompt=intro+'\n'.join(sections)
(out/'prompt.md').write_text(prompt,encoding='utf-8',newline='\n')
save=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
save(HERE/'materials.json',dict(documents=docs,output=str(out),prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),bytes=len(prompt.encode()),prior_accounting=prior['cumulative_conservative_accounting'],reservation=200000,cumulative_reserved=prior['cumulative_conservative_accounting']+200000))
names=['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']
save(HERE/'notes_before.json',dict(before_sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}))
print(json.dumps(dict(bytes=len(prompt.encode()),documents=len(docs),reserved=965430)))
