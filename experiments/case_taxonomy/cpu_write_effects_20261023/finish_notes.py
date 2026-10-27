"""Maintain the user-requested working notes after the bounded N2.22 loop."""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
OUTER = HERE.parents[3]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    result = json.loads((HERE / 'program_results_v2.json').read_text(encoding='utf-8'))
    assert result['status'] == 'bounded_source_facts_checked'
    assert '没有实质阻断' in (HERE / 'post_execution_review.md').read_text(encoding='utf-8')
    assert not (HERE / 'notes_update.json').exists(), 'preserve note update receipt'
    baseline = json.loads((HERE / 'notes_before.json').read_text(encoding='utf-8'))['before_sha256']
    originals = {name: (OUTER/name).read_bytes() for name in baseline}
    (HERE/'notes_integration_before.json').write_text(json.dumps(
        {'sha256': {name: sha(raw) for name, raw in originals.items()}}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    status = ('文档维护：2026-10-23；研究实验截止：2026-10-23 N2.22。用户确认先CPU拓扑相关，再迁移其他接口。'
              '本轮3次宿主对象构建、3份预处理；新直接写入候选组件区分可写分支1处赋值与FORCE/单CPU常量分支0处。'
              '首次解析不足及两项有限语法修复保留，修复后6项开发参考核对吻合、相关43测试通过；三项无条件候选仍不足。'
              '这是已读开发重放，外部对象绑定/完整要求推导未证，尚未接通生产CLI；模型0、完整内核构建/启动0、独立正/正常0/0。'
              '下一CPU-B / N2.23连接实际效果、目标及首次公共使用，尚未执行；其后CPU-C冻结与独立资格，再表示、页几何、IOMMU、DMA。R3仍暂缓。')
    body = ('本轮复用N2.21固定setter，三个事前编译分支首次采集均成功：可写分支在原include/linux/cpumask.h:38显示'
            '`nr_cpu_ids = nr`，FORCE4和NR_CPUS1为预处理常量绑定，只显示诊断替身计数器的条件写入。'
            '新增受限写入观察/候选适配器复用既有解析器，保留函数、符号、SHA、位置、分支和未知；'
            '同名局部、调用/指针和无条件效果不升级成外部状态证明。六项是3配置×2参考核对，非缺陷或准确率。\n\n'
            '首次程序分析被always_inline属性阻断，事后诊断明确标记；仅补精确属性和[0:0]人工位置的语法支持，'
            '原代码/中间版、首manifest和原dump保留，v2在相同产物上开发重放。43项相关测试通过，未重编译。'
            '研究者仍提供源范围、查询、配置及预期；WARN_ON是计数替身，不证明历史诊断全部效果；'
            '完整调用参数、目标对象和首次消费关系未闭合，新候选层尚非旧模型协议或生产CLI自动接通。\n\n'
            '本轮新增案例0、付费模型0请求/0token、完整内核构建/启动0，正式独立正/正常仍0/0；'
            'R3继续单独暂缓，Word/GitHub未改。计划及结果见[接口验证后续规划](接口验证后续规划.md)和'
            '[N2.22报告](linux_bug_analyze/experiments/case_taxonomy/cpu_write_effects_20261023/README.md)。'
            '下一[CPU-B / N2.23](linux_bug_analyze/experiments/case_taxonomy/cpu_write_effects_20261023/next_task_N223.md)'
            '优先连接s390/x86已有公共锁保护用途的准备资格、效果、对象和首次使用，分开程序事实、人工绑定和未知；不扩大运行网格。')
    heading = '## 10月23日 N2.22完成：配置下的直接写入事实与候选核对'
    updated = {}
    for name, raw in originals.items():
        text = raw.decode('utf-8-sig')
        if name == '当前代办.md':
            text = re.sub(r'(?m)^文档维护：[^\n]*\n*', '', text, count=1)
            text = text.replace('# 当前代办\n', '# 当前代办\n\n'+status+'\n', 1)
            text = re.sub(r'(?m)^- \[ \] \*\*CPU-A / N2\.22[^\n]*',
                          '- [x] **CPU-A / N2.22（10/23有限闭环完成）：** 3分支编译与直接写入候选核对完成，首次不足/修复保留；6项开发参考吻合、43项测试通过。外部绑定及完整链未证，见本轮README。', text, count=1)
            marker = '## 10月23日 用户确认的执行顺序'
            text = text.replace(marker, '## 当前下一操作：CPU-B / N2.23\n\n'+body+'\n\n'+marker, 1)
        elif name == '当前研究方向与进展.md':
            text = re.sub(r'(?m)^文档维护：[^\n]*', status, text, count=1)
            first_section = text.index('\n## ')
            text = text[:first_section]+'\n\n'+heading+'\n\n'+body+'\n'+text[first_section:]
        else:
            text = re.sub(r'(?m)^> 文档维护日期：[^\n]*', '> '+status, text, count=1)
            first_section = text.index('\n## ')
            text = text[:first_section]+'\n\n'+heading+'\n\n'+body+'\n'+text[first_section:]
            start = text.index('## 8. 下一项、未完成事项与暂停边界')
            end = text.index('\n## 9.', start)
            text = text[:start]+('## 8. 下一项、未完成事项与暂停边界\n\n'
                '当前N2.22有限开发闭环已完成，事实截止10/23；先CPU拓扑、后其他接口的顺序见首页及《接口验证后续规划》。'
                '旧N2.20正常资格不足不回填，N2.21旧运行/组合不重复计数。\n\n'
                '下一CPU-B / N2.23尚未执行：将配置下的实际效果与目标、调用实参和首次公共用途连接，先复用固定材料，'
                '不足明确留存，不扩大平台运行网格。其后CPU-C冻结支持域并有界审核独立问题与正常对照，资格不足也如实收束，'
                '再进入表示、页几何、IOMMU、DMA的已有材料迁移；不无限延长CPU支线。\n\n'
                '完整要求推导、规范/政策判断、外部对象与跨过程效果、精确消费与稳定性、合法对照的独立收益和其他接口迁移仍未完成。'
                '正式独立正/正常0/0不表示没有历史实验；N1/N2与R5/R6仍未完成。\n\n'
                'R3 shmem继续单独暂缓，不能因规划页几何就恢复该运行配对。旧模型拒绝及失败保留，不通过换词恢复拒绝内容。'
                '本轮三份工作文档的旧SHA保护同步收据在cpu_write_effects_20261023/notes_sync.json；镜像状态以该文件为准。\n')+text[end:]
        updated[name] = text.encode('utf-8')
    for name, raw in originals.items():
        assert (OUTER/name).read_bytes() == raw, 'concurrent working-note edit: '+name
    for name, raw in updated.items():
        (OUTER/name).write_bytes(raw)
    changes = {'before_sha256': baseline, 'after_sha256': {name: sha(raw) for name, raw in updated.items()},
               'names': list(updated), 'note': 'three working notes; initial hashes precede the authorized plan edits'}
    (HERE/'notes_update.json').write_text(json.dumps(changes, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    log = OUTER/'日志/2026-10-23.md'
    text = log.read_text(encoding='utf-8')
    assert heading not in text
    with log.open('a', encoding='utf-8') as handle:
        handle.write('\n\n'+heading+'\n\n'+body+'\n\n'
                     '执行前WSL沙箱服务拒绝后经工具审批恢复；另一次collector调用被尚未完成的独立门控拦住，未启动GCC。'
                     '真实3次编译首次均成功。独立角色完成执行前/后有限复核；同步以本阶段notes_sync.json为准。\n')
    plan = OUTER/'接口验证后续规划.md'
    text = plan.read_text(encoding='utf-8').replace('**N2.22，配置下的真实写入效果（当前执行）。**',
                                                 '**N2.22，配置下的真实写入效果（10/23有限闭环完成）。**')
    text += '\n本轮收尾：N2.22完成3分支编译及开发核对，首解析不足与v2修复保留；下一CPU-B / N2.23尚未执行。详见当前代办和本轮报告。\n'
    plan.write_text(text, encoding='utf-8')
    print(json.dumps({'updated_working_notes': len(updated), 'daily_log': '2026-10-23', 'next': 'CPU-B / N2.23'}))


if __name__ == '__main__':
    main()
