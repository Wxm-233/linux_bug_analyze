from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;R=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
body='''## 10月26日 最新闭环：SMMU范围失效接口的分层判定

按用户确认的其他接口优先安排，完成SMMU有界方法整理与函数层复核。WSL从/root/repos/linux读取固定父/修复版本源码，4份源码与已有归档正文/Git blob相符；重新编译旧版、修复版及两个明确构造变体，共4个主机函数测试程序、336组执行。新结果与历史smmu_range_result.json逐字段一致，本轮额外保留实际编译C、环境/参数和逐条命令原始stdout。没有完整内核构建/启动、真实设备或项目模型调用。

**判定方法：**分别登记请求范围覆盖R1、范围命令全零TTL/Num/Scale组合限制R2、non-leaf未知层级TTL语义R3。新audit.py不调用旧assess，而从原始字段重新计算区间并集与条件关系；仍依赖人工登记的命令公式及已知修复依据，不是独立金标准。非范围模式下R2不适用；leaf或非范围模式下R3不适用。扩大范围许可及设备执行均另报不足。

**结果：**每个实现84组，均满足登记模型下的覆盖。旧版9组违反R2；只处理单页变体仍6组违反R2；只改TTL变体没有R2违规，却有21组违反R3；修复版两项违规均0、9组额外覆盖一页。数字按测试输入组合计，不是独立案例或新缺陷。1/33/65页边界说明只看单页请求不足；正常大小、leaf和关闭范围模式分别检验不同条件，关闭功能不等于目标路径正确。

**证据边界与研究范围：**主机函数体使用结构/队列替身，尚未执行SVA调用链、真实cmdq位编码或设备完成。4/16/64K为参数差异，非三种ARM64内核运行，更非跨CPU架构验证；此例是架构相关设备协议边界。规范依据限固定源码与修复说明，尚未独立核硬件规范、超范围失效许可和全部errata。旧断言num<=30不能直接当完整硬件合法域。部分历史中文说明乱码，本轮使用可核英文源码/提交说明，不依赖乱码陈述。

**对自动化的增量：**积累条件化的多关系判定机制：范围覆盖不保证编码合法，修补编码也可能破坏未知层级用途。程序负责原件、字段和有限关系；人工提供用途、协议与合法输入，模型本轮未调用。未建统一入口，不宣称自动要求推导或独立检测效果已完成。

**停点和下一项：**SMMU函数层方法阶段收束，保留硬件规范、调用者可达性、设备效果及迁移缺口；下一项推进virtio DMA布局/缓存隔离，核首尾边界、缓存粒度及DMA后端条件。CPU拓扑、Btrfs继续保留既有缺口，表示接口/shmem R3暂缓、VT-d后置。旧N2.24或CPU信息导出不覆盖当前排程。

统计：本轮新增4次函数编译、336组既有输入重执行（含构造变体），不是新增历史内核运行；新缺陷0、项目模型0，独立正例/正常样本仍0/0。证据入口linux_bug_analyze/experiments/case_taxonomy/smmu_method_20261026/：README.md、results.json、replay_check.json、raw_commands.json、sources.json、source_audit.json、relation_audit.json、builds.json、environment.json及四份C。Word未改；日志/待办/进展/交接已维护，三份WSL镜像以本目录notes_sync.json成功回执为准。

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
print('SMMU method, daily log and three notes updated.')
