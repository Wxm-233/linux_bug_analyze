"""M5 automatic check (criteria.md, part 2): in every arch/*/ .c file at the range end, find calls that may sleep (or
cross-call and wait) inside a local-irq-disabled region of a function: from local_irq_disable/save to the first
textual enable/restore in the same function, expanding same-file callees one level. Also lists, for each flagged
function name, whether same-named functions in other architectures disable interrupts. WSL; no model calls.
Output: m5scan.json; prints a summary.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'mech_state_size_checker_20261101'))
import checker as CK  # noqa: E402  (git, functions, END)
from linux_bug_analyze.path_conditions import analyze  # noqa: E402

END = CK.END
DISABLE = re.compile(r'(raw_)?local_irq_(disable|save)$')
ENABLE = re.compile(r'(raw_)?local_irq_(enable|restore)$')
SLEEP = re.compile(r'smp_shutdown_nonboot_cpus|cpu_maps_update_begin|cpus_read_lock|cpus_write_lock|cpu_device_down'
                   r'|remove_cpu|mutex_lock\w*|down|down_read\w*|down_write\w*|down_interruptible|down_killable'
                   r'|msleep\w*|ssleep|usleep_range\w*|schedule\w*|wait_for_completion\w*|wait_event\w*'
                   r'|synchronize_rcu\w*|synchronize_srcu|flush_work|flush_workqueue|cancel_work_sync|kthread_stop'
                   r'|vmalloc|vzalloc|on_each_cpu\w*|smp_call_function\w*')


def sleeping(call):
    if SLEEP.fullmatch(call.name):
        return call.name
    if any(re.search(r'\bGFP_KERNEL\b', a) for a in call.args):
        return call.name + '(GFP_KERNEL)'
    return None


def scan_file(path):
    rows, irq_fns = [], set()
    fns = CK.functions(END, path)
    calls = {n: analyze(t) for s, e, n, t in fns}
    direct_sleep = {n: sorted({x for c in cs if (x := sleeping(c))}) for n, cs in calls.items()}
    for s, e, name, text in fns:
        cs = calls[name]
        if any(DISABLE.fullmatch(c.name) for c in cs):
            irq_fns.add(name)
        k = 0
        while k < len(cs):
            if not DISABLE.fullmatch(cs[k].name):
                k += 1
                continue
            start, j = cs[k], k + 1
            while j < len(cs) and not ENABLE.fullmatch(cs[j].name):
                j += 1
            for c in cs[k + 1:j]:
                hit = sleeping(c)
                via = None
                if not hit and c.name in direct_sleep and c.name != name and direct_sleep[c.name]:
                    hit, via = direct_sleep[c.name][0], c.name
                if hit:
                    rows.append({'arch': path.split('/')[1], 'file': path, 'function': name,
                                 'disable_line': s + start.line - 1, 'disable': start.name,
                                 'call_line': s + c.line - 1, 'call': hit, 'via': via,
                                 'region_closed': j < len(cs)})
            k = j + 1
    return rows, {(path.split('/')[1], n) for n in irq_fns}


def main():
    target = HERE / 'm5scan.json'
    if target.exists():
        raise SystemExit('preserve')
    files = [l.split(':', 1)[1] for l in CK.git('grep', '-l', '-E', 'local_irq_(disable|save)', END, '--',
                                                 'arch/*.c').splitlines()]
    files = [f for f in files if f.startswith('arch/')]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(scan_file, files))
    rows = [r for rs, _ in results for r in rs]
    irq = set().union(*(i for _, i in results))
    names = sorted({r['function'] for r in rows})
    # same-named functions in other architectures: do they disable interrupts?
    cross = {}
    for n in names:
        defs = {}
        for line in CK.git('grep', '-n', '-E', r'^[a-z_ ].*\b%s\(' % re.escape(n), END, '--', 'arch/*.c').splitlines():
            arch = line.split(':', 2)[1].split('/')[1]
            defs[arch] = (arch, n) in irq
        cross[n] = defs
    shutdown = {}
    for line in CK.git('grep', '-l', '-E', r'^void machine_shutdown\(', END, '--', 'arch/*.c').splitlines():
        path = line.split(':', 1)[1]
        for s, e, name, text in CK.functions(END, path):
            if name == 'machine_shutdown':
                cs = [c.name for c in analyze(text)]
                shutdown[path] = {'calls': cs,
                                  'irq_off_then_shutdown': any(DISABLE.fullmatch(c) for c in
                                                               cs[:cs.index('smp_shutdown_nonboot_cpus')])
                                  if 'smp_shutdown_nonboot_cpus' in cs else None}
    by_arch = {}
    for r in rows:
        by_arch[r['arch']] = by_arch.get(r['arch'], 0) + 1
    summary = {'files_scanned': len(files), 'flags': len(rows), 'functions_flagged': len(names), 'by_arch': by_arch,
               'riscv_machine_shutdown_flagged': any(r['arch'] == 'riscv' and r['function'] == 'machine_shutdown'
                                                     for r in rows)}
    target.write_text(json.dumps({'summary': summary, 'rows': rows, 'cross_arch': cross,
                                  'machine_shutdown': shutdown}, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(summary))
    for r in rows:
        print(r['arch'], r['file'], r['function'], r['disable_line'], r['call_line'], r['call'], r['via'] or '')
    for p, v in shutdown.items():
        print('SHUTDOWN', p, v['irq_off_then_shutdown'], v['calls'][:8])


if __name__ == '__main__':
    main()
