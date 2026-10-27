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


SECTION = '''## 10月27日 最新进展：固件与平台信息接口限定方法阶段评审完成

按用户指示整理固件与平台信息接口（ACPI MADT记录接受、Xen PV早期限额两用途）的限定方法阶段评审。评审前复核，无新构建/启动/模型调用：ACPI 6修订各52例共312条逐例记录重算，接受/能力不一致与完全一致数与summary完全相同；KUnit before/after工件SHA一致，失败恰为before场景2/3的mask与APIC成员；环境分类实测交付清单54个文件SHA一致，8个契约输入经不变核心（42d37cc4…）重放5满足/3违反逐项一致；Xen 12对重算“早期上限改变/后期结果相同”条件集合与原analysis一致（C01/C02/C05）；无清单目录只记SHA快照。

方法卡按八项提纲成文。依据分规范（ACPI 6.3 Online Capable；此前Enabled=0不可用）、Linux兼容政策（QEMU热插槽约定、adbf61cc47cb“只对guest允许”）与实现事实（识别表、nopv、setter分支）三层，政策不等于规范。须显式的适用条件：固件能力版本（QEMU 8.2.2实为FADT/APIC v03）、政策作用域、作用域条件的提供者（已识别hypervisor类型、KVM_GUEST、nopv）、LAPIC/x2APIC路径、阶段与setter赋值分支。目标关系含接受与版本能力一致、兼容放宽只在作用域内生效、作用域条件提供者须覆盖政策意图环境（P1）、热插上线CPU属启动possible（P3）及早期范围不被不适用的平台判断收窄。证据层级为原函数投影（312条ACPI、24条Xen）、编译器事实、注入固件真实启动（16次）、真实固件真实环境启动+QMP热插（4次）；裸机/厂商固件/Xen运行为空。最强合法对照是新增的“同表异环境”。

机制比较加入第七类“固件记录接受：版本化能力、作用域兼容政策及其作用域条件提供者资格”，记录跨机制观察：来源资格出现在两层——数据来源对用途的资格（CPU导出）与政策作用域条件提供者的资格（ACPI环境分类）；配置/环境相关的分支选择在CPU身份、virtio与固件中反复出现，须绑定具体配置或运行环境。

阶段状态：固件与平台信息接口两用途**限定开发方法阶段评审完成**，不是整个家族、裸机/厂商固件或独立评价完成。挂账：裸机与厂商固件、online-capable真实表、未开KVM_GUEST内核、畸形/混合表、Xen真实运行（本机不可行）。ACPI环境覆盖与SPARC IRQ栈两项观察均未确认、未外报，由用户决定。

下一步：已积累拓扑准备、来源导出、Btrfs几何、SMMU失效、virtio DMA、CPU身份/范围、固件/平台作用域政策七类机制，可按《最终研究目标与阶段推进原则》开展横向复核，再决定是否启动统一实现；启动时机由用户决定。其他未立项家族不为凑覆盖开新项；表示/R3暂缓、VT-d后置；Kimi大请求停点未重试。

统计：66个ACPI归档工件与54个实测文件SHA、312条投影逐例重算、16次启动结论、8次契约重放、12对Xen重算均0不一致；0构建、0启动、0模型调用，新确认Linux缺陷0，独立正例/正常仍0/0。证据linux_bug_analyze/experiments/case_taxonomy/firmware_platform_review_20261027/：method_card.md、mechanism_comparison.json、replay_and_integrity.py、replay_results.json、delivery_manifest.json。日志、待办、进展、交接及家族规划同轮更新，三份WSL镜像以本轮notes_sync收据为准；Word未改。

以下为历史记录，以本节及用户最新指示为准。

'''

PLAN_ROW = ('| 2026-10-27 | 固件与平台／ACPI记录接受与Xen早期限额 | 限定方法阶段评审完成：方法卡八项、第七类机制入比较；312投影逐例、16启动、8契约重放、12对Xen重算及120工件SHA均一致；'
            'linux_bug_analyze/experiments/case_taxonomy/firmware_platform_review_20261027/ | 裸机/厂商固件/online-capable表/Xen运行挂账；两项观察未外报；依据层级与作用域提供者人工登记，独立0/0；可开展七类机制横向复核 |\n')


def main():
    target = HERE / 'notes_update.json'
    need(not target.exists(), 'preserve_notes_update')
    before = json.loads((HERE / 'notes_before.json').read_text(encoding='utf-8'))['before_sha256']
    for name, digest in before.items():
        need(sha(OUTER / name) == digest, 'work_note_changed_during_round:' + name)
    plan = OUTER / '接口验证后续规划.md'
    need(sha(plan) == sha(HERE / 'plan_before.md'), 'family_plan_changed_during_round')
    text = plan.read_text(encoding='utf-8')
    old = '| ACPI兼容政策环境覆盖已实测（非确认缺陷）；待限定方法评审；未完成家族验证 |'
    new = '| ACPI记录接受与Xen早期限额两用途限定方法阶段评审完成（含环境覆盖实测，非确认缺陷）；未完成家族验证 |'
    need(text.count(old) == 1, 'family_status_not_unique')
    text = text.replace(old, new)
    marker = '\n## 当前执行顺序\n'
    need(text.count(marker) == 1, 'execution_heading_not_unique')
    text = text.replace(marker, PLAN_ROW + marker)
    start = text.index(marker) + len(marker)
    while text[start] == '\n':
        start += 1
    end = text.index('\n\n', start)
    text = text[:start] + ('固件与平台信息接口两用途限定方法阶段评审已完成（firmware_platform_review_20261027）。已积累七类机制，下一项可开展横向复核并决定是否启动统一实现，时机由用户决定；SPARC与ACPI两项观察是否外报由用户决定。'
                           '各接口未决项挂账；其他未立项家族不为凑覆盖开新项；表示/R3暂缓、VT-d后置不变。') + text[end:]
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
        'archive_files_rechecked': 120, 'projection_records_recounted': 312, 'boot_conclusions_recomputed': 16,
        'contract_replays': 8, 'xen_pairs_recounted': 12, 'mismatches': 0, 'new_builds': 0, 'new_boots': 0,
        'model_calls': 0, 'independent_positive_normal': [0, 0]},
        'stage_status': 'firmware/platform two-purpose limited development method stage review complete'},
        ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    (HERE / 'notes_before.json').write_text(json.dumps({'before_sha256': {n: sha(OUTER / n) for n in NOTES}},
                                                       ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    shutil.copyfile(OUTER / '接口验证后续规划.md', HERE / 'plan_before.md')


if __name__ == '__main__':
    prepare() if sys.argv[1:] == ['prepare'] else main()
