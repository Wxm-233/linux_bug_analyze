"""The frozen version-2 rules CTX, R7 and R10 (rules_v2_unified_20261103/rules2.py, ctx2.py) with the checked
architecture as a parameter (criteria_amendment1.md section 1). Only the architecture-specific constants are replaced;
every pattern, threshold and helper is the frozen one, imported unchanged. WSL; no model calls; labels are not read.
Usage: python3 rules_la.py ARCH SNAPSHOT OUT.json   (ARCH: loongarch, or riscv for the equivalence self-test)
"""
from pathlib import Path
import importlib.util
import json
import re
import sys
import time

HERE = Path(__file__).resolve().parent
V2 = HERE.parent / 'rules_v2_unified_20261103'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


R2 = load('rules2', V2 / 'rules2.py')  # also loads mech_rules (R2.MR) and mech_scan modules (R2.M)
M, MR = R2.M, R2.MR
ARCHES = {
    'riscv': {'ref': ('arm64', 'x86', 'loongarch'), 'own_prefix': 'riscv', 'extra_words': None,
              'r7_files': R2.R7_FILES},
    'loongarch': {'ref': ('arm64', 'x86', 'riscv'), 'own_prefix': 'loongarch', 'extra_words': re.compile(r'riscv|sbi', re.I),
                  'r7_files': re.compile(r'arch/loongarch/kvm/.*\.c$|arch/loongarch/kernel/(ptrace|signal|syscall|process)\.c$')},
}
ARCH = SNAP = CFG = None


def git(*a):
    return M.git(*a)


def arch_word(c):
    return M.ARCH_WORDS.search(c) or (CFG['extra_words'] and CFG['extra_words'].search(c))


# ------------------------------------------------------------------ R7 (R2.r7 with the directory as a parameter)
def internal_constant(name, text, var):
    head = text.split('{', 1)[0]
    m = re.search(r'\((.*)\)\s*$', head.strip(), re.S)
    if not m:
        return False
    plist = [MR.IDENT.findall(p.split('[')[0]) for p in R2.split_args(m.group(1))]
    pos = next((i for i, ids in enumerate(plist) if ids and ids[-1] == var), None)
    if pos is None:
        return False
    sites = 0
    for h in git('grep', '-h', '-E', r'(^|[^A-Za-z0-9_])' + name + r'[[:space:]]*\(', SNAP, '--', f'arch/{ARCH}').splitlines():
        for mm in re.finditer(r'(?<![A-Za-z0-9_])' + name + r'\s*\(([^;]*)\)\s*;', h):
            args = R2.split_args(mm.group(1))
            if len(args) > pos:
                sites += 1
                if not R2.CONST_ARG.fullmatch(args[pos]):
                    return False
    return sites > 0


def r7():
    out = []
    for p in [p for p in M.files(SNAP, f'arch/{ARCH}', ('.c',)) if CFG['r7_files'].match(p)]:
        for s, e, n, t in M.funcs(SNAP, p):
            hits = [h for h in MR.r7_function(p, s, e, n, t) if not internal_constant(n, t, h[1])]
            if hits:
                out.append({'rule': 'R7', 'path': p, 'name': n, 'start': s, 'end': e,
                            'reason': '; '.join(f'line {a}: [{v}] after bound check at line {c}, no array_index_nospec'
                                                for a, v, c in hits[:3]),
                            'issue': f'R7|{p}:{n}'})
    return out


# ------------------------------------------------------------------ R10 (MR.r10 + R2.r10 with the architecture as a parameter)
_KCONFIG = None


def kconfig():
    global _KCONFIG
    if _KCONFIG is None:
        _KCONFIG = ''.join(git('show', f'{SNAP}:{p}') for p in
                           git('ls-tree', '-r', '--name-only', SNAP, f'arch/{ARCH}').splitlines() if 'Kconfig' in p)
    return _KCONFIG


def config_gated_off(x):
    R2._KCONFIG = kconfig()  # R2.config_gated_off reads the Kconfig text through R2.riscv_kconfig()
    R2.SNAP = SNAP
    return R2.config_gated_off(x)


def own_defs():
    paths = M.files(SNAP, f'arch/{ARCH}', ('.c', '.h'))
    out = {}
    for p in paths:
        for s, e, n, t in M.funcs(SNAP, p):
            out.setdefault(n, []).append(p)
    return out


