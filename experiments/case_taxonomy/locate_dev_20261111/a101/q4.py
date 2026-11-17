import gzip, json, sys
sys.path.insert(0, '/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/heldout_prep_20261110/pipeline')
import hints4
F = json.load(gzip.open('/root/work/fieldhint/facts/A101_pre.json.gz', 'rt'))
vals = json.load(open('/root/work/static2/values/A101.json'))
fn = F['functions']
for u, f in fn.items():
    if f['name'] in ('mm_get_unmapped_area_vmflags', 'arch_get_unmapped_area_topdown_vmflags', 'arch_get_unmapped_area_vmflags', 'thp_get_unmapped_area_vmflags', '__thp_get_unmapped_area'):
        print('==', f['name'], f['file'], f['line'], [c[1] for c in f['calls']][:12])
h = hints4.run(F, vals, {"I1", "I2", "I3", "I4"})
chain = ['riscv_sys_mmap', 'ksys_mmap_pgoff', 'vm_mmap_pgoff', 'do_mmap', '__get_unmapped_area', 'mm_get_unmapped_area_vmflags',
         'arch_get_unmapped_area_topdown_vmflags', 'arch_get_unmapped_area_vmflags', 'generic_get_unmapped_area_topdown', 'generic_get_unmapped_area',
         'thp_get_unmapped_area_vmflags', '__thp_get_unmapped_area']
print('DEPTH', h['depth'])
for n in chain:
    print(f'{n:42s} reach_any depth={h["reach_any"].get(n)}  mapped={n in h["reach_map"]}')
print('mmap sites in generic_*:', [(s['fn'], s['line']) for s in h['sites'].get('mmap', []) if 'unmapped' in s['fn']])
print('sites in generic_* for any syscall:', sorted({(sc, s['fn'], s['line']) for sc, ss in h['sites'].items() for s in ss if s['fn'].startswith('generic_get_unmapped')})[:20])
# per-syscall BFS for mmap with the same edge rule (direct calls with any mapped argument)
from collections import deque
by = {}
for u, f in fn.items(): by.setdefault(f['name'], []).append(u)
ent = [u for u in by['__do_sys_mmap']][0]
depth = {ent: 0}; q = deque([ent])
while q:
    u = q.popleft()
    for c in fn[u]['calls']:
        for v in by.get(c[1], []):
            if v in fn and v not in depth:
                depth[v] = depth[u] + 1; q.append(v)
for n in chain:
    print(f'mmap-only depth {n:42s}', min((depth[u] for u in by.get(n, []) if u in depth), default=None))
