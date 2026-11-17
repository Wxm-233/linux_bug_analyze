"""M10 rules (criteria.md). R1: the syscall return value is preset to -ENOSYS, unconditionally, before the tracer
hook. R2: huge-mapping adjustment in arch KVM is guarded by a dirty-logging check (at the call or in the callee).
R3: before copying user extended state into the current task, the kernel's held state is given up.
Subcommands: dev (E1), scan (E2), search (E3 retrieval), heldout (E3 check of selected commits in heldout.json).
WSL; no model calls. Outputs: dev.json, scan.json, search.json, heldout_result.json.
"""
from pathlib import Path
import json
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'mech_state_size_checker_20261101'))
import checker as CK  # noqa: E402  (git, functions, END)
from linux_bug_analyze.path_conditions import analyze, occurrences  # noqa: E402

END = CK.END
R1_ANCHORS = {'syscall_enter_from_user_mode', 'syscall_enter_from_user_mode_work', 'syscall_trace_enter'}
R2_CALLS = {'transparent_hugepage_adjust', 'kvm_mmu_hugepage_adjust'}
R2_LOG = re.compile(r'logging|dirty_track|dirty_log|force_pte')
R3 = {
    'riscv': {'files': ['arch/riscv/kernel/signal.c'],
              'copy': lambda c: c.name in ('copy_from_user', '__copy_from_user') and c.args
              and 'current -> thread . vstate' in c.args[0],
              'claim': lambda c: c.name == 'riscv_v_vstate_set_restore'},
    'x86': {'files': ['arch/x86/kernel/fpu/signal.c'],
            'copy': lambda c: c.name == 'copy_sigframe_from_user_to_xstate'
            or (c.name == '__copy_from_user' and c.args and 'fxsave' in c.args[0]),
            'claim': lambda c: c.name == '__fpu_invalidate_fpregs_state'
            or (c.name == 'set_thread_flag' and any('TIF_NEED_FPU_LOAD' in a for a in c.args))},
    'arm64': {'files': ['arch/arm64/kernel/signal.c'],
              'copy': lambda c: c.name in ('copy_from_user', '__copy_from_user') and c.args
              and 'current -> thread' in c.args[0],
              'claim': lambda c: c.name == 'fpsimd_flush_task_state'},
}
DEV = {'R1': ('61119394631f', 'do_trap_ecall_u'), 'R2': ('b342166cbcf9', 'kvm_riscv_mmu_map'),
       'R3': ('c27fa53b858b', '__restore_v_state')}
SEARCH = {
    'R1': [['ENOSYS'], ['syscall|tracer|ptrace']],
    'R2': [['dirty log|dirty_log|dirty logging'], ['huge|THP|block|PMD']],
    'R3': [['sigreturn|signal'], ['restore'], ['FPU|SVE|fpsimd|vector|xstate']],
}


def grep_files(rev, pattern, spec):
    return [l.split(':', 1)[1] for l in CK.git('grep', '-l', '-E', pattern, rev, '--', spec).splitlines()]


def r1(rev, files=None):
    out = []
    for path in files or grep_files(rev, '|'.join(sorted(R1_ANCHORS)), 'arch/*.c'):
        for s, e, name, text in CK.functions(rev, path):
            if name in R1_ANCHORS:
                continue
            anchors = [c for c in analyze(text) if c.name in R1_ANCHORS]
            if not anchors:
                continue
            a = anchors[0]
            ok = [o for o in occurrences(text, {'ENOSYS'}) if o.line < a.line and set(o.conds) <= set(a.conds)]
            if not ok:
                out.append({'rule': 'R1', 'arch': path.split('/')[1], 'file': path, 'function': name,
                            'line': s + a.line - 1, 'anchor': a.name,
                            'enosys_lines': [s + o.line - 1 for o in occurrences(text, {'ENOSYS'})]})
    return out


