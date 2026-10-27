"""Update daily log, three working notes and family plan with SHA guards (run once)."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
OUTER = HERE.parents[3]
NOTES = ['当前代办.md', '当前研究方向与进展.md', '项目研究与文档写作交接说明.md']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def need(value, reason):
    if not value:
        raise ValueError(reason)


SECTION = '''## 10月27日 最新进展：SPARC64身份→IRQ栈/per-CPU消费链及cpumask位宽前提

按下一项待办核固定SPARC历史版本（父版95706e717c4f55ca62025c151451ccc28863d085、修复98937707fea8375e8acea0aaa0b68a956dd52719，主线df2908090cda同修复写法）的固件身份→possible→实际消费链。源码链：setup_arch先解析nr_cpus并把nr_cpu_ids降为L，paging_init中record_one_cpu以固件cpuid直接作位索引设present/possible，父版再改写为连续前缀；随后alloc_irqstack_bootmem在setup_nr_cpu_ids之前以for_each_possible_cpu分配软/硬中断栈；之后重定界、per-CPU偏移，smp_init遍历present并由cpu_up拒绝非possible。handler_irq的set_hardirq_stack直接取hardirq_stack[smp_processor_id()]切栈。

关键前提是cpumask位宽分支。10/21旧投影只用NR_CPUS=8（small_cpumask_bits=NR_CPUS），并已注明多字/动态位图未覆盖；本轮核sparc64 Kconfig默认NR_CPUS=4096、defconfig未覆盖，属于small_cpumask_bits=nr_cpu_ids分支，cpumask_weight与for_each_cpu只看当时nr_cpu_ids以内的位。修复版“num_possible_cpus() < nr_cpu_ids”因此不会被L以外的稀疏cpuid计入，IRQ栈分配也只遍历L以内的位。

平台可行性已查：QEMU上游v8.2.2的sun4u/sun4v（sun4u.c 813/841行）和niagara（166行）均max_cpus=1，niagara另装载1up单CPU镜像，原文与SHA存platform_sources。当前QEMU路线不能给出多CPU稀疏cpuid SPARC64 guest，单CPU启动不能触发关系；qemu-system-sparc与gcc-sparc64-linux-gnu未安装，本轮未安装任何软件包。

逐字提取13段原函数（9段编入执行），宿主投影只替身cpumask/bitmap、memblock、per-CPU和cpu_up首个possible检查；S64/L4096两位宽×父/修复共4次编译首次成功，{0,1}/{0,2}/{0,2,4}×nr_cpus none/2共24条记录退出0。研究者登记R1身份不虚构、R2数量≤L、R3不需截断时保留、R4上线CPU已有IRQ栈、R5上线CPU已有per-CPU偏移，经不变公共核心评价120次，适用项deadline全部不足。

结果：父版S64违反7、L4096违反5（{0,2}/L=2时possible变{0}，R1转满足而R3仍违反）；修复S64违反0；修复L4096违反3：{0,2}/nr_cpus=2时CPU2进入possible并上线但IRQ栈只分给CPU0，{0,2,4}/nr_cpus=2时possible为3个超过L且CPU2/4均无IRQ栈。同输入两分支有4组possible或判定不同；只数数量的谓词24条通过21条，其中7条存在R1或R4违反。父版L4096、{0,2}未给L时CPU2既不上线也不触发cpu_up拒绝，S64会打印拒绝，二者与历史“只有CPU0上线”均相容，历史机器实际配置未知。10项构造控制全部符合预期。

阶段结论：SPARC身份契约须把cpumask位宽分支与nr_cpus早期定界阶段列为显式适用条件，不能用小NR_CPUS投影代表默认配置。修复版/主线在默认大NR_CPUS且nr_cpus小于稀疏cpuid时的IRQ栈准备缺失与数量限制失效，**只是源码投影候选，不是确认Linux缺陷**；未核真实硬件、配置常见度及上游是否已有报告，外报需用户决定。已读案例、关系在看修复后由研究者写定，不是N1自动推导或独立检测。首轮analysis汇总字段把not_applicable计入deadline导致汇总为false，判定未变，原结果保留analysis_attempt1。

下一步：需用户决定是否安装gcc-sparc64-linux-gnu，以sparc64 defconfig真实编译固定父/修复版对象，核alloc_irqstack_bootmem与record_one_cpu循环界实际读取nr_cpu_ids（把位宽前提从投影升到编译对象层）；QEMU多CPU SPARC64不可用，真实启动挂账。未获批准前，整理CPU身份/范围限定方法阶段评审（ARM64正常+SPARC双位宽正例/候选）。表示/R3暂缓、VT-d后置，CPU导出/拓扑、SMMU和virtio开放项保留；Kimi大请求停点未重试。

统计：4次宿主投影编译、24条投影记录、120次核心评价、10项控制；0内核构建、0启动、0模型调用、0软件包安装，新确认Linux缺陷0，独立正例/正常仍0/0。证据linux_bug_analyze/experiments/case_taxonomy/sparc_identity_chain_20261027/：frozen_plan、fragments与source_manifest/file_blobs、projection.c、attempt1、checking_policy、analysis（及analysis_attempt1）、controls、platform_sources、delivery_manifest。源码Git /root/repos/linux，工作区仍Windows挂载，无独立/root/repos/linux_bug_analyze副本。日志、待办、进展、交接及家族规划同轮更新，三份WSL镜像以本轮notes_sync收据为准；Word未改。另：本日已按用户要求将研究相关Ubuntu内容（项目工作区、/root笔记镜像、/root/repos/linux及lba-acpi/vtd树，不含34GB构建缓存）tar备份到E:\\研究备份\\ubuntu_backup_20261027_1826，7包条目数与源一致并附SHA256SUMS；这是维护操作，不计研究实验。

以下为历史记录，以本节及用户最新指示为准。

'''

PLAN_ROW = ('| 2026-10-27 | CPU／SPARC64身份→IRQ栈/per-CPU消费与cpumask位宽 | 子阶段完成：逐字原函数×S64/L4096两位宽×父/修复，24投影记录、120核心评价；'
            '修复版默认大NR_CPUS下nr_cpus<稀疏cpuid时IRQ栈缺失/数量超限为源码候选；QEMU sparc64仅1 CPU；'
            'linux_bug_analyze/experiments/case_taxonomy/sparc_identity_chain_20261027/ | 10控制符合预期；关系/位宽前提人工登记，独立0/0；'
            '候选未确认、未外报；待用户决定是否装sparc64交叉编译器做对象层核对，真实多CPU启动挂账 |\n')


def main():
    target = HERE / 'notes_update.json'
    need(not target.exists(), 'preserve_notes_update')
    before = json.loads((HERE / 'notes_before.json').read_text(encoding='utf-8'))['before_sha256']
    for name, digest in before.items():
        need(sha(OUTER / name) == digest, 'work_note_changed_during_round:' + name)
    plan = OUTER / '接口验证后续规划.md'
    need(sha(plan) == sha(HERE / 'plan_before.md'), 'family_plan_changed_during_round')
    text = plan.read_text(encoding='utf-8')
    replacements = [
        ('SPARC正例实际消费/合法配置/真实启动，ARM64正常仅限本配置',
         'SPARC修复版默认大NR_CPUS下IRQ栈/数量候选待对象层与真实平台确认（QEMU sparc64仅1 CPU），ARM64正常仅限本配置'),
        ('身份/范围新增ARM64实际正常对照，继续SPARC正例消费/合法性；非全家族完成',
         '身份/范围新增ARM64实际正常对照及SPARC双位宽消费链投影；非全家族完成'),
    ]
    for old, new in replacements:
        need(text.count(old) == 1, 'family_row_not_unique:' + old[:12])
        text = text.replace(old, new)
    marker = '\n## 当前执行顺序\n'
    need(text.count(marker) == 1, 'execution_heading_not_unique')
    text = text.replace(marker, PLAN_ROW + marker)
    start = text.index(marker) + len(marker)
    while text[start] == '\n':
        start += 1
    end = text.index('\n\n', start)
    text = text[:start] + ('CPU身份与启动范围进行中：ARM64已有4格实际正常对照；SPARC已核固件cpuid→possible→IRQ栈/per-CPU/bringup源码链，'
                           '并以两种cpumask位宽分支投影，发现修复版在默认NR_CPUS=4096且nr_cpus小于稀疏cpuid时的源码候选。'
                           'QEMU sparc64仅支持1 CPU，真实启动挂账。下一项待用户决定是否安装sparc64交叉编译器做对象层核对；'
                           '未获批准则整理CPU身份/范围限定方法阶段评审。CPU导出、拓扑、SMMU及virtio未决项挂账；表示/R3暂缓、VT-d后置不变。') + text[end:]
    for name in before:
        path = OUTER / name
        title, rest = path.read_text(encoding='utf-8').split('\n', 1)
        path.write_text(title + '\n\n' + SECTION + rest.lstrip('\n'), encoding='utf-8')
    plan.write_text(text, encoding='utf-8')
    log = OUTER / '日志/2026-10-27.md'
    with log.open('a', encoding='utf-8') as f:
        f.write('\n\n' + SECTION.replace('以下为历史记录，以本节及用户最新指示为准。\n\n', ''))
    target.write_text(json.dumps({'before_sha256': before, 'after_sha256': {n: sha(OUTER / n) for n in before},
                                  'family_plan_sha256': sha(plan), 'daily_log_sha256': sha(log)},
                                 ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'updated_notes': len(before), 'daily_log': '2026-10-27.md', 'family_plan': True}))


def prepare():
    """Snapshot pre-round state (run before main)."""
    need(not (HERE / 'notes_before.json').exists(), 'preserve_notes_before')
    (HERE / 'notes_before.json').write_text(json.dumps({'before_sha256': {n: sha(OUTER / n) for n in NOTES}},
                                                       ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    shutil.copyfile(OUTER / '接口验证后续规划.md', HERE / 'plan_before.md')


if __name__ == '__main__':
    import sys
    prepare() if sys.argv[1:] == ['prepare'] else main()
