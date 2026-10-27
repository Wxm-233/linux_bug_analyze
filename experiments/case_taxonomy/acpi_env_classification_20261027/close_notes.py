"""Write manifest; update daily log, three working notes and family plan with SHA guards; prepare once, run once."""
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


SECTION = '''## 10月27日 最新进展：ACPI legacy MADT热插槽兼容政策的真实环境分类实测

经用户批准执行审计轮登记的最小新证据。修复adbf61cc47cb（v7.0-rc1，主线谓词未变）git archive后out-of-tree x86_64_defconfig构建，仅设LOCALVERSION；KVM_GUEST、ACPI_HOTPLUG_CPU、HYPERVISOR_GUEST、HOTPLUG_CPU、DEVTMPFS在defconfig中均已为y，未额外启用，NR_CPUS=64。bzImage首次成功（153秒，6.19.0-rc1-lba-acpi-env），静态PID1与newc initramfs首次成功，无源码修改。

同一镜像在QEMU 8.2.2 q35、-smp 1,maxcpus=4下以KVM、KVM+nopv、TCG、TCG(-cpu max)四环境启动；PID1打印sysfs集合后，驱动经QMP对首个空槽（socket 0/core 1）device_add，PID1等新CPU目录并写online。四次均完整结束，QMP device_add均被QEMU接受；四次固件表完全相同（APIC长度0x90、v03，FACP v03，legacy无Online Capable）。

结果：KVM识别为KVM，“1 present plus 3 hotplug”，启动possible 0-3，热插后“ACPI: CPU1 has been hot-added”并启动Processor 1，online写入成功，最终online 0-1。KVM+nopv、TCG、TCG cpu max均无hypervisor识别行，“1 present plus 0 hotplug”，possible仅0，热插时内核报“ACPI: Unable to map lapic to logical cpu number”，没有新CPU目录。P1（依赖legacy Enabled=0热插槽的QEMU guest启动possible≥present+热插槽=4）与P3（上线CPU均属启动possible）经不变公共核心8次评价：P1 KVM满足、其余3违反，P3全部满足；10项构造控制全部符合预期。

结论变化：审计轮的源码假说已由真实运行确认——同一固件表、同一镜像下，legacy Enabled=0热插槽是否被接受只取决于内核是否识别出已登记hypervisor；nopv的KVM guest与TCG guest被按裸机处理而失去CPU热插拔。“是guest”的用途条件由“识别到的hypervisor类型”提供，二者在这些环境不一致，提交说明“只对guest允许QEMU用例”的意图与实际覆盖存在可观察差异。这是来源资格与用途政策机制在固件/平台家族的实测实例。**不是确认缺陷**：上游可能认为TCG/nopv不在支持范围；未检验裸机规范行为、厂商固件、Xen、online-capable表或未启用KVM_GUEST的内核；是否报告由用户决定。已读开发案例，关系依提交说明由研究者登记，不是N1自动推导或独立检测。

下一步：整理固件与平台信息接口限定方法阶段评审（ACPI版本化能力/兼容政策投影、fixture启动、真实环境分类实测，Xen早期限额投影），Xen真实运行与裸机挂账。SPARC与ACPI两个观察是否外报由用户决定。表示/R3暂缓、VT-d后置，CPU、SMMU及virtio开放项保留；Kimi大请求停点未重试。

统计：1次内核构建、1次PID1编译、4次合格guest启动、4次QMP热插、8次核心评价、10项控制；0模型调用，新确认Linux缺陷0，独立正例/正常仍0/0。证据linux_bug_analyze/experiments/case_taxonomy/acpi_env_classification_20261027/：frozen_plan、build.py/guest_init.c、build_attempt1、run_boots.py、runs_attempt1（console/stderr/receipt含QMP记录）、checking_policy、analysis、controls、delivery_manifest；缓存/root/.cache/linux-bug-analyze/acpi-env-20261027。日志、待办、进展、交接及家族规划同轮更新，三份WSL镜像以本轮notes_sync收据为准；Word未改。

以下为历史记录，以本节及用户最新指示为准。

'''

