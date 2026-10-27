from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent;R=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
S=H.parent/'s390_arch_contract_20261013/runtime/observer_sources'
anchors=[]
for file,needle in [('old/arch/s390/kernel/topology.c','if (!cpu_online(cpu))'),('fixed/arch/s390/kernel/topology.c','if (!cpumask_test_cpu(cpu, &cpu_setup_mask))'),('fixed/arch/s390/kernel/smp.c','cpumask_set_cpu(cpu, &cpu_setup_mask);'),('old/kernel/sched/core.c','o->mask = cpumask_bits(smt_mask)[0];')]:
 p=S/file;lines=p.read_text(encoding='utf-8').splitlines();hits=[i+1 for i,t in enumerate(lines) if needle in t];assert hits
 anchors.append(dict(path=str(p.relative_to(R)).replace('\\','/'),sha256=sha(p),needle=needle,lines=hits))
save('source_anchors.json',anchors)
body='''## 10月26日 最新闭环：CPU拓扑判定方法、归档复核与机制比较

按先积累各接口判定方法的方向，完成CPU拓扑（非全部CPU接口）的方法档案，并与Btrfs比较。原CPU-B驱动仅在内存中重定向新输出，原方法、适配器、契约核心和历史输入输出均未改；方法清单及38份旧归档输入SHA核验通过，4份历史运行和16项证据控制重算结果与旧results_v2逐字段一致。源码原文再核online/setup资格、通知前准备顺序及锁前采样位置。

**实质结论：**旧s390的采样集合不含目标CPU，其余三格包含；四格采样时均online=0、最终集合均含目标。因此最终状态或统一online要求都不能替代该用途的阶段判定。旧提供者使用online资格，修复使用setup资格，说明准备调用提前不等于目标被接受并完成准备。样本成员、消费时刻覆盖和实际锁对象保护分开；四格期限与whole_path仍不足，逻辑CPU绑定、锁次数和rq_self不证明全部物理锁别名与稳定窗口。

**自动化分工：**原程序核原件/配置/事件/字段并调用既有关系核心；用途、角色、权威、期限及提供者语义仍是研究者输入。每格7类required_claims、11条ledger claim和13个绑定工件仅为输入规模，跨格共享，不是独立证据数、已证明命题数或工时。专用适配器只支持4个profile，未改名包装成通用检测器。16项缺证/身份/时刻变异均仍不足；属于旧开发控制，不是新增Linux案例。未重跑旧单元测试，不重计测试数量。

**跨机制比较：**CPU是集合覆盖、对象资格和锁关系；Btrfs是数值裁剪、权威几何及文件路径门禁。可复用候选是身份/用途/阶段登记、关系与证据分层、缺证规则；来源资格摘要、集合/数值语义和观测适配仍专用。两类都不能把相邻采样或最终成功提升为消费期限保证。该比较支持长期统一方向，不证明自动提取已通用，也没有新建统一入口。

**下一步：**限定已有开发材料，整理CPU信息导出的来源资格与用途政策，先核材料/接触史、信息源选择依据及正常路径，再判断是否形成区别于准备期限的新机制。旧N2.24独立材料计划作为后续保留，不越过10月25日用户确认的先积累机制安排。Btrfs期限参考缺口挂账；表示接口/R3继续暂缓、VT-d后置；不自动启动付费模型或新内核矩阵。

本轮新增模型/构建/启动/缺陷均0，独立正例/正常样本仍0/0；4份历史运行、16项控制与38份归档输入分开统计。证据入口：linux_bug_analyze/experiments/case_taxonomy/cpu_method_20261026/（README.md、replay.json、summary.json、inputs.json、source_anchors.json）。本轮Word未改。日志及三份持续文档同步更新，Windows/WSL一致性以本目录notes_sync.json成功回执为准。

以下为历史记录，以本节及用户最新指示为准。

'''
before=read(H/'notes_before.json')['before_sha256'];after={}
for n,d in before.items():
 p=R/n;assert sha(p)==d
 text=p.read_text(encoding='utf-8');title,rest=text.split('\n',1)
 p.write_text(title+'\n\n'+body+rest.lstrip(),encoding='utf-8');after[n]=sha(p)
save('notes_update.json',dict(before_sha256=before,after_sha256=after))
with (R/'日志/2026-10-26.md').open('a',encoding='utf-8') as f:f.write('\n'+body)
save('delivery_manifest.json',{n:sha(H/n) for n in ['README.md','run.py','finish.py','replay.json','summary.json','inputs.json','source_anchors.json']})
print('Method, source anchors, daily log and three notes saved.')
