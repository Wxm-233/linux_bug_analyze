"""Execution-context rule checker, version 2 (rules_v2_unified_20261103/criteria.md section 1): the frozen checker of
ctx_rules_riscv_20261103 with I1 (path-sensitive region, trap-prefix and instrumentation state) and I2 (no _async
cross calls), version 3 adds P1 (rules_v3_precision_20261103/criteria.md): a callee that re-enables interrupts,
unlocks or re-enables preemption before a call is not followed further. The snapshot is set by the caller. WSL; no model calls; labels are not read.
"""
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
import json
import re
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'mech_state_size_checker_20261101'))
sys.path.insert(0, str(HERE.parents[2]))
import checker as CK  # noqa: E402
from linux_bug_analyze.path_conditions import analyze  # noqa: E402

SNAP = 'v6.12'
RISCV = 'arch/riscv'
DEF_DIRS = (RISCV, 'kernel', 'mm', 'lib', 'init', 'include/linux', 'include/asm-generic')
COMMON_CALLERS = ('kernel/', 'mm/', 'lib/', 'init/')
DEPTH = 3

DISABLE = re.compile(r'(raw_)?local_irq_(disable|save)')
ENABLE = re.compile(r'(raw_)?local_irq_(enable|restore)')
REGIONS = {  # kind: (acquire, release, hard)
    'irq': (DISABLE, ENABLE, True),
    'raw': (re.compile(r'raw_spin_lock(_irq|_irqsave|_bh|_nested|_irqsave_nested)?'),
            re.compile(r'raw_spin_unlock(_irq|_irqrestore|_bh)?'), True),
    'spin': (re.compile(r'(spin|read|write)_lock(_irq|_irqsave|_bh|_nested|_irqsave_nested)?'),
             re.compile(r'(spin|read|write)_unlock(_irq|_irqrestore|_bh)?'), False),
    'preempt': (re.compile(r'preempt_disable(_notrace)?|get_cpu'), re.compile(r'preempt_enable(_notrace|_no_resched)?|put_cpu'),
                False),
}
SLEEP = re.compile(r'smp_shutdown_nonboot_cpus|cpu_maps_update_begin|cpus_read_lock|cpus_write_lock|cpu_device_down'
                   r'|remove_cpu|mutex_lock\w*|down|down_read\w*|down_write\w*|down_interruptible|down_killable'
                   r'|msleep\w*|ssleep|usleep_range\w*|schedule\w*|wait_for_completion\w*|wait_event\w*'
                   r'|synchronize_rcu\w*|synchronize_srcu|flush_work|flush_workqueue|cancel_work_sync|kthread_stop'
                   r'|vmalloc|vzalloc'
                   r'|copy_from_user|copy_to_user|get_user|put_user|__get_user|__put_user|clear_user|strncpy_from_user'
                   r'|might_sleep|cond_resched')
XCALL = re.compile(r'on_each_cpu\w*|smp_call_function\w*')  # amendment 1a: only in hard contexts
ENDING = re.compile(r'(raw_)?local_irq_(enable|restore)|\w*_unlock\w*|preempt_enable\w*')  # P1
GFP = re.compile(r'\bGFP_(KERNEL|USER|KERNEL_ACCOUNT)\b')
RT_LOCK = REGIONS['spin'][0]
NO_DESCEND = re.compile(r'(pr_|printk|dev_|WARN|BUG|panic|dump_stack|trace_|lockdep_|kasan_|kcsan_|kmsan_'
                        r'|irqentry_|syscall_enter_from_user_mode|syscall_exit_to_user_mode|exit_to_user_mode'  # 1c
                        r'|.*for_each)')  # 1e
SKIP_FILES = ('mm/highmem.c',)  # amendment 1d
REF = ('arm64', 'x86', 'loongarch')
CALLBACK_USERS = re.compile(r'on_each_cpu\w*|smp_call_function\w*|stop_machine\w*|stop_one_cpu\w*')
INSTR_BEGIN, INSTR_END = 'instrumentation_begin', 'instrumentation_end'
NOINSTR_OK = re.compile(r'(^|\W)(noinstr|__cpuidle|__always_inline)(\W|$)')


