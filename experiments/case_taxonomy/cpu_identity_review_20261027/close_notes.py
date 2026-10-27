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


SECTION = '''## 10月27日 最新进展：CPU身份与启动范围限定方法阶段评审完成

按用户指示整理CPU身份/范围接口的方法阶段评审，纳入SPARC 12条旧投影、x86/PowerPC映射试用、Xen资格与24条阶段投影、三分支setter写入事实、准入审核、ARM64 4格实际启动、SPARC双位宽投影及真实sparc64编译对象。评审前复核：三轮最新目录按交付清单逐文件核SHA，126/120/88项全部一致；六个旧轮次无清单，只记当前SHA快照。用不变公共核心（42d37cc4…）重放已保存的164个契约输入（ARM64 20满足；旧SPARC适配器24项20满足/4违反；双位宽120项89满足/16不适用/15违反），与原记录逐项一致，账本证据文件SHA未变；对象层16项按最终判定器重算一致。没有新构建、启动、投影执行或模型调用。

方法卡按八项提纲成文。公共层以cpumask位位置表示逻辑CPU身份，按位做准备型（IRQ栈、per-CPU偏移）、激活型（bringup/cpu_up）与使用型（set_hardirq_stack、per-CPU对象）消费。须显式作为适用条件的维度：编号命名空间/映射（SPARC直映 vs ARM64显式映射）、选择数量/后期上界/激活数、cpumask位宽分支、setter赋值分支（FORCE/NR_CPUS==1只告警）和阶段。目标关系分身份不虚构、数量≤nr_cpus、无截断时保留、上线CPU已有IRQ栈与per-CPU偏移，ARM64另有映射单射/硬件相符/重定界/激活域/选择上限；数量与身份必须分开，只数数量的谓词在双位宽24条中21条通过而其中7条有身份或准备违反。

证据层级分为源码blob、原函数逐字宿主投影、预处理/编译对象、实际虚拟平台启动，物理硬件和首次消费为空；同一关系不同层级结论不得互相冒充。自动部分为身份/SHA、逐字提取与投影、集合事实、.i与对象重定位模式、ARM64日志观测、核心四态判定与控制；研究者负责依据权威、命名空间与阶段角色、合法输入/正常资格、位宽分支认定和对象判定规则（已因循环轮转修订一次）。迁移需替换命名空间适配器、阶段采样点、准备型消费者清单和位宽核对规则。

机制比较在既有五机制上加入CPU身份/范围，并记录跨机制观察：配置相关的分支选择（cpumask位宽、FORCE_NR_CPUS）与来源导出的版本政策、virtio的一致性/后端分支一样，须按具体配置绑定，不能由缩减投影推断。

阶段状态：CPU身份/范围**限定开发方法阶段评审完成**，不是整个CPU家族、运行真值或独立检测完成。挂账：多CPU SPARC64真实启动（QEMU sparc64仅1 CPU）、首次硬中断/per-CPU使用、热插拔与maxcpus后续上线、物理硬件、独立评价；SPARC修复版/主线候选未确认、未外报，是否报告由用户决定。

下一步：按10/26接口队列转固件与平台信息接口（ACPI来源/政策、Xen CPU枚举条件），先核已有材料与可行成本再登记最小新证据。已积累拓扑准备、来源导出、Btrfs几何、SMMU失效、virtio DMA、CPU身份六类机制，可准备横向复核是否启动统一实现，启动时机由用户决定。表示/R3暂缓、VT-d后置；Kimi大请求停点未重试。

统计：334个文件SHA核对、164次契约重放、16项对象判定重算，均0不一致；0构建、0启动、0投影执行、0模型调用，新确认Linux缺陷0，独立正例/正常仍0/0。证据linux_bug_analyze/experiments/case_taxonomy/cpu_identity_review_20261027/：method_card.md、mechanism_comparison.json、replay_and_integrity.py、replay_results.json、delivery_manifest.json。日志、待办、进展、交接及家族规划同轮更新，三份WSL镜像以本轮notes_sync收据为准；Word未改。

以下为历史记录，以本节及用户最新指示为准。

'''

PLAN_ROW = ('| 2026-10-27 | CPU／身份与启动范围（命名空间、数量/上界/激活、位宽、准备覆盖） | 限定方法阶段评审完成：方法卡八项、六机制比较；334文件SHA、164契约重放、16对象判定重算均一致；'
            'linux_bug_analyze/experiments/case_taxonomy/cpu_identity_review_20261027/ | 多CPU SPARC64启动、首次消费、热插拔与物理硬件挂账；SPARC候选未确认未外报；'
            '依据/角色/资格人工，独立0/0；转固件与平台信息接口 |\n')


def main():
    target = HERE / 'notes_update.json'
    need(not target.exists(), 'preserve_notes_update')
    before = json.loads((HERE / 'notes_before.json').read_text(encoding='utf-8'))['before_sha256']
    for name, digest in before.items():
        need(sha(OUTER / name) == digest, 'work_note_changed_during_round:' + name)
    plan = OUTER / '接口验证后续规划.md'
    need(sha(plan) == sha(HERE / 'plan_before.md'), 'family_plan_changed_during_round')
    text = plan.read_text(encoding='utf-8')
    old = '拓扑与die导出两用途限定方法已整理；身份/范围新增ARM64实际正常对照及SPARC双位宽消费链投影及真实编译对象核对；非全家族完成'
    new = '拓扑、die导出、身份/范围三用途限定方法已整理（身份/范围含ARM64实际正常、SPARC双位宽投影与真实编译对象）；非全家族完成'
    need(text.count(old) == 1, 'family_status_not_unique')
    text = text.replace(old, new)
    marker = '\n## 当前执行顺序\n'
    need(text.count(marker) == 1, 'execution_heading_not_unique')
    text = text.replace(marker, PLAN_ROW + marker)
    start = text.index(marker) + len(marker)
    while text[start] == '\n':
        start += 1
    end = text.index('\n\n', start)
    text = text[:start] + ('CPU身份与启动范围限定方法阶段评审已完成（cpu_identity_review_20261027）；SPARC多CPU真实启动、首次消费与热插拔挂账，'
                           '修复版候选未确认未外报。下一项转固件与平台信息接口（ACPI来源/政策、Xen CPU枚举条件），先核已有材料与可行成本。'
                           '已积累六类机制，横向复核及统一实现启动时机由用户决定。CPU导出、拓扑、SMMU及virtio未决项挂账；表示/R3暂缓、VT-d后置不变。') + text[end:]
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
