import gzip, json, sys
P = '/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/heldout_prep_20261110/pipeline'
sys.path.insert(0, P)
src = open(P + '/hints4.py').read()
assert src.count('DEPTH = 8 if I4 else 4') == 1
for g, tag in (("A101", "A101_pre"), ("CUR", "CUR")):
    F = json.load(gzip.open(f'/root/work/fieldhint/facts/{tag}.json.gz', 'rt'))
    vals = json.load(open(f'/root/work/static2/values/{g}.json'))
    fn = F['functions']
    arch_entries = sorted(f['name'][9:] for f in fn.values() if f['name'].startswith('__do_sys_') and f['file'].startswith('arch/riscv/'))
    print(g, 'syscall entries defined in arch/riscv:', arch_entries)
    res = {}
    for d in (8, 9, 10):
        ns = {'__file__': P + '/hints4.py', '__name__': 'h4_%d' % d}
        exec(compile(src.replace('DEPTH = 8 if I4 else 4', f'DEPTH = {d} if I4 else 4'), 'hints4', 'exec'), ns)
        h = ns['run'](F, vals, {"I1", "I2", "I3", "I4"})
        res[d] = h
        mm = [(s['fn'], s['line']) for s in h['sites'].get('mmap', []) if s['fn'].startswith('generic_get_unmapped')]
        print(g, 'DEPTH', d, 'sites', sum(len(v) for v in h['sites'].values()), 'syscalls with sites', len(h['sites']),
              'mmap sites', len(h['sites'].get('mmap', [])), 'mmap generic_get_unmapped sites', mm)
    for sc in arch_entries:
        a = {(s['fn'], s['line']) for s in res[8]['sites'].get(sc, [])}
        b = {(s['fn'], s['line']) for s in res[9]['sites'].get(sc, [])}
        print('   ', sc, 'sites depth8', len(a), 'depth9', len(b))