# ------------------------------------------------------------------ index
def files():
    out = []
    for d in DEF_DIRS:
        out += [f for f in CK.git('ls-tree', '-r', '--name-only', SNAP, d).splitlines() if f.endswith(('.c', '.h'))]
    return out


def build_index():
    paths = files()
    index = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for p, fs in zip(paths, pool.map(lambda p: CK.functions(SNAP, p), paths)):
            if p in SKIP_FILES:
                continue
            for s, e, n, t in fs:
                if 'for_each' in n:
                    continue
                index.setdefault(n, []).append({'path': p, 'name': n, 'start': s, 'end': e, 'text': t,
                                                'head': t.split('{', 1)[0]})
    return index, len(paths)


INDEX = {}


def definition(name):
    defs = INDEX.get(name) or []
    for d in defs:
        if d['path'].startswith(RISCV):
            return d
    return defs[0] if defs else None


@lru_cache(maxsize=None)
def _calls(path, start, name):
    d = next(x for x in INDEX[name] if x['path'] == path and x['start'] == start)
    return analyze(d['text'])


def calls(d):
    return _calls(d['path'], d['start'], d['name'])


def is_init(d):
    return re.search(r'(^|\W)__init(\W|$)', d['head']) is not None


def prefix(a, b):
    return tuple(b[:len(a)]) == tuple(a)


def inside(cs, on, off, initially=False):
    """I1: the calls whose latest preceding on/off call on the same or an outer branch (conditions a prefix of the
    call's conditions) is an `on` call (or none and `initially`)."""
    out = []
    for i, c in enumerate(cs):
        state = initially
        for e in cs[:i]:
            if prefix(e.conds, c.conds):
                if on(e.name):
                    state = True
                elif off(e.name):
                    state = False
        if state and not on(c.name) and not off(c.name):
            out.append(c)
    return out


def regions(d):
    """[(kind, hard, [calls inside], None)] per region kind of d (I1); none in __init functions (amendment 1b)."""
    if is_init(d):
        return []
    cs = calls(d)
    out = []
    for kind, (acq, rel, hard) in REGIONS.items():
        if any(acq.fullmatch(c.name) for c in cs):
            ins = inside(cs, acq.fullmatch, rel.fullmatch)
            if ins:
                out.append((kind, hard, ins, None))
    return out


# ------------------------------------------------------------------ may-sleep closure
def sink(c, hard):
    if SLEEP.fullmatch(c.name):
        return 'sleep', c.name
    if any(GFP.search(a) for a in c.args):
        return 'sleep', c.name + '(GFP)'
    if hard and XCALL.fullmatch(c.name) and not c.name.endswith('_async'):  # I2
        return 'sleep', c.name
    if hard and RT_LOCK.fullmatch(c.name):
        return 'rt', c.name
    return None


@lru_cache(maxsize=None)
def closure(name, depth, hard, stack=()):
    if depth == 0 or NO_DESCEND.match(name) or name in stack:
        return None
    d = definition(name)
    if not d:
        return None
    for c in calls(d):
        if ENDING.fullmatch(c.name):  # P1: the callee ends the atomic context itself
            return None
        s = sink(c, hard)
        if s:
            return ((d['path'], d['name'], d['start'] + c.line - 1, c.name, s[0]),)
        sub = closure(c.name, depth - 1, hard, stack + (name,))
        if sub:
            return ((d['path'], d['name'], d['start'] + c.line - 1, c.name, None),) + sub
    return None


def check_region(owner, cs, hard, source, via, flags):
    for c in cs:
        if c.name == owner['name']:
            continue
        s = sink(c, hard)
        chain = ()
        if not s:
            chain = closure(c.name, DEPTH, hard)
            if not chain:
                continue
            s = (chain[-1][4], chain[-1][3])
        flags.append({'kind': s[0], 'source': source, 'via': via, 'path': owner['path'], 'function': owner['name'],
                      'start': owner['start'], 'end': owner['end'], 'line': owner['start'] + c.line - 1,
                      'call': c.name, 'sink': s[1], 'chain': [list(x) for x in chain]})


