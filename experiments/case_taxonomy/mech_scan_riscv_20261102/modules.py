"""Check-point enumeration and facts for the mechanism modules of criteria.md section 2 (M1, M5, M8, M10; M2 via
the existing checker). Shared with llm_counterpart_pilot_20261102 (criteria_amendment3.md). WSL; no model calls.
"""
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'mech_state_size_checker_20261101'))
sys.path.insert(0, str(ROOT.parent.parent))
import checker as CK  # noqa: E402
from linux_bug_analyze.path_conditions import analyze  # noqa: E402

REF = ('arm64', 'x86', 'loongarch')
ARCH_WORDS = re.compile(r'arm64|aarch64|x86|loongarch|lsx|lasx|sve|fpsimd|mte|ptrauth|kvm_arm|vgic|ibt|tdx|sev|'
                        r'cpu_feature_enabled|boot_cpu_has|static_cpu_has', re.I)
GENERIC = {'init', 'setup', 'main', 'probe', 'remove', 'show', 'store', 'open', 'release', 'read', 'write', 'ioctl'}
DISABLE = re.compile(r'(raw_)?local_irq_(disable|save)$')
ENABLE = re.compile(r'(raw_)?local_irq_(enable|restore)$')
SLEEP = re.compile(r'(mutex_lock\w*|down(_read|_write|_interruptible|_killable)?\w*|msleep\w*|ssleep|usleep_range\w*|'
                   r'schedule\w*|wait_for_completion\w*|wait_event\w*|synchronize_(rcu|srcu)\w*|flush_work\w*|'
                   r'cancel_work_sync|kthread_stop|cpus_(read|write)_lock|cpu_maps_update_begin|'
                   r'smp_shutdown_nonboot_cpus|copy_(from|to)_user|get_user|put_user|vmalloc|vzalloc|'
                   r'on_each_cpu\w*|smp_call_function\w*)$')
CTX_MARKS = ('noinstr', '__cpuidle', '__kprobes')


def git(*a):
    return CK.git(*a)


@lru_cache(maxsize=None)
def files(rev, prefix, exts=('.c', '.h')):
    return [f for f in git('ls-tree', '-r', '--name-only', rev, prefix).splitlines() if f.endswith(exts)]


@lru_cache(maxsize=None)
def funcs(rev, path):
    return CK.functions(rev, path)


def function(rev, path, name):
    for s, e, n, t in funcs(rev, path):
        if n == name:
            return {'path': path, 'name': name, 'start': s, 'end': e, 'text': t}
    return None


def riscv_defs(rev, exts=('.c', '.h')):
    """{name: [path]} for functions defined in arch/riscv at rev."""
    paths = files(rev, 'arch/riscv', exts)
    out = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for p, fs in zip(paths, pool.map(lambda p: funcs(rev, p), paths)):
            for s, e, n, t in fs:
                out.setdefault(n, []).append(p)
    return out


def defs_in(rev, names, where, macros=False):
    """{name: set(path)} for function definitions (and #define when macros) under `where` (git pathspecs)."""
    names = sorted({n for n in names if re.fullmatch(r'[A-Za-z_]\w*', n)})
    out = {}
    for k in range(0, len(names), 80):
        chunk = names[k:k + 80]
        alt = '|'.join(chunk)
        pat = r'^[A-Za-z_].*[^A-Za-z0-9_](' + alt + r')[[:space:]]*\('
        if macros:
            pat = r'(' + pat + r')|(^#[[:space:]]*define[[:space:]]+(' + alt + r')([^A-Za-z0-9_]|$))'
        for line in git('grep', '-n', '-E', pat, rev, '--', *where).splitlines():
            parts = line.split(':', 3)
            if len(parts) < 4:
                continue
            text = ' ' + parts[3]
            for n in chunk:
                if re.search(r'[^A-Za-z0-9_]' + n + r'[ \t]*\(', text) or (
                        macros and re.match(r'\s*#\s*define\s+' + n + r'\b', parts[3])):
                    out.setdefault(n, set()).add(parts[1])
    return out


