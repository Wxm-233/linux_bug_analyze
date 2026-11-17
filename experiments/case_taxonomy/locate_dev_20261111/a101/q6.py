import gzip, json, sys
P = '/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/heldout_prep_20261110/pipeline'
sys.path.insert(0, P)
src = open(P + '/hints4.py').read().replace('DEPTH = 8 if I4 else 4', 'DEPTH = 9 if I4 else 4')
ns = {'__file__': P + '/hints4.py', '__name__': 'h4_9'}
exec(compile(src, 'hints4', 'exec'), ns)
F = json.load(gzip.open('/root/work/fieldhint/facts/A101_pre.json.gz', 'rt'))
vals = json.load(open('/root/work/static2/values/A101.json'))
h = ns['run'](F, vals, {"I1", "I2", "I3", "I4"})
for s in h['sites']['mmap']:
    if s['fn'].startswith('generic_get_unmapped'):
        print(s['fn'], s['line'], 'depth', s['depth'], 'divergent', sorted(s['divergent'])[:5], 'values', json.dumps(s['values'])[:300])
