"""Build and boot the dedicated KUnit kernel, preserving both success and failure."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worktree',type=Path,required=True)
    parser.add_argument('--build-dir',type=Path,required=True)
    parser.add_argument('--outdir',type=Path,required=True)
    parser.add_argument('--mode',choices=['before','after'],required=True)
    args=parser.parse_args()
    out=args.outdir.resolve();out.mkdir(parents=True,exist_ok=True)
    tree=args.worktree.resolve();build=args.build_dir.resolve()
    source=json.loads((tree/'.lba-vtd-kunit.json').read_text())
    assert source['mode']==args.mode
    for name,digest in source['managed_files'].items():
        assert hashlib.sha256((tree/name).read_bytes()).hexdigest()==digest,name
    command=['python3','-u','tools/testing/kunit/kunit.py','run','--arch=x86_64',
             '--build_dir='+str(build),'--kunitconfig='+str(Path(__file__).with_name('kunitconfig').resolve()),
             '--jobs=8','--timeout=120','--json='+str(out/(args.mode+'-kunit.json')),
             'intel-iommu-pte-contract']
    start=time.monotonic()
    with (out/(args.mode+'-build-run.log')).open('w') as log:
        proc=subprocess.run(command,cwd=tree,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
    artifacts={}
    for name,dest in [('.config',args.mode+'-config'),('test.log',args.mode+'-boot.log'),
                      ('arch/x86/boot/bzImage',args.mode+'-bzImage')]:
        path=build/name
        if path.exists():
            shutil.copyfile(path,out/dest)
            artifacts[dest]=hashlib.sha256(path.read_bytes()).hexdigest()
    info={'mode':args.mode,'returncode':proc.returncode,'elapsed_seconds':round(time.monotonic()-start,2),
          'command':command,'source':source,'artifacts':artifacts}
    (out/(args.mode+'-run.json')).write_text(json.dumps(info,indent=2)+'\n')
    print(json.dumps(info,indent=2))
    print('\n'.join((out/(args.mode+'-build-run.log')).read_text().splitlines()[-35:]))


if __name__=='__main__':main()
