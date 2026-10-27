"""Close N2.23 and update the three mirrored working notes and daily log."""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
OUTER = HERE.parents[3]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    assert (HERE/'post_execution_review.md').is_file()
    assert not (HERE/'notes_update.json').exists(), 'preserve this round receipt'
    result = json.loads((HERE/'results_v2.json').read_text(encoding='utf-8'))
    states = [row['checked']['evaluation']['relation_at_observation'] for row in result['profiles']]
    assert states == ['violated','satisfied','satisfied','satisfied']
    assert len(result['controls']) == 16 and all(row['checked']['status']=='insufficient' for row in result['controls'])
    assert all(row['checked']['evaluation']['relation_at_deadline']=='insufficient' and
               row['checked']['evaluation']['whole_path']=='insufficient' for row in result['profiles'])
    before = json.loads((HERE/'notes_before.json').read_text(encoding='utf-8'))['before_sha256']
    original = {name:(OUTER/name).read_bytes() for name in before}
    assert {name:sha(raw) for name,raw in original.items()} == before, 'concurrent working-note changes'
    status = ('文档维护：2026-10-23；研究小闭环截止：2026-10-23 CPU-B / N2.23。'
              '同一已读案例四份历史运行完成归档/核心接线：旧s390采样成员关系不满足，其余三格满足；'
              '四项精确期限/完整路径仍不足。16项缺证据/错身份控制均不足，14项新方法测试通过。'
              '首驱动CRLF诊断失败与v2重放分存，核心/适配器/输入未因结果改写。'
              '这是已读特化集成，非新运行或独立检出；本轮模型、编译、启动、新案例均0，独立正/正常0/0。'
              '下一CPU-C / N2.24固定支持域并有界审核独立材料，尚未执行；之后表示、页几何、IOMMU、DMA。R3仍暂缓。')
    body = ('本轮新增的是将同run版本、配置、观察源码、日志行/序号和逻辑样本事实接入未改契约核心的特化适配器。'
            '用途和角色由源码复核作为人工条件性输入；程序不从旧status、predicates或WARN取答案。'
            '四格CPU1采样mask为0/2/2/2，成员关系为1项不满足、3项满足；最终成员诊断全满足，online诊断全不满足。'
            '四类各四项缺members、缺对象审核、错profile、抬样本为消费均保留不足；14项是方法测试，20条是4基线+16控制，均不是案例数。\n\n'
            '关键边界保持：旧s390 prepared=-1为未测；实际准备写入的完整因果、物理锁目标身份、精确首次遍历值和连续稳定未知。'
            'lock_snapshot在IRQ关闭/遍历前采样、解锁后打印；不能升级为真实期限，四项deadline及whole_path全部不足。'
            '旧foundation的first/stable命名不证明精确消费或稳定，也不向核心补语义前提。首次主驱动CRLF比较诊断断言停止，'
            'v2仅修诊断并单列结果，原失败/清单/输入保留；没有新模型、编译或内核启动。\n\n'
            '结果见[N2.23报告](linux_bug_analyze/experiments/case_taxonomy/cpu_topology_chain_20261023/README.md)与'
            '[执行后复核](linux_bug_analyze/experiments/case_taxonomy/cpu_topology_chain_20261023/post_execution_review.md)。'
            '本轮CPU-B有限接线收束，不为清零未知继续扩helper。下一[CPU-C / N2.24](linux_bug_analyze/experiments/case_taxonomy/cpu_topology_chain_20261023/next_task_N224.md)'
            '区分可复用组件与四格专用适配，固定支持域和人工依赖，有界审核一组未用于开发的同用途问题/正常参照；资格不足也如实收束，'
            '再按[接口规划](接口验证后续规划.md)迁移其他接口。完整N1/N2与独立评价未完成，R3仍暂缓。')
    heading = '## 10月23日 CPU-B / N2.23完成：同配置样本与公共用途接线'
    outputs = {}
    for name in before:
        # Universal newlines keep the live-note header independent of CRLF history.
        text = (OUTER/name).read_text(encoding='utf-8-sig')
        if name == '当前代办.md':
            start = text.index('## 10月23日 用户确认的执行顺序')
            text = '# 当前代办\n\n'+status+'\n\n## 当前下一操作：CPU-C / N2.24\n\n'+body+'\n\n'+text[start:]
            text = re.sub(r'(?m)^- \[ \] \*\*CPU-B：\*\*[^\n]*',
                          '- [x] **CPU-B（10/23有限接线完成，完整链未证）：** 四格采样/核心与16项控制接线完成，14项方法测试通过；精确消费、完整准备和物理对象仍不足。转CPU-C，不再扩helper清零。', text, count=1)
        elif name == '当前研究方向与进展.md':
            text = re.sub(r'(?m)^文档维护：[^\n]*',status,text,count=1)
            first = text.index('\n## ')
            text = text[:first]+'\n\n'+heading+'\n\n'+body+'\n'+text[first:]
        else:
            text = re.sub(r'(?m)^> 文档维护[^\n]*','> '+status,text,count=1)
            first = text.index('\n## ')
            text = text[:first]+'\n\n'+heading+'\n\n'+body+'\n'+text[first:]
            start = text.index('## 8. 下一项、未完成事项与暂停边界')
            end = text.index('\n## 9.',start)
            text = text[:start]+('## 8. 下一项、未完成事项与暂停边界\n\n'
                '当前CPU-B / N2.23受限接线完成，新增14项方法测试和20条已读开发记录；历史四次启动不重计。'
                '四格专用归档适配器不等于通用检测器，采样成员关系与实际期限/整条路径分开，后两者均不足。\n\n'
                '下一CPU-C / N2.24尚未执行：先固定可复用组件、人工输入和支持域，再有界审核一组独立同用途问题/正常参照。'
                '合格才安排同材料/预算比较，资格不足也保存分母与原因并收束；不无限补源或换样本凑结果。随后进入共享格式、页几何、IOMMU、DMA。\n\n'
                '完整要求推导、规范/政策处理、完整准备效果、物理锁对象、精确消费与稳定性、独立配置选择收益及其他接口迁移仍未完成。'
                '正式独立正/正常仍0/0，N1/N2和R5/R6未完成。R3 shmem继续单独暂缓，不因规划页几何而恢复。\n\n'
                '本轮工作文档镜像收据为cpu_topology_chain_20261023/notes_sync.json；实际一致性以收据及当前SHA为准。'
                '旧失败/拒绝保存，不换词恢复；Word/GitHub本轮未改。\n')+text[end:]
        outputs[name] = text.encode('utf-8')
    assert all((OUTER/name).read_bytes()==raw for name,raw in original.items())
    for name,raw in outputs.items():
        (OUTER/name).write_bytes(raw)
    changes = {'before_sha256':before,'after_sha256':{name:sha(raw) for name,raw in outputs.items()}}
    (HERE/'notes_update.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    log = OUTER/'日志/2026-10-23.md'
    assert heading not in log.read_text(encoding='utf-8')
    with log.open('a',encoding='utf-8') as stream:
        stream.write('\n\n'+heading+'\n\n'+body+'\n\n'
                     '本轮来源、方法、执行前后由独立助手限域复核；旧38归档与新输入/方法绑定一致。'
                     '首驱动停止在保存结果前，不能追认为首轮完成；v2的四基线/16控制已归档。三份工作笔记按旧SHA同步，收据见本阶段notes_sync.json。\n')
    plan = OUTER/'接口验证后续规划.md'
    text = plan.read_text(encoding='utf-8')
    text = text.replace('**连接准备资格、对象与首次使用。**','**连接准备资格、对象与首次使用（10/23受限样本接线完成，完整链仍不足）。**')
    text = re.sub(r'(?m)^本轮收尾：[^\n]*','当前停点：CPU-B / N2.23有限归档接线完成，四项真实期限和完整链不足保留。下一CPU-C / N2.24资格/支持域审查尚未执行，后续其他接口顺序不变。',text,count=1)
    plan.write_text(text,encoding='utf-8')
    print(json.dumps({'updated_notes':3,'daily_log':'2026-10-23','next':'CPU-C / N2.24'}))


if __name__ == '__main__':
    main()
