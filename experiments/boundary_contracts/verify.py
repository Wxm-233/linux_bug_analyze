"""Verify saved artifacts, full fixture coverage and exact counterexample sets."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--outdir',type=Path,required=True)
    out=ap.parse_args().outdir
    manifest=json.loads((out/'manifest.json').read_text())
    for path,digest in manifest['artifacts'].items():
        assert hashlib.sha256((out/path).read_bytes()).hexdigest()==digest,path
    summary=json.loads((out/'summary.json').read_text())
    for case in ('btrfs','fbnic','parisc'):
        fixtures=json.loads((out/(case+'-fixtures.json')).read_text())
        for mode in ('before','after'):
            rows=json.loads((out/case/mode/'results.json').read_text())
            assert len(rows)==len(fixtures)
            expected_failed=set()
            for row,(name,inputs,want) in zip(rows,fixtures):
                assert (row['name'],row['inputs'],row['expected'])==(name,inputs,want)
                assert row['passed']==(row['actual']==want)
                if mode=='before':
                    if case=='btrfs' and inputs[0]==65536 and inputs[1]>4096:
                        expected_failed.add(name)
                    elif case=='fbnic' and inputs[0]>4096:
                        expected_failed.add(name)
                    elif case=='parisc' and want['cleared']==0:
                        expected_failed.add(name)
            actual_failed={r['name'] for r in rows if not r['passed']}
            assert actual_failed==expected_failed,(case,mode)
            assert set(summary[case][mode]['failed'])==actual_failed
            assert summary[case][mode]['passed']==len(rows)-len(actual_failed)
    print('Verified: artifact hashes, 100 executions, exact old failures, all fixed cases pass.')


if __name__=='__main__': main()
