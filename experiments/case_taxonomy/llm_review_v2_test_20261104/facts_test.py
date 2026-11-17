"""Program facts of the test round (criteria.md section 3): llm_review_v2_dev2_20261104/facts2.py imported unchanged,
with MIPS added: the architecture name, the hand-written MIPS table (written before any MIPS sample was seen), and the
exception-entry registration fact, which for MIPS names the BUILD_HANDLER clear argument. LoongArch is unchanged.
WSL (git); no model. facts(row, arch) -> [{'id', 'text'}]."""
from functools import lru_cache
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'llm_review_v2_dev2_20261104'))
import facts2  # noqa: E402
from facts2 import F1, git  # noqa: E402

F1.ARCH_NAME['mips'] = 'MIPS'
F1.ARCH_TABLE['mips'] = [
    '进入异常时，硬件置位CP0 Status寄存器的EXL位，此时中断被屏蔽。',
    '异常入口arch/mips/kernel/genex.S中，BUILD_HANDLER的第三个参数决定调用处理函数之前的中断状态：'
    'sti、gsexc打开中断；cli、fpe、msa_fpe关闭中断；ade执行KMODE，保持异常发生前的中断开关状态；'
    'none不改变（EXL仍置位，中断仍被屏蔽）。页错误入口arch/mips/mm/tlbex-fault.S也执行KMODE。'
    '（出处：genex.S中的__build_clear_*宏，arch/mips/include/asm/stackframe.h中的CLI、STI、KMODE宏）',
]
_entry_handlers = F1.entry_handlers


@lru_cache(maxsize=None)
def entry_handlers(rev, arch):
    if arch != 'mips':
        return _entry_handlers(rev, arch)
    out, clear = {}, {}
    text = git('show', f'{rev}:arch/mips/kernel/genex.S')
    for h, c in re.findall(r'^\s*BUILD_HANDLER\s+\w+\s+(\w+)\s+(\w+)', text, re.M):
        clear.setdefault('do_' + h, [])
        if c not in clear['do_' + h]:
            clear['do_' + h].append(c)
    for name, cs in clear.items():
        out[name] = f'arch/mips/kernel/genex.S，BUILD_HANDLER第三个参数为{"或".join(cs)}'
    fault = git('show', f'{rev}:arch/mips/mm/tlbex-fault.S')
    if re.search(r'\bdo_page_fault\b', fault):
        out['do_page_fault'] = 'arch/mips/mm/tlbex-fault.S' + ('，KMODE' if re.search(r'\bKMODE\b', fault) else '')
    return out


F1.entry_handlers = entry_handlers
ARCH_NAME, ARCH_TABLE = F1.ARCH_NAME, F1.ARCH_TABLE
facts = facts2.facts
