"""Second-version labels (criteria_amendment2.md): frozen labels.json + labels_amendment1.md (adjudication.json
first_error rows) + the re-check of all C rows and all M8 rows under the tightened rules. Every change is listed
with its reason. Output: labels_v2.json, labels_v2_changes.json, summary_v2.json.
"""
from collections import Counter
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
FIELDS = ('mechanism', 'cross', 'counterpart_kind', 'counterpart', 'state', 'masking')
R = ('', '', '', '')

# id -> (field updates, reason); fields not given are kept
V2 = {
    'A095': ({'mechanism': 'M6', 'cross': 'R', **dict(zip(FIELDS[2:], R))},
             '规则3：数组只初始化第0项是通用编程错误，arm64同错，不是共享约定'),
    'A160': ({'mechanism': 'M6', 'cross': 'R', **dict(zip(FIELDS[2:], R))},
             '规则3：缺module_exit是通用错误，各架构同错'),
    'A280': ({'mechanism': 'M1', 'cross': 'R', **dict(zip(FIELDS[2:], R))},
             '规则4：x86的级名是固定数组，没有处理“运行时降级”这一条件；且只影响显示'),
    'A093': ({'mechanism': 'X2', 'cross': 'R', **dict(zip(FIELDS[2:], R))},
             '规则3：公共系统调用表的命名笔误，与架构无关'),
    'A062': ({'mechanism': 'M7'}, '机制规则2：修复改变的是参数按宽度传递，记M7'),
    'B446': ({'mechanism': 'M7'}, '机制规则2：修复补的是符号扩展，记M7'),
    'A026': ({'mechanism': 'M10', 'masking': '5'},
             '机制规则1：arm64在2019-12已处理.exit.text，RISC-V的patch.c于2020-03照arm64写成，参照对象先改好，按内容记M10、只移植了一半'),
    'A155': ({'mechanism': 'M10', 'masking': '4'},
             '机制规则1：arm64在2018年已导出保留区，早于RISC-V的init_resources，按内容记M10'),
    'A202': ({'mechanism': 'M10', 'masking': '4'},
             '机制规则1：x86在2017-01已修，早于RISC-V回溯代码，按内容记M10'),
    'A251': ({'mechanism': 'M10', 'masking': '4'},
             '机制规则1：arm64在2020年已修，RISC-V的CFI vDSO写于2026年，按内容记M10'),
    'A243': ({'mechanism': 'M10', 'masking': '4'},
             '机制规则1：公共regset note要求先于RISC-V新加的CFI regset，按内容记M10'),
    'B414': ({'mechanism': 'M6'}, '机制规则1：缺陷在公共crashkernel代码的资源插入时机本身，不是RISC-V未跟上'),
    'B425': ({'mechanism': 'M9'}, '机制规则1：缺陷在公共nopmd头文件本身，只在两级页表配置下出现，记M9'),
    'B498': ({'mechanism': 'M1'}, '机制规则1：公共剥离规则假设.rela.dyn不需要，RISC-V不成立，记M1'),
    'B531': ({'mechanism': 'M1'}, '机制规则1：公共剥离命令的假设在RISC-V可重定位加KASAN下不成立，记M1'),
    'B467': ({'counterpart_kind': 'K1', 'counterpart': 'kernel/events/core.c:perf_init_event（-ENOENT表示换下一个PMU继续尝试）'},
             '规则5：对应物改为perf核心的接口语义'),
    'A065': ({'counterpart': 'arch/loongarch/net/bpf_jit.c:build_insn（BPF_CALL处按调用约定sign_extend）'},
             '规则4：原对应物写的是x86“不需要扩展”，改为同样处理扩展的LoongArch JIT（git grep核实）'),
    'A195': ({'counterpart': 'arch/loongarch/net/bpf_jit.c:build_insn（BPF_CALL处按调用约定sign_extend）'}, '同A065'),
    'A277': ({'counterpart': 'arch/loongarch/net/bpf_jit.c:build_insn（BPF_CALL处按调用约定sign_extend）'}, '同A065'),
}


def stats(rows):
    kept = [r for r in rows if r['flag'] != '无关']
    c = [r for r in kept if r['cross'] == 'C']
    test_c = [r for r in c if not r['dev'] and r['flag'] != '构建错误']
    cnt = lambda rs, key: dict(sorted(Counter(r[key] for r in rs).items()))
    return {'kept': len(kept), 'C': len(c), 'C_share': round(len(c) / len(kept), 3),
            'C_A': sum(r['source'] == 'A' for r in c), 'C_B': sum(r['source'] == 'B' for r in c),
            'dev_C': sum(r['dev'] for r in c), 'test_C': sum(not r['dev'] for r in c),
            'test_C_without_build_errors': len(test_c),
            'C_by_mechanism': cnt(c, 'mechanism'), 'C_by_kind': cnt(c, 'counterpart_kind'),
            'C_by_state': cnt(c, 'state'), 'C_by_masking': cnt(c, 'masking'),
            'test_C_by_mechanism': cnt(test_c, 'mechanism'),
            'C_common_triggered': sum(r['common_triggered'] for r in c),
            'reference_line': '够用于评估' if len(test_c) >= 50 else '有限' if len(test_c) >= 25 else '不足'}


def main():
    rows = json.loads((HERE / 'labels.json').read_text(encoding='utf-8'))
    by = {r['id']: r for r in rows}
    changes = []
    for a in json.loads((HERE / 'adjudication.json').read_text(encoding='utf-8'))['rows']:
        if a['kind'] == 'first_error':
            r = by[a['id']]
            old = [r[f] for f in FIELDS]
            r.update(dict(zip(FIELDS, a['new'])))
            changes.append({'id': a['id'], 'source': '修订1', 'old': old, 'new': a['new'], 'why': a['why']})
    for i, (upd, why) in V2.items():
        r = by[i]
        old = [r[f] for f in FIELDS]
        assert r['cross'] == 'C' or upd.get('cross') == 'R', i
        r.update(upd)
        changes.append({'id': i, 'source': '修订2', 'old': old, 'new': [r[f] for f in FIELDS], 'why': why})
    assert not [r['id'] for r in rows if r['cross'] == 'C' and r['mechanism'] == 'M8' and r['id'] in
                ('A026', 'A155', 'A202', 'A251', 'A243')]
    (HERE / 'labels_v2.json').write_text(json.dumps(rows, indent=1, ensure_ascii=False) + '\n', encoding='utf-8',
                                         newline='\n')
    (HERE / 'labels_v2_changes.json').write_text(json.dumps(changes, indent=1, ensure_ascii=False) + '\n',
                                                 encoding='utf-8')
    v1 = stats(json.loads((HERE / 'labels.json').read_text(encoding='utf-8')))
    v2 = stats(rows)
    (HERE / 'summary_v2.json').write_text(json.dumps({'v1': v1, 'v2': v2, 'changes': len(changes)}, indent=1,
                                                     ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'v1': v1, 'v2': v2, 'changes': len(changes)}, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
