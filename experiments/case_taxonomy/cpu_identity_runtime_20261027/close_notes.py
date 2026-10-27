"""Update daily record, three working notes and family plan with SHA guards."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
OUTER=HERE.parents[3]

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def need(value,reason):
    if not value: raise ValueError(reason)

SECTION='''## 10月27日 最新进展：CPU身份／限额的ARM64真实启动正常对照

按待办核CPU身份、映射和启动范围的既有结果。旧SPARC 12条局部投影、映射试用、平台限额24条投影和作用事实组件均已做过，保留其真实层级和失败正常资格。本轮实际新增一组ARM64开发正常对照：独立归档固定db191ba0c8564ff84877e5b1c9553e991feca239源码，复用既有SMP/NR_CPUS=512/OF/PROC/SYSFS且无hotplug配置，仅LOCALVERSION改变；14份关键原文核Git blob。arch/arm64/kernel/smp.c与kernel/smp.c只增加映射、MPIDR、mask、上限和阶段日志，不改选择/映射/setter。1次新Image构建50.609秒首次成功，1次静态PID1编译首次成功。

平台资格未凭请求参数猜测。原最多2次DT试验（4 CPU/2 cluster、9 CPU）均得到连续硬件编号，未通过稀疏正常对照资格，按原计划先停，保留platform_v1_stop，尚未构建/启动Linux。随后核QEMU8.2.2上游virt/GICv3/affinity源码，单独冻结v2：16个目标编号后产生高层affinity，因此只增加一次17 CPU设备树试验，实际得到0..15、256后再冻结四个启动条件。上游全文归档HTTPS读取45秒超时、无模型调用且未重试下载；URL/行范围与浏览核查依据保留。Ubuntu QEMU二进制未核同源码blob，最终以实际DT和guest寄存器为准。

同一个6.19.0-rc2-lba-cpu-identity镜像/config/initrd，在QEMU virt/GICv3/cortex-a57/17 vCPU/512MiB/TCG完成4次真实Linux启动，均到PID1挂载proc/sysfs、读实际CPU节点和集合、正常关机。baseline：nr_cpu_ids 512→17，possible/present/online均0–16；nr_cpus=2：2→2、三集合均0–1；maxcpus=2：512→17、possible/present仍0–16、online仅0–1；nr_cpus=3 maxcpus=2：3→3、possible/present0–2、online0–1。NR_CPUS始终512、kernel_max始终511，分别记录为编译容量和运行逻辑上界/集合/激活数量，不混用。

baseline的逻辑CPU16映射到硬件256，实际MPIDR也为256；23条按运行重复计的boot/secondary硬件记录均覆盖对应online CPU并与映射一致。nr_cpus=2时logical16→256等未选中map槽仍有效，却不在当前运行域；probe仅对域内CPU调用mask API，域外标-1未知。由此不能要求原始硬件编号等于逻辑编号、所有有效map槽都possible或present等于online。这是一个已读方向、特定虚拟平台/正参数配置的实际正常见证，非裸机、同版本跨ISA配对或独立正常评价。

新增有限观测适配器绑定Image/config/initrd/console SHA、PID1、实际参数、DT reg、阶段/映射窗口和寄存器记录。程序投影映射来源/完整性/单射、实际硬件相符、重定界后的逻辑上界、激活域及正名额、possible选择上限，交不变公共核心；4格×5关系=20项均满足，deadline和whole_path保持不足。关系/角色/正常资格由研究者审核，适配器在读开发数据后实现；不是N1自动推导或盲测。

同一映射关系经“SPARC cpuid直接作位索引”的另一事实适配器，只读回验旧12条原始stdout/JSON：父版2满足/4违反，修复6满足；数量上限12条均满足。12记录×两关系为24次核心回验，不是24个新运行/案例，不升级SPARC实际配置、完整启动或早期高位API合法性。局部复用说明namespace和映射必须显式绑定，未建立统一入口/完整自动检查器；先前Xen/LoongArch及CPU设备注册的失败准入不因本正常见证而改变。

最终12个构造控制全部符合预期：6个缺记录/身份/阶段控制及1个未知语义审核账本均不足；5个明确synthetic反例（错误直映namespace、重复target、实际硬件错配、借早期容量当后期上界、借possible数量当online数量）均违反，未冒充kernel观察或新缺陷。首控制驱动误用origin=synthetic被原核心拒绝，保存controls_attempt1，改用原协议synthetic_assumption后通过，未改核心。最终新增核心26次、旧回验24次，首协议拒绝1次单列，全轮51次；调用数不是检测准确率。

阶段状态：CPU身份/范围已补ARM64实际正常对照及共享关系的有限适配，接口仍进行中。下一步仍核固定SPARC历史版本的固件身份→possible构造→实际per-CPU/IRQ等消费链，明确合法cpumask前提和阶段，并评估真实启动/工具限制；当前WSL没有qemu-system-sparc64或sparc64-linux-gnu-gcc，尚未开展SPARC内核构建/启动。ARM64对照用于检验过强要求及迁移边界，不能替代正例全链、物理真值或独立评价。表示/R3暂缓、VT-d后置，CPU导出/拓扑、SMMU和virtio开放项保留；Kimi大请求停点未重试。

统计：1个新内核Image构建、1个PID1编译、4次合格guest启动；另3个仅DT导出的QEMU进程，合计7个QEMU进程。项目外部源码模型API请求0，新确认Linux缺陷0，独立正例/正常仍0/0。证据linux_bug_analyze/experiments/case_taxonomy/cpu_identity_runtime_20261027/：原/v2计划、三个DT和失败收据、14源manifest、instrumentation/observed_sources、kernel.config、build_complete/kernel_inputs、runs四格原日志、analysis新正常/旧投影的事实契约结果、checking_policy、controls、delivery_manifest。WSL新独立缓存/root/.cache/linux-bug-analyze/cpu-identity-runtime-20261027，Git/root/repos/linux；旧virtio/CPU缓存未改，工作区仍Windows挂载，无独立/root/repos/linux_bug_analyze副本。日志、待办、进展、交接及家族规划同轮更新，三份WSL镜像以notes_sync成功收据为准；Word未改。

以下为历史记录，以本节及用户最新指示为准。

'''

def main():
    target=HERE/'notes_update.json'; need(not target.exists(),'preserve_notes_update')
    before=json.loads((HERE/'notes_before.json').read_bytes())['before_sha256']
    for name,digest in before.items(): need(sha(OUTER/name)==digest,'work_note_changed_during_round:'+name)
    plan=OUTER/'接口验证后续规划.md'; need(sha(plan)==sha(HERE/'plan_before.md'),'family_plan_changed_during_round')
    text=plan.read_text(encoding='utf-8')
    old='| 拓扑与die导出两用途限定方法已整理；导出已补工件到发布样本，身份/范围继续复核；非全家族完成 |'
    new='| 拓扑与die导出两用途限定方法已整理；身份/范围新增ARM64实际正常对照，继续SPARC正例消费/合法性；非全家族完成 |'
    need(text.count(old)==1,'CPU_family_status_row_not_unique'); text=text.replace(old,new)
    old='历史x86/s390运行、局部函数与组件；集合覆盖、准备资格/期限、来源资格、编号域/数量限制'
    new='历史x86/s390运行、ARM64映射/限额4格实际启动、局部函数与组件；集合覆盖、准备资格/期限、来源资格、编号域/数量限制'
    need(text.count(old)==1,'CPU_family_evidence_row_not_unique'); text=text.replace(old,new)
    old='拓扑精确消费与锁对象/稳定窗口；导出政策适用范围；身份路径真实启动及正常资格。不同用途分别登记'
    new='拓扑精确消费与锁对象/稳定窗口；导出物理真值/历史文本；SPARC正例实际消费/合法配置/真实启动，ARM64正常仅限本配置；独立评价未做'
    need(text.count(old)==1,'CPU_family_gap_row_not_unique'); text=text.replace(old,new)
    marker='\n## 当前执行顺序\n'; need(text.count(marker)==1,'execution_heading_not_unique')
    addition='| 2026-10-27 | CPU／身份映射与选择／激活限额 | 子阶段完成：新建1内核/1PID1、4格ARM64真实启动，逻辑16→硬件256及nr_cpus/maxcpus差异；20关系通过，旧SPARC12投影回验；linux_bug_analyze/experiments/case_taxonomy/cpu_identity_runtime_20261027/ | 7缺证拒判/5显式合成反例；namespace/依据/支持域人工，独立0/0。接口继续核SPARC实际消费与合法配置/启动可行性，非跨ISA受控复现 |\n'
    text=text.replace(marker,addition+marker)
    start=text.index(marker)+len(marker)
    while text[start]=='\n': start+=1
    end=text.index('\n\n',start)
    text=text[:start]+('CPU身份与启动范围进行中：ARM64已补一个实际虚拟平台/正参数范围的4格正常对照，同一映射关系用不同适配器回验旧SPARC投影。下一项核SPARC固定历史版本固件身份、possible构造与实际per-CPU/IRQ等消费者，确定合法cpumask前提及阶段，并评估真实启动/工具限制；尚无新的SPARC构建或启动。旧映射/平台/独立准入结果保持原资格。CPU导出、拓扑、SMMU及virtio未决项挂账；表示/R3暂缓、VT-d后置不变。')+text[end:]
    for name in before:
        path=OUTER/name; title,rest=path.read_text(encoding='utf-8').split('\n',1)
        path.write_text(title+'\n\n'+SECTION+rest.lstrip('\n'),encoding='utf-8')
    plan.write_text(text,encoding='utf-8')
    log=OUTER/'日志/2026-10-27.md'
    with log.open('a',encoding='utf-8') as f: f.write('\n\n'+SECTION.replace('以下为历史记录，以本节及用户最新指示为准。\n\n',''))
    target.write_text(json.dumps({'before_sha256':before,'after_sha256':{name:sha(OUTER/name) for name in before},
        'family_plan_sha256':sha(plan),'daily_log_sha256':sha(log)},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'updated_notes':len(before),'daily_log':'2026-10-27.md','family_plan':True}))

if __name__=='__main__': main()