PLAN_ROW = ('| 2026-10-27 | 固件与平台／ACPI legacy MADT热插槽兼容政策的环境覆盖 | 子阶段完成：修复版1构建、KVM/KVM+nopv/TCG/TCG max四环境真实启动+QMP热插；同一固件表下仅KVM接受热插槽并热插成功，其余possible仅0、热插“Unable to map lapic”；'
            'linux_bug_analyze/experiments/case_taxonomy/acpi_env_classification_20261027/ | P1 1满足3违反、10控制符合；政策范围观察非确认缺陷、未外报；裸机/Xen/online-capable表未测；转固件/平台限定方法评审 |\n')


def main():
    target = HERE / 'notes_update.json'
    need(not target.exists(), 'preserve_notes_update')
    before = json.loads((HERE / 'notes_before.json').read_text(encoding='utf-8'))['before_sha256']
    for name, digest in before.items():
        need(sha(OUTER / name) == digest, 'work_note_changed_during_round:' + name)
    plan = OUTER / '接口验证后续规划.md'
    need(sha(plan) == sha(HERE / 'plan_before.md'), 'family_plan_changed_during_round')
    text = plan.read_text(encoding='utf-8')
    old = ('| ACPI 6修订投影与16次fixture真实启动、Xen资格/投影；来源资格、政策版本与阶段传播 | 真实环境分类（KVM/TCG/nopv）×真实QEMU表×实际热插拔待测；Xen PV与裸机不可行挂账；与CPU用途交叉，不重复计案例 | 10/27已审计材料与可行成本，最小新证据已登记未执行；未完成家族验证 |')
    new = ('| ACPI 6修订投影、16次fixture真实启动及4环境真实分类+QMP热插、Xen资格/投影；来源资格、政策版本、环境分类与阶段传播 | 裸机规范行为、厂商固件、online-capable表、Xen PV真实运行不可行或未测；与CPU用途交叉，不重复计案例 | ACPI兼容政策环境覆盖已实测（非确认缺陷）；待限定方法评审；未完成家族验证 |')
    need(text.count(old) == 1, 'family_row_not_unique')
    text = text.replace(old, new)
    marker = '\n## 当前执行顺序\n'
    need(text.count(marker) == 1, 'execution_heading_not_unique')
    text = text.replace(marker, PLAN_ROW + marker)
    start = text.index(marker) + len(marker)
    while text[start] == '\n':
        start += 1
    end = text.index('\n\n', start)
    text = text[:start] + ('固件与平台信息接口进行中：ACPI legacy MADT兼容政策已在KVM/KVM+nopv/TCG/TCG max真实环境实测（acpi_env_classification_20261027），仅KVM接受热插槽。下一项整理固件/平台限定方法阶段评审；Xen真实运行与裸机挂账。'
                           'SPARC与ACPI两个观察是否外报由用户决定。CPU、SMMU及virtio未决项挂账；表示/R3暂缓、VT-d后置不变。') + text[end:]
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
    files = {p.relative_to(HERE).as_posix(): sha(p) for p in sorted(HERE.rglob('*'))
             if p.is_file() and p.name != 'delivery_manifest.json' and '__pycache__' not in p.parts}
    (HERE / 'delivery_manifest.json').write_text(json.dumps({'date': '2026-10-27', 'files': files, 'statistics': {
        'kernel_builds': 1, 'pid1_builds': 1, 'qualified_guest_boots': 4, 'qmp_hotplugs': 4, 'core_evaluations': 8,
        'controls': 10, 'controls_as_expected': 10, 'model_calls': 0, 'confirmed_linux_defects': 0,
        'independent_positive_normal': [0, 0]}}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    (HERE / 'notes_before.json').write_text(json.dumps({'before_sha256': {n: sha(OUTER / n) for n in NOTES}},
                                                       ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    shutil.copyfile(OUTER / '接口验证后续规划.md', HERE / 'plan_before.md')


if __name__ == '__main__':
    prepare() if sys.argv[1:] == ['prepare'] else main()