def r10():
    ref = CFG['ref']
    own = own_defs()
    names = [n for n in own if n not in M.GENERIC and not n.startswith(CFG['own_prefix'])]
    per_arch = {a: M.defs_in(SNAP, names, (f'arch/{a}/*.c', f'arch/{a}/*.h')) for a in ref}
    all3 = [n for n in names if all(n in per_arch[a] for a in ref)]
    common = M.called_in_common(SNAP, all3)
    out = []
    for n in sorted(set(all3) & common):
        impl = next((M.function(SNAP, p, n) for p in sorted(own[n], key=lambda p: not p.endswith('.c'))
                     if M.function(SNAP, p, n)), None)
        if not impl:
            continue
        impls = {}
        for a in ref:
            for p in sorted(per_arch[a].get(n, []), key=lambda p: not p.endswith('.c')):
                f = M.function(SNAP, p, n)
                if f:
                    impls[a] = f
                    break
        if len(impls) < 3:
            continue
        own_calls = M.call_names(impl['text'])
        sets = [M.call_names(f['text']) - own_calls for f in impls.values()]
        missing = sorted(c for c in set.intersection(*sets) if not arch_word(c) and c != n and not MR.AUX.fullmatch(c))
        if missing:
            common_defs = M.defs_in(SNAP, missing, ('*.c', '*.h', ':(exclude)arch', ':(exclude)tools'), macros=True)
            missing = [c for c in missing if c in common_defs]
        if not missing or R2.is_stub(impl['text']):
            continue
        kept = [x for x in missing[:8] if not config_gated_off(x)]
        if kept:
            out.append({'rule': 'R10', 'path': impl['path'], 'name': n, 'start': impl['start'], 'end': impl['end'],
                        'reason': f'all three references call {kept}, {ARCH} does not',
                        'refs': {a: f['path'] for a, f in impls.items()}, 'issue': f'R10|{impl["path"]}:{n}'})
    return out


# ------------------------------------------------------------------ CTX (ctx2 with the directory, references and trap handlers replaced)
def la_trap_handlers(C):
    def handlers():
        text = C.CK.git('show', f'{C.SNAP}:arch/loongarch/kernel/genex.S')
        names = {'do_' + h for h in re.findall(r'^\s*BUILD_HANDLER\s+\w+\s+(\w+)', text, re.M)}
        if re.search(r'\bdo_page_fault\b', C.CK.git('show', f'{C.SNAP}:arch/loongarch/mm/tlbex.S')):
            names.add('do_page_fault')
        return sorted(names)
    return handlers


def ctx():
    C = load('ctx2', V2 / 'ctx2.py')
    C.SNAP = SNAP
    if ARCH != 'riscv':
        C.RISCV = f'arch/{ARCH}'
        C.DEF_DIRS = (C.RISCV,) + C.DEF_DIRS[1:]
        C.REF = CFG['ref']
        C.trap_handlers = la_trap_handlers(C)
    idx, _ = C.build_index()
    C.INDEX.update(idx)
    flags, stats = C.run()
    out = []
    for f in C.dedupe(flags):
        last = f['chain'][-1][1] if f['chain'] else f['function']
        out.append({'rule': 'CTX', 'path': f['path'], 'name': f['function'], 'start': f['start'], 'end': f['end'],
                    'reason': f'{f["kind"]} {f["source"]}: line {f["line"]} {f["call"]} -> {f["sink"]}',
                    'chain': f['chain'], 'kind': f['kind'], 'source': f['source'],
                    'issue': f'CTX|{f["kind"]}|{last}|{f["sink"]}'})
    return out, stats.get('trap_handlers')


def main():
    global ARCH, SNAP, CFG
    ARCH, SNAP, target = sys.argv[1], sys.argv[2], Path(sys.argv[3]).resolve()
    CFG = ARCHES[ARCH]
    MR.SNAP = SNAP
    if target.exists():
        raise SystemExit('preserve')
    t0, flags, stats = time.time(), [], {'arch': ARCH, 'snapshot': SNAP}
    for name, fn in (('CTX', ctx), ('R7', r7), ('R10', r10)):
        t = time.time()
        got = fn()
        if name == 'CTX':
            got, stats['trap_handlers'] = got
        flags += got
        stats[name] = {'flags': len(got), 'issues': len({f['issue'] for f in got}), 'seconds': round(time.time() - t)}
    stats['seconds'] = round(time.time() - t0)
    target.write_text(json.dumps({'stats': stats, 'flags': flags}, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(stats, indent=1))


if __name__ == '__main__':
    main()
