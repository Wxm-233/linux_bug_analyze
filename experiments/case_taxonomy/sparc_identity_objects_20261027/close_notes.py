"""Update daily log, three working notes and family plan with SHA guards (prepare once, then run once)."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

HERE = Path(__file__).resolve().parent
OUTER = HERE.parents[3]
NOTES = ['当前代办.md', '当前研究方向与进展.md', '项目研究与文档写作交接说明.md']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def need(value, reason):
    if not value:
        raise ValueError(reason)


SECTION = '''## 10月27日 最新进展：SPARC64真实编译对象确认possible计数与IRQ栈循环的位宽界

经用户批准，apt安装gcc-sparc64-linux-gnu 4:13.2.1-2ubuntu1（sparc64-linux-gnu-gcc 13.3.0）与binutils 2.42，这是WSL持久环境变更。父版95706e717c4f55ca62025c151451ccc28863d085、修复98937707fea8375e8acea0aaa0b68a956dd52719各自git archive到/root/.cache/linux-bug-analyze/sparc-identity-objects-20261027，out-of-tree用sparc64_defconfig原样（实测CONFIG_NR_CPUS=4096、SMP=y、DEBUG_PER_CPU_MAPS未开）及只改NR_CPUS=64的对照，4变体各编译prom_64/setup_64/smp_64的.o与.i，全部首次成功；日志仅sparc常见clone3 #warning。

对象层事实：alloc_irqstack_bootmem无独立符号，内联进setup_arch；4096配置中循环以ld [nr_cpu_ids],%o1作size调用_find_next_bit(__cpu_possible_mask,…)，出口比较nr_cpu_ids，循环体两次memblock_alloc_try_nid后按cpu<<3写softirq_stack/hardirq_stack；64对照为常数0x40单字扫描+__ffs，不读nr_cpu_ids。修复版record_one_cpu在4096下ld [nr_cpu_ids],%o1后call __bitmap_weight，再与nr_cpu_ids比较决定set_bit；64下为__arch_hweight64全字计数。父版smp_fill_in_cpu_possible_map同样在4096用nr_cpu_ids大小的__bitmap_weight。.i展开分别为(nr_cpu_ids)与((unsigned int)64)。

判定O1循环界、O2计数宽度、O3预处理展开、O4版本差异，4变体16项全部与配置一致；7项篡改控制（删重定位、删栈存储、换helper、配置标签互换、父冒充修复、.i界换常数）均拒判。首版判定器用±20行邻近定位循环，父版两变体O1判不足：编译器轮转了父版循环，基址装载与find-bit调用相距约40行；对象未变，attempt2改为“首个IRQ栈基址重定位至最后分配后15行”区间且要求唯一界构造，修复版结果不变、父版转一致。attempt1脚本与结果保留。

结论变化：上一轮投影的两条cpumask位宽前提已由真实sparc64编译对象确认——默认NR_CPUS=4096下，修复版possible计数与IRQ栈分配循环都以运行时nr_cpu_ids为界，而nr_cpus=L在setup_arch开头即生效；因此L以外稀疏cpuid不计数也分不到IRQ栈在对象层成立，小NR_CPUS配置编译为常数宽度。仍未证实多CPU稀疏cpuid SPARC64真实启动时进入possible、上线并在首次硬中断使用NULL栈（QEMU sparc64仅1 CPU），也未核配置常见度与上游报告；候选仍**未确认、未外报**，对象层不是运行观察。

下一步：CPU身份/范围转限定方法阶段评审，整理ARM64实际正常、SPARC正例投影及双位宽对象核对的方法卡、关系/适用条件/证据层级与人工分工；SPARC多CPU真实启动挂账。是否向上游报告该候选由用户决定。表示/R3暂缓、VT-d后置，CPU导出/拓扑、SMMU和virtio开放项保留；Kimi大请求停点未重试。

统计：1次apt工具链安装、2份源码归档、4配置变体×3对象+3预处理单元、16项对象判定、7项控制，判定器2次（首次规则过窄失败保留）；0 vmlinux链接、0启动、0模型调用，新确认Linux缺陷0，独立正例/正常仍0/0。证据linux_bug_analyze/experiments/case_taxonomy/sparc_identity_objects_20261027/：frozen_plan、toolchain_install_receipt、build_objects.sh、attempt1（对象/配置/.cmd/SHA256SUMS）、analysis（逐函数反汇编与object_facts）、check_objects及attempt1、object_results及attempt1、delivery_manifest。日志、待办、进展、交接及家族规划同轮更新，三份WSL镜像以本轮notes_sync收据为准；Word未改。

以下为历史记录，以本节及用户最新指示为准。

'''

PLAN_ROW = ('| 2026-10-27 | CPU／SPARC64 possible计数与IRQ栈循环的编译位宽 | 子阶段完成：apt装sparc64工具链，父/修复×defconfig(4096)/NR_CPUS=64共4变体真实编译对象，16项判定一致、7控制拒判；'
            'linux_bug_analyze/experiments/case_taxonomy/sparc_identity_objects_20261027/ | 对象层确认默认配置以运行时nr_cpu_ids为界；首版判定器因循环轮转过窄已保留；'
            '真实多CPU启动与首次硬中断未证，候选未确认未外报；转CPU身份/范围限定方法评审 |\n')


def main():
    target = HERE / 'notes_update.json'
    need(not target.exists(), 'preserve_notes_update')
    before = json.loads((HERE / 'notes_before.json').read_text(encoding='utf-8'))['before_sha256']
    for name, digest in before.items():
        need(sha(OUTER / name) == digest, 'work_note_changed_during_round:' + name)
    plan = OUTER / '接口验证后续规划.md'
    need(sha(plan) == sha(HERE / 'plan_before.md'), 'family_plan_changed_during_round')
    text = plan.read_text(encoding='utf-8')
    for old, new in [
        ('SPARC修复版默认大NR_CPUS下IRQ栈/数量候选待对象层与真实平台确认（QEMU sparc64仅1 CPU）',
         'SPARC修复版默认NR_CPUS=4096下IRQ栈/数量候选已获对象层位宽确认，真实多CPU启动待合格平台（QEMU sparc64仅1 CPU）'),
        ('SPARC双位宽消费链投影；非全家族完成', 'SPARC双位宽消费链投影及真实编译对象核对；非全家族完成'),
    ]:
        need(text.count(old) == 1, 'family_row_not_unique:' + old[:12])
        text = text.replace(old, new)
    marker = '\n## 当前执行顺序\n'
    need(text.count(marker) == 1, 'execution_heading_not_unique')
    text = text.replace(marker, PLAN_ROW + marker)
    start = text.index(marker) + len(marker)
    while text[start] == '\n':
        start += 1
    end = text.index('\n\n', start)
    text = text[:start] + ('CPU身份与启动范围进行中：ARM64有4格实际正常对照；SPARC固件cpuid→possible→IRQ栈/per-CPU/bringup链已有双位宽投影，'
                           '并经真实sparc64编译对象确认默认NR_CPUS=4096下计数与IRQ栈循环以运行时nr_cpu_ids为界。修复版候选未确认、未外报，'
                           'QEMU sparc64仅1 CPU，真实启动挂账。下一项整理CPU身份/范围限定方法阶段评审。CPU导出、拓扑、SMMU及virtio未决项挂账；'
                           '表示/R3暂缓、VT-d后置不变。') + text[end:]
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
    need(not (HERE / 'notes_before.json').exists(), 'preserve_notes_before')
    (HERE / 'notes_before.json').write_text(json.dumps({'before_sha256': {n: sha(OUTER / n) for n in NOTES}},
                                                       ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    shutil.copyfile(OUTER / '接口验证后续规划.md', HERE / 'plan_before.md')


if __name__ == '__main__':
    prepare() if sys.argv[1:] == ['prepare'] else main()