# ------------------------------------------------------------------ context sources
def riscv_defs():
    return [d for ds in INDEX.values() for d in ds if d['path'].startswith(RISCV)]


def trap_handlers():
    text = CK.git('show', f'{SNAP}:arch/riscv/kernel/entry.S')
    m = re.search(r'excp_vect_table\)(.*?)SYM_DATA_END', text, re.S)
    return sorted(set(re.findall(r'RISCV_PTR\s+(\w+)', m.group(1)))) if m else []


def run():
    flags, stats = [], {}
    rv = riscv_defs()
    rv_names = {d['name'] for d in rv}
    # A
    for d in rv:
        for kind, hard, cs, start in regions(d):
            check_region(d, cs, hard, 'A:' + kind, None, flags)
    # B
    handlers = trap_handlers()
    stats['trap_handlers'] = handlers
    for n in handlers:
        d = definition(n)
        if not d or not d['path'].startswith(RISCV):
            continue
        cs = calls(d)
        pre = inside(cs, lambda n: False, lambda n: n == 'local_irq_enable', initially=True)  # I1
        check_region(d, pre, True, 'B:trap', None, flags)
    # C
    cbs = {}
    for d in rv:
        for c in calls(d):
            if CALLBACK_USERS.fullmatch(c.name):
                for a in c.args:
                    a = a.strip().lstrip('&')
                    if re.fullmatch(r'[A-Za-z_]\w*', a) and a in rv_names:
                        cbs.setdefault(a, set()).add(f'{d["path"]}:{d["name"]}')
    stats['callbacks'] = {k: sorted(v) for k, v in cbs.items()}
    for n, via in cbs.items():
        d = definition(n)
        if d and d['path'].startswith(RISCV):
            check_region(d, calls(d), True, 'C:callback', sorted(via), flags)
    # D
    hooks = {}
    common = [d for ds in INDEX.values() for d in ds if d['path'].startswith(COMMON_CALLERS) and d['path'].endswith('.c')]
    ident = re.compile(r'([A-Za-z_]\w*)\s*\(')
    same_file = {}
    for d in common:
        same_file.setdefault(d['path'], []).append(d)
    local = {p: {d['name'] for d in ds} for p, ds in same_file.items()}

    def atomic_sites(g, name):
        return [(kind, hard) for kind, hard, cs, _ in regions(g) if any(c.name == name for c in cs)]

    for g in common:
        names = {m for m in ident.findall(g['text']) if m in rv_names and m not in local[g['path']]}
        if not names:
            continue
        for h in names:
            hit = [(k, hd, f'{g["path"]}:{g["name"]}') for k, hd in atomic_sites(g, h)]
            if not hit:
                for up in same_file[g['path']]:
                    if up is g or g['name'] + '(' not in up['text'].replace(' (', '('):
                        continue
                    hit += [(k, hd, f'{up["path"]}:{up["name"]}->{g["name"]}') for k, hd in atomic_sites(up, g['name'])]
            for k, hd, via in hit:
                hooks.setdefault(h, {}).setdefault(via, set()).add((k, hd))
    stats['hooks_in_atomic'] = len(hooks)
    for h, vias in hooks.items():
        d = definition(h)
        if not d or not d['path'].startswith(RISCV):
            continue
        hard = any(hd for v in vias.values() for _, hd in v)
        check_region(d, calls(d), hard, 'D:hook', sorted(f'{v} [{",".join(sorted(k for k, _ in s))}]'
                                                          for v, s in vias.items()), flags)
    # N1
    for g in [d for ds in INDEX.values() for d in ds if not d['path'].startswith(RISCV)]:
        if not re.search(r'(^|\W)(noinstr|__cpuidle)(\W|$)', g['head']):
            continue
        outside = instr_outside(g)
        for c in outside:
            d = definition(c.name)
            if c.name in rv_names and d and d['path'].startswith(RISCV) and not NOINSTR_OK.search(d['head'])                     and ref_noinstr(c.name):
                flags.append({'kind': 'noinstr', 'source': 'N1', 'via': [f'{g["path"]}:{g["name"]}'],
                              'path': d['path'], 'function': d['name'], 'start': d['start'], 'end': d['end'],
                              'line': d['start'], 'call': c.name, 'sink': 'called from noinstr/__cpuidle', 'chain': []})
    # N2
    for d in rv:
        if not re.search(r'(^|\W)noinstr(\W|$)', d['head']):
            continue
        for c in instr_outside(d):
            t = definition(c.name)
            if t and not re.search(r'(^|\W)(noinstr|__cpuidle|__always_inline|inline)(\W|$)', t['head']):
                flags.append({'kind': 'noinstr', 'source': 'N2', 'via': None, 'path': d['path'], 'function': d['name'],
                              'start': d['start'], 'end': d['end'], 'line': d['start'] + c.line - 1, 'call': c.name,
                              'sink': 'instrumentable callee', 'chain': [[t['path'], t['name'], t['start'], '', None]]})
    return flags, stats


