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


SECTION = '''## 10月27日 最新进展：七类机制横向复核及统一实现建议

按用户指示，依《最终研究目标与阶段推进原则》“转入统一实现的条件”四个问题，复核拓扑准备、来源资格导出、Btrfs几何、SMMU失效、virtio DMA、CPU身份/范围、固件/平台作用域政策七类已完成限定方法评审的机制。只读扫描案例目录（usage_scan.json）：五类用过公共核心（去重契约：拓扑1、导出38、Btrfs 7、身份164、固件8；算子contains/eq/le/lt/gt/ge/and/or/not），SMMU与virtio完全未用核心、各有专用检查器；核心269行，选择器/事实桥/模型候选等约750行。扫描为下界，行数含收尾脚本，只作量级参考。

问题一：证据流程（身份固定→外部审核依据→显式关系→分层证据→四态→控制拒判→SHA收尾）七类全部重复出现；公共表达覆盖五类，不是为单例设计。问题二：通用规则、接口适配与人工语义可分开，已有两次实际迁移（同一身份映射关系经ARM64启动与SPARC投影两种适配器复用；固件环境分类沿用身份账本结构）；机械重复明显——envelope()封装在8个文件各写一份，收尾/同步脚本各约65份、其中55份同步脚本逐字节相同。问题三：开发层七类都有正常对照、过强/过弱诊断和构造拒判，且两次抓出我们自己的检查器缺陷（SMMU旧检查器忽略顺序、SPARC对象判定窗口过窄），独立评价层仍0/0、未冻结未接触候选池。问题四：已识别核心表达不了的关系——按对象代次的事件顺序（SMMU qtest、virtio map→发布→完成→unmap→消费→重投）、算术包络与min/floor/ceil（virtio维护区间、Btrfs min只能由适配器预算）、编译对象证据层（basis缺compiled_object）、样本到期限的稳定性（适用项deadline恒不足）；均以不足或专用检查器如实处理，没有改答案取得通过。

建议启动“有界统一实现”：先(1)抽取共享契约/账本构建器与收尾同步工具，用已存全部契约输入回归；(4)动代码前冻结评价协议与未接触候选池；再(2)最小表示扩展（compiled_object层、仅覆盖SMMU qtest与virtio普通split的有序事件关系、可追溯的min/max/floor/ceil），每项须逐项复现对应专用检查器已存结论，否则保留专用检查器；最后(3)薄统一入口（输入组织→适配器选择→契约评价→分层报告），不称N1自动推导。不建议模型候选自动批准、为凑覆盖开新家族或放宽采样不升格为期限。是否启动及顺序由用户决定。

工程风险：contract_protocol.py等新组件及大部分实验目录在Git（sjy_test）中仍未跟踪，只有今日E盘tar备份覆盖；统一实现前是否提交由用户决定。SPARC与ACPI两项观察仍未确认、未外报。

统计：只读扫描7类机制79个目录；0新代码（除扫描脚本）、0实验、0模型调用，新确认缺陷0，独立正例/正常仍0/0。证据linux_bug_analyze/experiments/case_taxonomy/mechanism_cross_review_20261027/：cross_review.md、criteria_matrix.json、scan_usage.py、usage_scan.json、delivery_manifest.json。日志、待办、进展、交接及家族规划同轮更新，三份WSL镜像以本轮notes_sync收据为准；Word未改。

以下为历史记录，以本节及用户最新指示为准。

'''

PLAN_ROW = ('| 2026-10-27 | 跨家族／七类机制横向复核 | 复核完成：流程7/7重复、核心表达5/7；两次迁移记录；SMMU/virtio因事件顺序与算术未用核心；envelope 8份、同步脚本55份逐字节重复；'
            'linux_bug_analyze/experiments/case_taxonomy/mechanism_cross_review_20261027/ | 建议有界统一实现（共享构建器/收尾工具→冻结评价协议与候选池→最小表示扩展→薄入口），待用户决定；独立0/0；新组件未入Git |\n')


def main():
    target = HERE / 'notes_update.json'
    need(not target.exists(), 'preserve_notes_update')
    before = json.loads((HERE / 'notes_before.json').read_text(encoding='utf-8'))['before_sha256']
    for name, digest in before.items():
        need(sha(OUTER / name) == digest, 'work_note_changed_during_round:' + name)
    plan = OUTER / '接口验证后续规划.md'
    need(sha(plan) == sha(HERE / 'plan_before.md'), 'family_plan_changed_during_round')
    text = plan.read_text(encoding='utf-8')
    marker = '\n## 当前执行顺序\n'
    need(text.count(marker) == 1, 'execution_heading_not_unique')
    text = text.replace(marker, PLAN_ROW + marker)
    start = text.index(marker) + len(marker)
    while text[start] == '\n':
        start += 1
    end = text.index('\n\n', start)
    text = text[:start] + ('七类机制横向复核已完成（mechanism_cross_review_20261027），建议启动有界统一实现：先共享契约/账本构建器与收尾工具并回归、冻结评价协议与未接触候选池，再做最小表示扩展与薄统一入口；是否启动及顺序待用户决定。'
                           '新组件未入Git、SPARC与ACPI观察是否外报亦由用户决定。各接口未决项挂账；表示/R3暂缓、VT-d后置不变。') + text[end:]
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
        'mechanisms_reviewed': 7, 'directories_scanned': 79, 'new_experiments': 0, 'model_calls': 0,
        'independent_positive_normal': [0, 0]}, 'decision_owner': 'user'}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    (HERE / 'notes_before.json').write_text(json.dumps({'before_sha256': {n: sha(OUTER / n) for n in NOTES}},
                                                       ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    shutil.copyfile(OUTER / '接口验证后续规划.md', HERE / 'plan_before.md')


if __name__ == '__main__':
    prepare() if sys.argv[1:] == ['prepare'] else main()