def called_in_common(rev, names):
    names = sorted({n for n in names if re.fullmatch(r'[A-Za-z_]\w*', n)})
    found = set()
    for k in range(0, len(names), 80):
        chunk = names[k:k + 80]
        pat = r'(^|[^A-Za-z0-9_])(' + '|'.join(chunk) + r')[[:space:]]*\('
        out = git('grep', '-h', '-o', '-E', pat, rev, '--', '*.c', ':(exclude)arch', ':(exclude)tools',
                  ':(exclude)Documentation', ':(exclude)scripts')
        for m in re.finditer(r'([A-Za-z_]\w*)\s*\($', out, re.M):
            found.add(m.group(1))
        found |= {n for n in chunk if re.search(r'(^|[^A-Za-z0-9_])' + n + r'\s*\(', out, re.M)}
    return found


def call_names(text):
    return {c.name for c in analyze(text)}


def facts(cand):
    """Calls with path conditions, and calls inside irq-disabled regions (shared with the pilot's 2c)."""
    calls = analyze(cand['text'])
    rows = []
    for c in calls[:40]:
        cond = ' 且 '.join(e if pos else f'非({e})' for e, pos in c.conds) if c.conds else '（无条件）'
        rows.append(f'第{cand["start"] + c.line - 1}行 调用 {c.name}，条件：{cond}')
    irq, k = [], 0
    while k < len(calls):
        if DISABLE.fullmatch(calls[k].name):
            j = k + 1
            while j < len(calls) and not ENABLE.fullmatch(calls[j].name):
                j += 1
            irq += [(cand['start'] + c.line - 1, c.name) for c in calls[k + 1:j]]
            k = j
        k += 1
    return rows, irq


# ---------------------------------------------------------------- M10
def m10_points(rev, rv=None):
    rv = rv or riscv_defs(rev)
    names = [n for n in rv if n not in GENERIC and not n.startswith('riscv')]
    per_arch = {a: defs_in(rev, names, (f'arch/{a}/*.c', f'arch/{a}/*.h')) for a in REF}
    multi = [n for n in names if sum(n in per_arch[a] for a in REF) >= 2]
    common = called_in_common(rev, multi)
    points = []
    for n in sorted(set(multi) & common):
        rv_impl = next((function(rev, p, n) for p in sorted(rv[n], key=lambda p: not p.endswith('.c'))
                        if function(rev, p, n)), None)
        if not rv_impl:
            continue
        impls = {}
        for a in REF:
            for p in sorted(per_arch[a].get(n, []), key=lambda p: not p.endswith('.c')):
                f = function(rev, p, n)
                if f:
                    impls[a] = f
                    break
        if len(impls) < 2:
            continue
        rv_calls = call_names(rv_impl['text'])
        counts = {}
        for a, f in impls.items():
            for c in call_names(f['text']):
                if c not in rv_calls and not ARCH_WORDS.search(c) and c != n:
                    counts[c] = counts.get(c, 0) + 1
        missing = sorted(c for c, k in counts.items() if k >= 2)
        if missing:
            points.append({'module': 'M10', 'path': rv_impl['path'], 'name': n, 'missing': missing,
                           'refs': {a: f['path'] for a, f in impls.items()}})
    return points


# ---------------------------------------------------------------- M1
def m1_defaults(rev):
    """[(name, path, kind)] of overridable defaults in common code."""
    out = []
    weak = git('grep', '-n', '-E', r'__weak', rev, '--', '*.c', ':(exclude)arch', ':(exclude)tools',
               ':(exclude)Documentation', ':(exclude)scripts')
    for line in weak.splitlines():
        parts = line.split(':', 3)
        if len(parts) < 4:
            continue
        m = re.search(r'([A-Za-z_]\w*)\s*\(', parts[3])
        if m and m.group(1) not in ('__weak',):
            out.append((m.group(1), parts[1], 'weak'))
    for path in files(rev, 'include/linux', ('.h',)) + files(rev, 'include/asm-generic', ('.h',)):
        lines = git('show', f'{rev}:{path}').splitlines()
        for k, l in enumerate(lines):
            m = re.match(r'#\s*ifndef\s+([a-z_][a-z0-9_]*)\s*$', l)
            if not m:
                continue
            n = m.group(1)
            window = '\n'.join(lines[k + 1:k + 4])
            if re.search(r'#\s*define\s+' + n + r'\b', window) or re.search(r'[^A-Za-z0-9_]' + n + r'\s*\(', window):
                out.append((n, path, 'ifndef'))
    seen, uniq = set(), []
    for n, p, kind in out:
        if n not in seen:
            seen.add(n)
            uniq.append((n, p, kind))
    return uniq