def r2(rev, files=None):
    out = []
    for path in files or grep_files(rev, '|'.join(sorted(R2_CALLS)), 'arch/*/kvm/*.c'):
        fns = CK.functions(rev, path)
        bodies = {n: t for _, _, n, t in fns}
        for s, e, name, text in fns:
            if name in R2_CALLS:
                continue
            for c in analyze(text):
                if c.name not in R2_CALLS:
                    continue
                guarded = any(R2_LOG.search(t) for t, _ in c.conds)
                if not guarded and c.name in bodies:
                    callee_conds = [t for x in analyze(bodies[c.name]) for t, _ in x.conds]
                    guarded = any(R2_LOG.search(t) for t in callee_conds)
                if not guarded:
                    out.append({'rule': 'R2', 'arch': path.split('/')[1], 'file': path, 'function': name,
                                'line': s + c.line - 1, 'call': c.name,
                                'conds': [t for t, _ in c.conds]})
    return out


def r3(rev, arches=None):
    out = []
    for arch, spec in R3.items():
        if arches and arch not in arches:
            continue
        for path in spec['files']:
            if not CK.show(rev, path):
                continue
            for s, e, name, text in CK.functions(rev, path):
                calls = analyze(text)
                claims = [c.line for c in calls if spec['claim'](c)]
                for c in calls:
                    if spec['copy'](c) and not any(l < c.line for l in claims):
                        out.append({'rule': 'R3', 'arch': arch, 'file': path, 'function': name,
                                    'line': s + c.line - 1, 'copy': c.name})
    return out


RULES = {'R1': lambda rev: r1(rev), 'R2': lambda rev: r2(rev), 'R3': lambda rev: r3(rev)}


def flagged(rows, fn):
    return any(r['function'] == fn for r in rows)


def dev():
    res = {}
    for rule, (commit, fn) in DEV.items():
        parent = CK.git('rev-parse', commit + '^').strip()[:12]
        res[rule] = {'commit': commit, 'function': fn,
                     'parent_flagged': flagged([r for r in RULES[rule](parent) if r['arch'] == 'riscv'], fn),
                     'fixed_flagged': flagged([r for r in RULES[rule](commit) if r['arch'] == 'riscv'], fn)}
    return res


def search():
    res = {}
    for rule, groups in SEARCH.items():
        # -E: the patterns use '|' alternation (first run without it matched nothing; kept as search_run1_bre_bug.json)
        args = ['log', '--no-merges', '--format=%H %as %s', '-i', '-E', '--all-match', '--grep=Fixes:']
        args += ['--grep=%s' % g for (g,) in groups]
        rows = []
        for line in CK.git(*args, f'v5.0..{END}', '--', 'arch/', ':(exclude)arch/riscv').splitlines():
            sha, date, subject = line.split(' ', 2)
            rows.append({'commit': sha[:12], 'date': date, 'subject': subject})
        res[rule] = rows
    return res


def heldout():
    sel = json.loads((HERE / 'heldout.json').read_text(encoding='utf-8'))
    out = []
    for x in sel['selected']:
        parent = CK.git('rev-parse', x['commit'] + '^').strip()[:12]
        rows = RULES[x['rule']](parent)
        out.append({**x, 'parent': parent, 'flagged': flagged(rows, x['function']),
                    'flags_at_parent_same_arch': [r for r in rows if r['arch'] == x['arch']]})
    return out


def main():
    cmd = sys.argv[1]
    target = HERE / {'dev': 'dev.json', 'scan': 'scan.json', 'search': 'search.json',
                     'heldout': 'heldout_result.json'}[cmd]
    if target.exists():
        raise SystemExit('preserve')
    if cmd == 'dev':
        data = dev()
    elif cmd == 'scan':
        data = {rule: f(END) for rule, f in RULES.items()}
    elif cmd == 'search':
        data = search()
    else:
        data = heldout()
    target.write_text(json.dumps(data, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(data, indent=1, ensure_ascii=False)[:6000])


if __name__ == '__main__':
    main()
