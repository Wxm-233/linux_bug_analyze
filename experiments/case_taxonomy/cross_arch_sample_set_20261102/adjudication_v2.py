"""First annotator's review of the 15 disagreements in agreement_v2.json (both annotators are models; not a human
adjudication). Rows of kind first_error are applied on top of labels_v2.json (which is left unchanged) to give
labels_v2_1.json. Output: adjudication_v2.json, labels_v2_1.json, summary_v2_1.json.
"""
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from labels_v2 import FIELDS, stats  # noqa: E402

FIRST_ERROR = {
    'A102': (['M5', 'C', 'K2', 'arch/arm64/kernel/pi/Makefile（MMU建立前运行的代码去掉ftrace插桩、用-fpie）', 'S1', '0'],
             'arm64对MMU建立前运行的代码同样去掉插桩（git grep核实），属同一具体条件'),
    'A158': (['M5', 'C', 'K2', 'arch/arm/mm/alignment.c:do_alignment（原先开中断的，先开中断再访问用户内存）', 'S1', '0'],
             'arm的未对齐处理同一条件下先开中断（git grep核实）；与A344的标法一致'),
    'A238': (['M9', 'C', 'K2', 'arch/arm64/kernel/entry-ftrace.S:ftrace_stub（间接调用的汇编函数用SYM_TYPED_FUNC_START）', 'S1', '2'],
             'kCFI下被间接调用的汇编函数须带类型，arm64同样处理（git grep核实）；只在开启CFI时出错'),
    'A022': (['X2', 'R', '', '', '', ''], '宏中寄存器写错是笔误，按定义记X2'),
    'A176': (['M4', 'R', '', '', '', ''], '按内容优先：两把锁之间的竞争属M4，不是RISC-V规范语义'),
    'A234': (['M6', 'R', '', '', '', ''], '按内容优先：静态键初始化早于探测完成属初始化时序（M6）'),
}
BOUNDARY = {
    'A079': '第一遍已在arm64 head.S核实PT_REGS_SIZE保留；GPT看不到源码，维持C',
    'A144': 'arm64无条件选HAVE_FUNCTION_GRAPH_TRACER，找不到处理同一条件的对应代码，维持R',
    'B464': '在可抢占上下文用smp_processor_id是公共API的通用误用，不是跨架构约定，维持R；但修订2第3条“调用上下文”的写法确实可被读成任何API误用都算',
    'B559': 'IORT中未找到建立device link的代码（git grep），维持R',
    'A331': '维持M7（bitmap比较越界），材料只显示改用bitmap_equal，GPT读成规范化',
    'A288': 'M6（释放时恢复权限）与M10（module_alloc约定少一步）之争，维持M6',
    'B414': '缺陷在公共代码本身，M10按定义指各架构实现不同，不适用，维持M6',
    'B494': '未查到公共CPU设备注册在此前由possible改为present的提交，不能确定是M8，维持M7',
    'B531': 'M1（公共剥离规则的假设）与M9（KASAN加可重定位的配置组合）之争，维持M1',
}


def main():
    key = json.loads((HERE / 'agreement_v2.json').read_text(encoding='utf-8'))['disagreements']
    assert set(FIRST_ERROR) | set(BOUNDARY) == {d['id'] for d in key}
    rows = json.loads((HERE / 'labels_v2.json').read_text(encoding='utf-8'))
    by = {r['id']: r for r in rows}
    adj = []
    for i, (new, why) in FIRST_ERROR.items():
        adj.append({'id': i, 'kind': 'first_error', 'old': [by[i][f] for f in FIELDS], 'new': new, 'why': why})
        by[i].update(dict(zip(FIELDS, new)))
    adj += [{'id': i, 'kind': 'boundary', 'why': w} for i, w in BOUNDARY.items()]
    (HERE / 'adjudication_v2.json').write_text(json.dumps(adj, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'labels_v2_1.json').write_text(json.dumps(rows, indent=1, ensure_ascii=False) + '\n', encoding='utf-8',
                                           newline='\n')
    s = stats(rows)
    (HERE / 'summary_v2_1.json').write_text(json.dumps(s, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(s, ensure_ascii=False))


if __name__ == '__main__':
    main()
