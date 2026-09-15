import argparse
import hashlib
import json

from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--outdir',type=Path,required=True);out=ap.parse_args().outdir
    manifest=json.loads((out/'manifest.json').read_text())
    for path,digest in manifest['artifacts'].items():
        assert hashlib.sha256((out/path).read_bytes()).hexdigest()==digest,path
    summary={}
    for mode in ('before','unified','followup'):
        rows=json.loads((out/mode/'results.json').read_text());assert len(rows)==32
        failures=[]
        for r in rows:
            bits,compat,pattern,short=r['args']
            fail=(compat==1 and bits>64 and pattern==1) if mode=='before' else (
                compat==1 and bits in (65,96) or mode=='unified' and bits in (128,192))
            fail=bool(fail and not short)
            assert r['passed']==(not fail),(mode,r['name'])
            if fail:failures.append(r['name'])
            if short:assert r['actual']['page_faults']==1 and r['actual']['consumed']==0
            if mode!='before' and fail:assert r['actual']['page_faults']==1
            if r['actual']['rc']:assert r['actual']['consumed']==0
        summary[mode]={'count':32,'failed':failures}
    (out/'verified.json').write_text(json.dumps({'verified':True,'cases':summary,'unresolved_followup_cases':4},indent=2)+'\n')
    print('Verified 96 executions; retained four follow-up contract mismatches, not treated as passes.')

if __name__=='__main__':main()
