"""Build once per policy, then boot isolated QEMU once per firmware scenario."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--worktree',type=Path,required=True)
    p.add_argument('--build-dir',type=Path,required=True)
    p.add_argument('--outdir',type=Path,required=True)
    p.add_argument('--mode',choices=['before','after'],required=True)
    p.add_argument('--scenarios',default='0,1,2,3,4,5,6,7')
    a=p.parse_args(); out=a.outdir.resolve(); out.mkdir(parents=True,exist_ok=True)
    build=a.build_dir.resolve(); tree=a.worktree.resolve()
    marker=json.loads((tree/'.lba-acpi-test.json').read_text())
    assert marker['mode']==a.mode
    for name,digest in marker['files'].items():
        assert hashlib.sha256((tree/name).read_bytes()).hexdigest()==digest
    cmd=['python3','tools/testing/kunit/kunit.py','build','--arch=x86_64',
         '--build_dir='+str(build),'--kunitconfig='+str(Path(__file__).with_name('kunitconfig').resolve()),'--jobs=8']
    start=time.monotonic()
    with (out/(a.mode+'-build.log')).open('w') as f:
        proc=subprocess.run(cmd,cwd=tree,stdout=f,stderr=subprocess.STDOUT,timeout=1800)
    if proc.returncode:
        print((out/(a.mode+'-build.log')).read_text()[-5000:]); raise SystemExit(proc.returncode)
    image=out/(a.mode+'-bzImage')
    shutil.copyfile(build/'arch/x86/boot/bzImage',image)
    shutil.copyfile(build/'.config',out/(a.mode+'-config'))
    runs=[]
    for scenario in map(int,a.scenarios.split(',')):
        assert 0<=scenario<=7
        cmd=['qemu-system-x86_64','-machine','q35','-accel','tcg','-cpu','max','-m','512',
             '-smp','1,maxcpus=8','-nodefaults','-display','none','-serial','stdio','-no-reboot',
             '-kernel',str(image),'-append',f'console=ttyS0 kunit.filter_glob=acpi-boot-contract kunit.enable=1 kunit_shutdown=reboot lba_acpi={scenario}']
        log=out/f'{a.mode}-{scenario}-boot.log'
        with log.open('w') as f:
            proc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=90)
        runs.append({'scenario':scenario,'returncode':proc.returncode,'command':cmd,'log':log.name})
        print(a.mode,scenario,'\n'+'\n'.join(l for l in log.read_text().splitlines() if any(k in l for k in ['LBA','acpi-boot-contract','not ok','possible=','apic=','fail:'])),flush=True)
    info={'source':marker,'runs':runs,'elapsed_seconds':round(time.monotonic()-start,2),
          'artifacts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob(a.mode+'-*') if p.is_file() and p.name!=a.mode+'-run.json'}}
    (out/(a.mode+'-run.json')).write_text(json.dumps(info,indent=2)+'\n')


if __name__=='__main__': main()
