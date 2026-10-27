"""Read tools/config and save actual QEMU DT; do not boot Linux yet."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

HERE=Path(__file__).resolve().parent
OLD=Path('/root/.cache/linux-bug-analyze/virtio-platform-20261027')

def save(name,value):
    with (HERE/name).open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2); f.write('\n')

def main():
    config=OLD/'build/.config'
    plan=json.loads((HERE/'frozen_plan.json').read_bytes())
    environment={'tools':{x:shutil.which(x) for x in ['qemu-system-aarch64','aarch64-linux-gnu-gcc','qemu-system-sparc64','sparc64-linux-gnu-gcc']},
        'config_sha256':hashlib.sha256(config.read_bytes()).hexdigest(),'qemu_version':subprocess.check_output(['qemu-system-aarch64','--version'],text=True).splitlines()[0]}
    save('environment.json',environment)
    shutil.copyfile(config,HERE/'baseline.config')
    for name in plan['source_files']:
        raw=subprocess.check_output(['git','-C','/root/repos/linux','show',plan['revision']+':'+name])
        target=HERE/'sources'/name; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(raw)
    manifest=[]
    for name in plan['source_files']:
        target=HERE/'sources'/name; raw=target.read_bytes()
        actual=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        wanted=subprocess.check_output(['git','-C','/root/repos/linux','rev-parse',plan['revision']+':'+name],text=True).strip()
        if actual!=wanted:
            raise ValueError('source blob mismatch:'+name)
        manifest.append({'path':name,'revision':plan['revision'],'git_blob':actual,'sha256':hashlib.sha256(raw).hexdigest()})
    save('source_manifest.json',manifest)
    argv=['qemu-system-aarch64','-machine','virt,gic-version=3,dumpdtb='+str(HERE/'topology.dtb'),
          '-cpu','cortex-a57','-accel','tcg','-smp','4,clusters=2,cores=2,threads=1','-m','512','-display','none']
    result=subprocess.run(argv,capture_output=True,timeout=30)
    (HERE/'dt_dump.stdout.log').write_bytes(result.stdout); (HERE/'dt_dump.stderr.log').write_bytes(result.stderr)
    save('dt_dump_receipt.json',{'argv':argv,'returncode':result.returncode,'new_Linux_boot':False})
    print(json.dumps({'source_files':len(manifest),'DT_dump_returncode':result.returncode,'stderr':result.stderr.decode(errors='replace')[:700]}))

if __name__=='__main__':
    main()