def m1_points(rev):
    defaults = m1_defaults(rev)
    names = [n for n, _, _ in defaults]
    rv = defs_in(rev, names, ('arch/riscv/*.c', 'arch/riscv/*.h', 'drivers/acpi/riscv/*.c'), macros=True)
    per_arch = {a: defs_in(rev, names, (f'arch/{a}/*.c', f'arch/{a}/*.h', f'drivers/acpi/{a}/*.c'), macros=True)
                for a in REF}
    points = []
    for n, p, kind in defaults:
        over = [a for a in REF if n in per_arch[a]]
        if over and n not in rv:
            points.append({'module': 'M1', 'name': n, 'default_path': p, 'kind': kind, 'overridden_by': over,
                           'ref_paths': {a: sorted(per_arch[a][n]) for a in over}})
    return points


# ---------------------------------------------------------------- M5
def m5_points(rev):
    points = []
    for path in files(rev, 'arch/riscv', ('.c',)):
        for s, e, n, t in funcs(rev, path):
            head = t.split('{', 1)[0]
            marks = [m for m in CTX_MARKS if m in head]
            calls = [c.name for c in analyze(t)]
            irq = any(DISABLE.fullmatch(c) for c in calls)
            entry = n.startswith(('do_trap_', 'handle_'))
            if marks or irq or entry:
                points.append({'module': 'M5', 'path': path, 'name': n, 'marks': marks, 'irq_region': irq,
                               'entry': entry})
    return points


# ---------------------------------------------------------------- M8
def last_change(rev, path, name, since=None):
    args = ['log', '--format=%H %cI', '-s', '-L', f':{name}:{path}']
    if since:
        args.insert(1, f'--since={since}')
    out = git(*args, rev)
    return [l.split() for l in out.splitlines() if re.fullmatch(r'[0-9a-f]{40} \S+', l.strip())]


def m8_pair(rev, n, rp, ap):
    rv_hist = last_change(rev, rp, n)
    if not rv_hist:
        return None
    rv_last = rv_hist[0][1]
    fixes = []
    for sha, d in last_change(rev, ap, n, rv_last):
        if d > rv_last and re.search(r'^\s*Fixes:', git('log', '-1', '--format=%B', sha), re.M | re.I):
            fixes.append({'sha': sha[:12], 'date': d[:10]})
    if fixes:
        return {'module': 'M8', 'path': rp, 'name': n, 'arm64_path': ap, 'riscv_last_change': rv_last[:10],
                'arm64_fixes': fixes}
    return None


def m8_points(rev, rv=None):
    rv = rv or riscv_defs(rev, ('.c',))
    names = [n for n in rv if n not in GENERIC and not n.endswith('__init')]
    a64 = defs_in(rev, names, ('arch/arm64/*.c',))
    pairs = [(n, sorted(rv[n])[0], sorted(a64[n])[0]) for n in sorted(a64) if n in rv]
    with ThreadPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(lambda x: m8_pair(rev, *x), pairs))
    return [r for r in res if r], len(pairs)


# ---------------------------------------------------------------- M2
def m2_points(rev):
    rows = CK.check(rev, 'riscv')
    return [{'module': 'M2', 'path': r['file'], 'name': r['function'], 'line': r['line'], 'verdict': r['verdict']}
            for r in rows if r['verdict'] in ('strong', 'weak')]
