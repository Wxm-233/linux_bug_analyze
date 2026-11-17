"""目标切换的小样例，不含留出集内容。由 selftest.sh 在两个独立进程中调用。"""
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import extract3
import hints4
import rank
import settings as S

checks = []


def check(name, condition):
    assert condition, name
    checks.append(name)


check('架构顺序', S.ARCHS == (S.TARGET, 'arm64', 'x86_64'))
other = 'loongarch' if S.TARGET == 'riscv' else 'riscv'
check('抽取目标 kernel/mm', extract3.unit_class(f'arch/{S.TARGET}/kernel/x.c') == 'base' and
      extract3.unit_class(f'arch/{S.TARGET}/mm/x.c') == 'base')
check('不抽其他目标 kernel', extract3.unit_class(f'arch/{other}/kernel/x.c') is None)
drivers = ('riscv', 'sifive', '-sbi') if S.TARGET == 'riscv' else ('loongarch', 'loongson')
check('目标驱动', all(extract3.unit_class(f'drivers/test/{n}.c') == 'drivers' for n in drivers))
check('不抽对方驱动', extract3.unit_class(f'drivers/test/{other}.c') is None)
check('头文件宏来源', bool(S.ARCH_MAC_FILE.search(f'/src/arch/{S.TARGET}/include/asm/a.h')) and
      not S.ARCH_MAC_FILE.search(f'/src/arch/{other}/include/asm/a.h') and
      bool(S.ARCH_MAC_FILE.search('include/asm-generic/a.h')))
vals = {a: {'T_BOUND': 'nonconst', 'NR_syscalls': 100} for a in S.ARCHS}
entry = {'name': '__do_sys_demo', 'file': 'kernel/demo.c', 'line': 1, 'end': 9,
         'params': [['x', 'unsigned long']], 'body': ['T_BOUND', 'target_fn'],
         'calls': [['arch_fn', 'target_fn', [[0]]]], 'nr_ifs': [], 'unit_class': ['base'],
         'guards': [{'line': 3, 'p': [0], 'items': ['#T_BOUND', 'target_fn'],
                     'cmps': [{'op': '<', 'op_tok': '<', 'sides': [{'p': [0], 'const': None}, {'p': [], 'const': 10}]}]}]}
fn = {'name': 'target_fn', 'file': f'arch/{S.TARGET}/kernel/demo.c', 'line': 1, 'end': 9,
      'params': [['x', 'unsigned long']], 'body': [], 'calls': [], 'guards': [],
      'nr_ifs': [{'line': 5, 'p': [0]}], 'unit_class': ['base']}
facts = {'functions': {'entry': entry, 'arch_fn': fn},
         'macros': {'T_BOUND': {'file': f'arch/{S.TARGET}/include/asm/a.h', 'fl': True, 'body': []}}}
h = hints4.run(facts, vals, {'I1', 'I2', 'I3', 'I4'})
check('I1 目标宏/函数', h['stats']['tree_boundary'] == {'macros': 1, 'functions': 1})
check('提示点及参数映射', h['stats']['sites'] == 1 and h['sites']['demo'][0]['values']['0'] == ['i:9', 'i:a', 'i:b'])
check('K3 目标入口', h['raw_nr']['ifs'] == [{'fn': 'target_fn', 'file': fn['file'], 'line': 5}] and
      set(h['raw_nr']['NR_syscalls']) == set(S.ARCHS))
check('e=2 目标宏/函数', rank.evidence('T_BOUND', facts, vals, {'target_fn': [fn['file']]}) == 2 and
      rank.evidence('target_fn', facts, vals, {'target_fn': [fn['file']]}) == 2)
rank.selftest()
check('原排序公式样例', True)
if S.TARGET == 'loongarch':
    check('边界池为空且禁用开发集', not hints4.BALL and not rank.FIXITEMS and not rank.FIXC)
    env = dict(os.environ, TARGET='loongarch', BOUNDARY_POOL='existing')
    r = subprocess.run([sys.executable, '-c', 'import settings'], cwd=S.HERE, env=env, capture_output=True, text=True)
    check('拒绝错配池', r.returncode != 0 and 'LoongArch' in r.stderr)
else:
    check('RISC-V 使用原名单', bool(hints4.BALL) and S.BOUNDARY_POOL == 'existing')
out = S.HERE / 'tests'
out.mkdir(exist_ok=True)
(out / f'selftest_{S.TARGET}.json').write_text(json.dumps({'target': S.TARGET, 'passed': checks}, ensure_ascii=False, indent=2))
print(S.TARGET, 'PASS', len(checks))
