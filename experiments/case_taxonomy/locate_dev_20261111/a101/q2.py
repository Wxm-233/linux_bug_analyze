import gzip, json, sys
sys.path.insert(0, '/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/heldout_prep_20261110/pipeline')
F = json.load(gzip.open('/root/work/fieldhint/facts/A101_pre.json.gz', 'rt'))
fn = F['functions']
by = {}
for u, f in fn.items(): by.setdefault(f['name'], []).append(u)
def show(n):
    for u in by.get(n, []):
        f = fn[u]
        print('==', n, f['file'], f['line'], 'params', [p[0] for p in f['params']])
        for c in f['calls']: print('     call', c[1], c[2][:5])
for n in ('__do_sys_mmap', 'riscv_sys_mmap', 'ksys_mmap_pgoff', 'vm_mmap_pgoff', 'do_mmap', 'get_unmapped_area', 'arch_get_unmapped_area', 'arch_get_unmapped_area_topdown', 'mm_get_unmapped_area'):
    show(n)
regs = [r for f in fn.values() for r in f.get('regs', []) if r[1] == 'get_unmapped_area'] + [r for r in F.get('global_regs', []) if r[1] == 'get_unmapped_area']
print('registrations of field get_unmapped_area:', regs[:8])
PY=1
