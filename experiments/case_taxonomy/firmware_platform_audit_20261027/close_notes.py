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


SECTION = '''## 10月27日 最新进展：固件与平台信息接口——已有材料与可行成本审计

按用户指示转入固件与平台信息接口，先核已有材料与可行成本。盘点ACPI MADT记录接受（acpi_contracts：6个历史修订原函数投影，52例/修订；acpi_kunit：QEMU q35 TCG真实内核16次启动，fixture注入MADT并替换环境选择器）及Xen PV早期限额（资格审核、24条阶段投影、setter三分支写入事实）。ACPI四个修复提交与Xen候选均为已读开发材料。归档复核：acpi-contract v2的42个工件、acpi-kunit before/after各12个工件SHA一致；按原verify断言内存重算，before仅场景2/3的mask/APIC成员预期失败、after全通过，未改写原verified-summary。原16次启动均为-accel tcg -cpu max，日志无“Hypervisor detected”，QEMU固件表头为FACP v03、APIC v03（legacy）。

新识别的可检验问题：修复adbf61cc47cb（v7.0-rc1，主线df2908090cda谓词未变）提交说明的意图是legacy MADT中Enabled=0条目只对guest按QEMU热插拔约定接受、裸机按规范忽略；代码判据却是!hypervisor_is_type(X86_HYPER_NATIVE)，即识别到已登记hypervisor类型。源码事实：识别表为xen_pv/xen_hvm/vmware/ms_hyperv/kvm（需CONFIG_KVM_GUEST）/jailhouse/acrn/bhyve，QEMU TCG guest不匹配；x86_hyper_kvm无ignore_nopv，nopv会跳过KVM识别；init_hypervisor_platform早于acpi_boot_init与topology_init_possible_cpus。“是guest”的用途条件由“识别到的hypervisor类型”提供，二者在TCG guest、nopv KVM guest及未启用KVM_GUEST的内核上可能不一致——这是来源资格与用途政策机制在本家族的实例，目前只是源码假说；9月KUnit替换了选择器，从未检验真实环境分类。

可行性实测：/dev/kvm存在，q35上-accel kvm与tcg均可初始化（KVM仅有Intel宿主不支持qemu64请求svm位的告警）；QEMU Xen HVM仿真被拒（宿主KVM不支持），QEMU不仿真Xen PV，本机无xl工具，也无裸机legacy MADT机器。Xen P01真实运行不可行、继续挂账；ACPI政策“真实环境分类×真实QEMU固件表×实际热插拔”本机可行，正好补9月材料最缺的一层。

登记最小新证据（未执行）：修复版一次x86_64 defconfig构建（不加fixture，核HYPERVISOR_GUEST/KVM_GUEST/ACPI_HOTPLUG_CPU），静态PID1；同一镜像在KVM、KVM+nopv、TCG、TCG(-cpu max)四环境以-smp 1,maxcpus=4启动，记hypervisor行、“Allowing N present plus M hotplug”、sysfs集合，并经QMP device_add热插一个CPU后尝试上线；预计1构建+4启动、约10—25分钟，父版对照可选（修复同时改topology.c，非单谓词对照）。预期为研究者源码假说；TCG guest若失去热插拔也只是政策适用范围观察，上游可能视TCG为范围外，不当确认缺陷。

下一步：经用户确认后执行上述ACPI环境分类实测；Xen挂账。表示/R3暂缓、VT-d后置，CPU身份/导出/拓扑、SMMU及virtio开放项保留；SPARC候选未外报；Kimi大请求停点未重试。

统计：66个归档工件SHA复核、16次原启动结论重算、4次加速器探测（QEMU -S暂停后退出，无guest代码）；0构建、0 Linux启动、0模型调用，新确认缺陷0，独立正例/正常仍0/0。证据linux_bug_analyze/experiments/case_taxonomy/firmware_platform_audit_20261027/：README、audit_probe.py、audit_probe_results.json、next_minimal_evidence_plan.json、delivery_manifest.json。日志、待办、进展、交接及家族规划同轮更新，三份WSL镜像以本轮notes_sync收据为准；Word未改。

以下为历史记录，以本节及用户最新指示为准。

'''

PLAN_ROW = ('| 2026-10-27 | 固件与平台／ACPI记录接受政策与Xen早期限额：材料与可行性审计 | 审计完成：66工件SHA与16次原启动结论复核一致；识别“guest政策由已识别hypervisor类型提供”的可测假说；KVM/TCG可用、Xen仿真不可用；'
            'linux_bug_analyze/experiments/case_taxonomy/firmware_platform_audit_20261027/ | 最小新证据（1构建+4启动+QMP热插）已登记未执行；Xen与裸机挂账；已读开发材料，独立0/0 |\n')


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
        ('| 部分真实启动或原函数投影；来源资格、政策版本与阶段传播 | 完整历史入口与平台配对、实际接受/枚举结果；与CPU用途交叉，不重复计案例 | 保留辅助机制材料，未完成家族验证 |',
         '| ACPI 6修订投影与16次fixture真实启动、Xen资格/投影；来源资格、政策版本与阶段传播 | 真实环境分类（KVM/TCG/nopv）×真实QEMU表×实际热插拔待测；Xen PV与裸机不可行挂账；与CPU用途交叉，不重复计案例 | 10/27已审计材料与可行成本，最小新证据已登记未执行；未完成家族验证 |'),
    ]:
        need(text.count(old) == 1, 'family_row_not_unique')
        text = text.replace(old, new)
    marker = '\n## 当前执行顺序\n'
    need(text.count(marker) == 1, 'execution_heading_not_unique')
    text = text.replace(marker, PLAN_ROW + marker)
    start = text.index(marker) + len(marker)
    while text[start] == '\n':
        start += 1
    end = text.index('\n\n', start)
    text = text[:start] + ('固件与平台信息接口进行中：已审计ACPI/Xen已有材料与可行成本（firmware_platform_audit_20261027）。下一项经用户确认后执行ACPI legacy MADT兼容政策的真实环境分类实测（KVM/KVM+nopv/TCG/TCG cpu max，QMP热插）；Xen真实运行不可行挂账。'
                           'CPU身份/导出/拓扑、SMMU及virtio未决项挂账；SPARC候选未外报；表示/R3暂缓、VT-d后置不变。') + text[end:]
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
             if p.is_file() and p.name not in {'delivery_manifest.json'} and '__pycache__' not in p.parts}
    (HERE / 'delivery_manifest.json').write_text(json.dumps({'date': '2026-10-27', 'files': files, 'statistics': {
        'archive_artifacts_rechecked': 66, 'archived_boot_conclusions_recomputed': 16, 'accelerator_probes': 4,
        'kernel_builds': 0, 'linux_boots': 0, 'model_calls': 0, 'independent_positive_normal': [0, 0]}},
        ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    (HERE / 'notes_before.json').write_text(json.dumps({'before_sha256': {n: sha(OUTER / n) for n in NOTES}},
                                                       ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    shutil.copyfile(OUTER / '接口验证后续规划.md', HERE / 'plan_before.md')


if __name__ == '__main__':
    prepare() if sys.argv[1:] == ['prepare'] else main()