@lru_cache(maxsize=None)
def ref_noinstr(name):
    """Reference arches whose definition of name is noinstr/__cpuidle/__always_inline (amendment 1f)."""
    out = []
    for h in CK.git('grep', '-n', '-E', r'^[A-Za-z_].*[^A-Za-z0-9_]' + name + r'[[:space:]]*\(', SNAP, '--',
                    *[f'arch/{a}' for a in REF]).splitlines():
        p = h.split(':', 3)
        if len(p) == 4 and not p[3].rstrip().endswith(';'):
            head = ' '.join(CK.git('show', f'{SNAP}:{p[1]}').splitlines()[max(0, int(p[2]) - 3):int(p[2])])
            if NOINSTR_OK.search(head):
                out.append(p[1])
    return tuple(sorted(set(out)))


@lru_cache(maxsize=None)
def instr_effect(name):
    """Amendment 1: INSTR_BEGIN or INSTR_END when the last instrumentation call in name's body is that call."""
    if name in (INSTR_BEGIN, INSTR_END):
        return name
    d = definition(name)
    if not d:
        return None
    last = [c.name for c in calls(d) if c.name in (INSTR_BEGIN, INSTR_END)]
    return last[-1] if last else None


def instr_outside(d):
    """I1: calls not inside an instrumentation_begin/end section on their own branch (helpers per amendment 1)."""
    cs = calls(d)
    ins = {id(c) for c in inside(cs, lambda n: instr_effect(n) == INSTR_BEGIN, lambda n: instr_effect(n) == INSTR_END)}
    return [c for c in cs if id(c) not in ins and instr_effect(c.name) is None]


def dedupe(flags):
    seen, out = set(), []
    for f in flags:
        k = (f['kind'], f['path'], f['function'], f['line'])  # amendment 1h
        if k not in seen:
            seen.add(k)
            out.append(f)
    return out


def main(out_name='flags.json'):
    target = HERE / out_name
    if target.exists():
        raise SystemExit('preserve')
    t0 = time.time()
    idx, n_files = build_index()
    INDEX.update(idx)
    flags, stats = run()
    flags = dedupe(flags)
    stats.update({'snapshot': SNAP, 'files_indexed': n_files, 'functions_indexed': sum(len(v) for v in INDEX.values()),
                  'riscv_functions': len(riscv_defs()), 'flags': len(flags),
                  'by_kind_source': {}, 'seconds': round(time.time() - t0)})
    for f in flags:
        k = f'{f["kind"]} {f["source"]}'
        stats['by_kind_source'][k] = stats['by_kind_source'].get(k, 0) + 1
    target.write_text(json.dumps({'stats': stats, 'flags': flags}, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in stats.items() if k not in ('callbacks', 'trap_handlers')}, indent=1))


if __name__ == '__main__':
    main(*sys.argv[1:])
