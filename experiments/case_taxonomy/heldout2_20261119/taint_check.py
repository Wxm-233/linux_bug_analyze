import json, os, io
sp=json.load(open('case_taxonomy/heldout2_20261119/split.json'))
ids={h[:12]:('analysis' if h in sp['analysis'] else 'sealed') for h in sp['analysis']+sp['sealed']}
skip_files={'case_taxonomy/heldout_commit_20261117/pool.json','case_taxonomy/depmine_20261115/candidates.json'}
hits={}
for root,dirs,files in os.walk('.'):
    if 'heldout2_20261119' in root or '__pycache__' in root: continue
    for fn in files:
        p=os.path.join(root,fn).replace(chr(92),'/')[2:]
        if p in skip_files or not fn.endswith(('.md','.json','.txt','.log','.py','.sh')): continue
        try: s=io.open(p,encoding='utf-8',errors='ignore').read()
        except Exception: continue
        for h in ids:
            if h in s: hits.setdefault(h,set()).add(p)
for h,ps in sorted(hits.items(), key=lambda x:ids[x[0]]):
    print(ids[h], h, len(ps), sorted(ps)[:5])
print('total hits', len(hits))
