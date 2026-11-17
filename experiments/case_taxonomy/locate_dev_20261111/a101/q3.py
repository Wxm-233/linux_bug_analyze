import gzip, json
F = json.load(gzip.open('/root/work/fieldhint/facts/A101_pre.json.gz', 'rt'))
fn = F['functions']
for u, f in fn.items():
    if f['name'] == '__get_unmapped_area':
        print('==', f['file'], f['line'], [p[0] for p in f['params']])
        for c in f['calls']: print('   call', c[0][:40], c[1], c[2][:5])
