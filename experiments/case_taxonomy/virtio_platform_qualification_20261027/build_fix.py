from pathlib import Path
import subprocess,json,hashlib,re,shutil,difflib,time
H=Path(__file__).resolve().parent;C=Path('/root/.cache/linux-bug-analyze/virtio-platform-20261027');S=C/'source';O=C/'build';P='db191ba0c8564ff84877e5b1c9553e991feca239';F='95c7b0ad6c69d1c0608ff0bbd358a546856beaf3';path='drivers/virtio/virtio_input.c'
if (H/'fix_build.json').exists():raise RuntimeError('preserve fix build')
def show(rev):return subprocess.check_output(['git','-C','/root/repos/linux','show',rev+':'+path]).decode()
old,new=show(P),show(F);pat=r'^struct virtio_input \{.*?^\};';a=re.search(pat,old,re.M|re.S).group();b=re.search(pat,new,re.M|re.S).group()
expected=old.replace(a,b).replace('#include <linux/slab.h>','#include <linux/slab.h>\n#include <linux/dma-mapping.h>')
if expected!=new:raise RuntimeError('fix has other changes; review before applying')
changed=subprocess.check_output(['git','-C','/root/repos/linux','diff','--name-only',P,F],text=True).splitlines()
if changed!=[path]:raise RuntimeError('fix changes other files')
probe=(S/path).read_text()
if probe.count(a)!=1:raise RuntimeError('unexpected instrumented source')
fixed=probe.replace(a,b).replace('#include <linux/slab.h>','#include <linux/slab.h>\n#include <linux/dma-mapping.h>');shutil.copyfile(O/'vmlinux',C/'parent.vmlinux');(S/path).write_text(fixed)
(H/'fix_application.patch').write_text(''.join(difflib.unified_diff(probe.splitlines(True),fixed.splitlines(True),fromfile='instrumented-parent/'+path,tofile='instrumented-fix/'+path)))
start=time.monotonic();args=['make','-C',str(S),'O='+str(O),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','-j8','Image']
with (H/'fix_build.log').open('w') as out:r=subprocess.run(args,stdout=out,stderr=subprocess.STDOUT,timeout=1200)
record=dict(code=r.returncode,seconds=round(time.monotonic()-start,3),base_revision=P,fix_revision=F,complete_original_input_fix_applied=True,source_sha256=hashlib.sha256(fixed.encode()).hexdigest(),config_sha256=hashlib.sha256((O/'.config').read_bytes()).hexdigest(),args=args)
if not r.returncode:
 shutil.copyfile(O/'arch/arm64/boot/Image',C/'fixed.Image');shutil.copyfile(O/'vmlinux',C/'fixed.vmlinux');record['image_sha256']=hashlib.sha256((C/'fixed.Image').read_bytes()).hexdigest()
(H/'fix_build.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
if r.returncode:raise RuntimeError('fix build failed')
