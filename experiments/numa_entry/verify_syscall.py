"""Validate recorded end-to-end observations without relabeling them as fixes."""
import argparse,json,hashlib,collections
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);a=p.parse_args();summary={}
for name,expected in [('native-final.log',64),('compat32-final.log',16)]:
    rows=[json.loads(l) for l in (a.outdir/name).read_text().splitlines() if l.startswith('{')]
    assert len(rows)==expected
    for r in rows:
        assert r['get_rc']==0
        if r['set_rc']==0:
            assert r['mode']==2 and r['mask0']==1 and r['page_query_rc']==0 and r['page_node']==0
        else:assert r['mode']==0 and r['mask0']==0 and r['set_rc'] in (-14,-22)
        compat=r.get('compat_dispatch',1)
        fault=compat and r['bits']==1025 and not r['padding64']
        expected_rc=-14 if fault else (-22 if r['bits']>1024 and r['tail'] else 0)
        assert r['set_rc']==expected_rc,(name,r)
    summary[name]={'count':len(rows),'return_codes':dict(collections.Counter(r['set_rc'] for r in rows)),
                   'successful_policy_and_page_readbacks':sum(r['set_rc']==0 for r in rows)}
summary['scope']='Observed WSL 6.18.33.2 x86_64, CONFIG_NODES_SHIFT=10, node0 allowed; not historical kernel or physical multi-node validation'
summary['artifacts']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in a.outdir.iterdir() if f.is_file() and f.name!='verified.json'}
(a.outdir/'verified.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
