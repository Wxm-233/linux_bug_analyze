import gzip, json
F = json.load(gzip.open('/root/work/fieldhint/facts/A101_pre.json.gz', 'rt'))
fn = F['functions']; M = F['macros']
print('macro def:', M.get('arch_get_mmap_end'))
for u, f in fn.items():
    gs = [g for g in f['guards'] if any('arch_get_mmap_end' in i for i in g['items'])]
    cs = [c for c in f['calls'] if 'arch_get_mmap_end' in c[1]]
    if gs or cs or f['name'] == 'arch_get_mmap_end':
        print('==', f['name'], f['file'], f['line'], 'params', [p[0] for p in f['params']])
        for g in gs: print('   guard', g['line'], 'p', g['p'], [i for i in g['items'] if 'mmap' in i or 'TASK' in i][:8], 'cmps', len(g['cmps']))
        for c in cs: print('   call', c[1], c[2])
