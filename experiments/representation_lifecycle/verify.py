"""Independent exact counterexample and artifact checks; no model calls."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--outdir',type=Path,required=True)
    out=ap.parse_args().outdir
    manifest=json.loads((out/'manifest.json').read_text())
    for path,digest in manifest['artifacts'].items():
        assert hashlib.sha256((out/path).read_bytes()).hexdigest()==digest,path
    summary=json.loads((out/'summary.json').read_text()); total=0
    for case,modes in summary.items():
        for mode,arches in modes.items():
            for arch,report in arches.items():
                rows=json.loads((out/case/mode/(arch+'-results.json')).read_text())
                assert len(rows)=={'numa':36,'perf':12,'topology':12}[case]
                assert len({r['name'] for r in rows})==len(rows)
                # ELF class/data encoding verifies that the s390x run is big endian.
                elf=(out/case/mode/arch).read_bytes()
                assert elf[:4]==b'\x7fELF' and elf[4]==2
                assert elf[5]==(2 if arch=='s390x' else 1)
                failed=[]
                for row in rows:
                    expected_failure=False
                    if case=='numa' and mode=='before':
                        bits,compat,bound=map(int,re.fullmatch(r'bits(\d+)-compat(\d+)-bound(\d+)',row['name']).groups())
                        if arch=='x86_64': expected_failure=compat==1 and bits<=32 and bound==0
                        else: expected_failure=compat==1 and bits in (1,31,32,63,64) and bound!=2
                    elif case=='perf' and mode=='before' and arch=='s390x':
                        kind,val=map(int,re.fullmatch(r'field(\d+)-(\d+)',row['name']).groups())
                        expected_failure=kind<5 and val!=0
                    elif case=='topology': expected_failure=mode!='after'
                    assert row['passed']==(row['expected']==row['actual'])
                    assert row['passed']==(not expected_failure),(case,mode,arch,row['name'])
                    if not row['passed']: failed.append(row['name'])
                    if case=='topology':
                        assert [e['event'] for e in row['actual']]==['notify','online','offline','notify']
                        assert row['actual'][0]['online']==1 and row['actual'][3]['online']==1
                        assert row['actual'][2]==dict(event='offline',group=0,thread=0,online=1)
                assert failed==report['failed'] and report['passed']==len(rows)-len(failed)
                total+=len(rows)
    assert total==288
    result={'verified':True,'executions':total,'historical_comparison_executions':240,
            'partial_repair_executions':48,'checks':'hashes, ELF endian, exact failed cases, lifecycle observations'}
    (out/'verified.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
