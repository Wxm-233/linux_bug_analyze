"""Four frozen runtime arguments, one image and actual QEMU sparse platform."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import time

HERE=Path(__file__).resolve().parent
ROOT=Path('/root/.cache/linux-bug-analyze/cpu-identity-runtime-20261027')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path,value):
    with path.open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2); f.write('\n')

def main():
    manifest=HERE/'boot_execution.json'
    if manifest.exists():
        raise ValueError('preserve boot execution')
    build=json.loads((HERE/'build_complete.json').read_bytes())
    guest=json.loads((HERE/'guest_build.json').read_bytes())
    matrix=json.loads((HERE/'boot_matrix.json').read_bytes())
    image=Path(build['image']); initrd=Path(guest['initrd']); config=Path(build['build_directory'])/'.config'
    if sha(image)!=build['image_sha256'] or sha(initrd)!=guest['initrd_sha256'] or sha(config)!=build['config_sha256']:
        raise ValueError('kernel_guest_configuration_identity_changed')
    archive=HERE/'kernel_inputs'; archive.mkdir(exist_ok=False)
    for src,name in [(image,'Image'),(Path(build['vmlinux']),'vmlinux'),(initrd,'initramfs.cpio.gz'),(Path(guest['binary']),'init')]:
        shutil.copyfile(src,archive/name)
    records=[]
    for profile in matrix['profiles']:
        name=profile['name']; local=ROOT/'runs'/name; local.mkdir(parents=True,exist_ok=False)
        cmdline=' '.join(['console=ttyAMA0','earlycon=pl011,0x9000000','rdinit=/init','panic=1','loglevel=7','lba_case='+name,*profile['arguments']])
        argv=['qemu-system-aarch64','-machine','virt,gic-version=3','-cpu','cortex-a57','-accel','tcg,thread=multi',
              '-smp','17','-m','512','-display','none','-serial','stdio','-monitor','none','-nic','none','-no-reboot',
              '-kernel',str(image),'-initrd',str(initrd),'-append',cmdline]
        start=time.monotonic(); timeout=False
        with (local/'console.log').open('xb') as stdout,(local/'qemu.stderr.log').open('xb') as stderr:
            try:
                done=subprocess.run(argv,stdout=stdout,stderr=stderr,timeout=180)
                code=done.returncode
            except subprocess.TimeoutExpired:
                timeout=True; code=None
        console=(local/'console.log').read_text(errors='replace')
        complete='LBA_USER {"event":"end","reached_end":true}' in console
        powered='reboot: Power down' in console
        receipt={'profile':name,'argv':argv,'cmdline':cmdline,'returncode':code,'timed_out':timeout,
            'seconds':round(time.monotonic()-start,3),'observer_reached_end':complete,'power_down_observed':powered,
            'image_sha256':sha(image),'config_sha256':sha(config),'initrd_sha256':sha(initrd),
            'console_sha256':sha(local/'console.log'),'stderr_sha256':sha(local/'qemu.stderr.log'),
            'runtime_arguments':profile['arguments'],'actual_Linux_boot':True,
            'qualification':'collection_complete' if code==0 and complete and powered and not timeout else 'incomplete'}
        save(local/'receipt.json',receipt)
        destination=HERE/'runs'/name; destination.parent.mkdir(exist_ok=True)
        shutil.copytree(local,destination)
        records.append(receipt)
        print(json.dumps({key:receipt[key] for key in ['profile','returncode','seconds','observer_reached_end','power_down_observed','qualification']}),flush=True)
    save(manifest,{'runs':records,'actual_Linux_boots':len(records),'new_full_kernel_builds':1,'new_PID1_compilations':1,
                   'new_model_calls':0,'DT_dump_processes':3})

if __name__=='__main__':
    main()
