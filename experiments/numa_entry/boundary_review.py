"""Recheck storage against the actual maxnode argument; never overwrite old data."""
import argparse,json,subprocess,hashlib
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--source-run',type=Path,required=True);p.add_argument('--outdir',type=Path,required=True);a=p.parse_args()
    a.outdir.mkdir(parents=True,exist_ok=False)
    original=(a.source_run/'followup/harness.c').read_text()
    old='size_t bytes=((bits+word-1)/word)*(word/8);'
    assert original.count(old)==1
    variants={'original_effective_bits':old,'declared_maxnode':'size_t bytes=((bits+1+word-1)/word)*(word/8);',
              'declared_maxnode_padded64':'size_t bytes=((bits+1+63)/64)*8;'}
    rows=[]
    for label,replacement in variants.items():
        source=a.outdir/(label+'.c');source.write_text(original.replace(old,replacement))
        exe=a.outdir/label;subprocess.run(['gcc','-O2','-Wall','-Wextra','-Werror',str(source),'-o',str(exe)],check=True)
        for bits in (65,96):
            for tail in (0,1):
                result=json.loads(subprocess.check_output([str(exe),str(bits),'1',str(tail),'0']))
                rows.append({'variant':label,'effective_bits':bits,'syscall_maxnode':bits+1,'tail':tail,
                    'storage_bytes':(((bits if label=='original_effective_bits' else bits+1)+(63 if label.endswith('64') else 31))//(64 if label.endswith('64') else 32))*(8 if label.endswith('64') else 4),
                    'actual':result,'expected_if_sufficient':-22 if tail else 0})
    (a.outdir/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
    (a.outdir/'manifest.json').write_text(json.dumps({'source_sha256':hashlib.sha256(original.encode()).hexdigest(),
        'scope':'same historical followup slice, storage-size intervention only; not full historical kernel'},indent=2))
    print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
