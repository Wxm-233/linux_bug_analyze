"""Program facts for one rule flag at its snapshot (criteria.md section 3): only facts read directly from the code,
numbered F1, F2, ... WSL (git); no model. facts(row, arch) -> [{'id', 'text'}]; ARCH_TABLE holds the hand-written
architecture facts (at most three per architecture, the same for every CTX flag of that architecture)."""
from functools import lru_cache
from pathlib import Path
import ast
import importlib.util
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'mech_state_size_checker_20261101'))
sys.path.insert(0, str(HERE.parents[2]))
import checker as CK  # noqa: E402
from linux_bug_analyze.path_conditions import analyze  # noqa: E402

spec = importlib.util.spec_from_file_location('ctx2', HERE.parent / 'rules_v2_unified_20261103' / 'ctx2.py')
C2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C2)  # region patterns only
ARCH_NAME = {'loongarch': 'LoongArch', 'riscv': 'RISC-V'}
ARCH_TABLE = {
    'loongarch': ['进入异常时硬件关闭中断（清除CSR.CRMD.IE），原来的中断状态保存在CSR.PRMD.PIE。',
                  '内核的异常处理函数按PIE决定是否重新开中断，见traps.c中各do_*的'
                  '“if (regs->csr_prmd & CSR_PRMD_PIE) local_irq_enable()”。'],
}
COMMON = ('init', 'kernel', 'mm')


def git(*a):
    return CK.git(*a)


@lru_cache(maxsize=None)
def function(rev, path, name):
    for s, e, n, t in CK.functions(rev, path):
        if n == name:
            return s, t
    return None


@lru_cache(maxsize=None)
def kconfig_selects(rev, arch, symbol):
    hits = git('grep', '-n', '-E', r'^[[:space:]]*select[[:space:]]+' + symbol + r'([[:space:]]|$)', rev, '--',
               f'arch/{arch}/Kconfig*', f'arch/{arch}/**/Kconfig*')
    return [h.split(':', 1)[1] for h in hits.splitlines()]


@lru_cache(maxsize=None)
def entry_handlers(rev, arch):
    """{name: source file} of exception handlers registered by the entry code."""
    out = {}
    if arch == 'loongarch':
        text = git('show', f'{rev}:arch/loongarch/kernel/genex.S')
        for h in re.findall(r'^\s*BUILD_HANDLER\s+\w+\s+(\w+)', text, re.M):
            out['do_' + h] = 'arch/loongarch/kernel/genex.S'
        if re.search(r'\bdo_vint\b', text):
            out['do_vint'] = 'arch/loongarch/kernel/genex.S（中断入口）'
        if re.search(r'\bdo_page_fault\b', git('show', f'{rev}:arch/loongarch/mm/tlbex.S')):
            out['do_page_fault'] = 'arch/loongarch/mm/tlbex.S'
    elif arch == 'riscv':
        text = git('show', f'{rev}:arch/riscv/kernel/entry.S')
        m = re.search(r'excp_vect_table\)(.*?)SYM_DATA_END', text, re.S)
        for h in re.findall(r'RISCV_PTR\s+(\w+)', m.group(1)) if m else []:
            out[h] = 'arch/riscv/kernel/entry.S'
    return out


def cond_text(conds):
    return ' 且 '.join(t if pos else f'!({t})' for t, pos in conds) if conds else '无条件'


def state_calls(rev, path, name):
    """Lines of interrupt and lock state changes in name, with their branch conditions."""
    f = function(rev, path, name)
    if not f:
        return []
    s, text = f
    pats = [C2.DISABLE, C2.ENABLE] + [p for acq, rel, _ in C2.REGIONS.values() for p in (acq, rel)]
    out = []
    for c in analyze(text):
        if any(p.fullmatch(c.name) for p in pats):
            out.append(f'第{s + c.line - 1}行调用{c.name}，条件：{cond_text(c.conds)}')
    return out[:12]


def call_sites(rev, name, dirs, limit):
    """Lines that call name (definitions, prototypes and #defines left out)."""
    def is_decl(line):
        if re.match(r'\s*#\s*define\b', line):
            return True
        m = re.search(r'(?<![A-Za-z0-9_])' + name + r'\s*\(', line)
        words = re.fullmatch(r'\s*((?:[A-Za-z_]\w*[\s\*]+)+)', line[:m.start()]) if m else None
        return bool(words) and words.group(1).split()[0] not in ('return', 'else', 'case', 'goto')

    out = []
    for h in git('grep', '-n', '-E', r'(^|[^A-Za-z0-9_])' + name + r'[[:space:]]*\(', rev, '--', *dirs).splitlines():
        p = h.split(':', 3)
        if len(p) == 4 and not is_decl(p[3]) and not p[3].strip().startswith(('*', '/*', '//')):
            out.append(f'{p[1]}第{p[2]}行：{p[3].strip()[:100]}')
        if len(out) >= limit:
            break
    return out


def facts(row, arch):
    rev, rule, path, name = row['snapshot'], row['rule'], row['path'], row['name']
    an = ARCH_NAME[arch]
    texts = []
    if rule == 'CTX':
        handlers = entry_handlers(rev, arch)
        if name in handlers:
            texts.append(f'{name}是由异常入口代码登记的处理函数（{handlers[name]}）。')
        else:
            texts.append(f'{name}不在异常入口代码登记的处理函数之列。')
        sc = state_calls(rev, path, name)
        texts.append(f'{name}中改变中断或锁状态的调用（条件按代码的分支结构算出，goto跳转未计入）：' + ('；'.join(sc) if sc else '没有') + '。')
        if row.get('kind') == 'rt':
            sel = kconfig_selects(rev, arch, 'ARCH_SUPPORTS_RT')
            texts.append(f'该版本{an}的Kconfig中{"有" if sel else "没有"}“select ARCH_SUPPORTS_RT”，'
                         f'即{"可以" if sel else "不能"}开启PREEMPT_RT。')
        if row.get('kind') == 'noinstr':
            sel = kconfig_selects(rev, arch, 'HAVE_NOINSTR_VALIDATION')
            texts.append(f'该版本{an}的Kconfig中{"有" if sel else "没有"}“select HAVE_NOINSTR_VALIDATION”，'
                         f'即objtool{"会" if sel else "不会"}校验noinstr代码中的调用。')
    elif rule == 'R7':
        sites = call_sites(rev, name, (f'arch/{arch}',), 5)
        texts.append(f'{name}在{an}目录中的调用位置：' + ('；'.join(sites) if sites else '没有找到') + '。')
    elif rule == 'R10':
        m = re.search(r'call (\[.*\]),', row.get('reason') or '')
        for x in (ast.literal_eval(m.group(1)) if m else [])[:4]:
            common = call_sites(rev, x, COMMON, 3)
            own = call_sites(rev, x, (f'arch/{arch}',), 3)
            texts.append(f'{x}在公共代码（init、kernel、mm）中的调用位置：' + ('；'.join(common) if common else '没有找到')
                         + f'；在{an}目录中的调用位置：' + ('；'.join(own) if own else '没有') + '。')
    return [{'id': f'F{k + 1}', 'text': t} for k, t in enumerate(texts)]
