from pathlib import Path
import hashlib,json,shutil,subprocess
H=Path(__file__).resolve().parent;R=H.parents[3];rev='db191ba0c8564ff84877e5b1c9553e991feca239'
def digest(b):return hashlib.sha256(b).hexdigest()
if (H/'notes_before.json').exists():raise RuntimeError('preserve round')
names=['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']
(H/'notes_before.json').write_text(json.dumps({'before_sha256':{n:digest((R/n).read_bytes()) for n in names}},ensure_ascii=False,indent=2),encoding='utf-8')
shutil.copyfile(R/'接口验证后续规划.md',H/'plan_before.md');shutil.copyfile(H.parent/'virtio_add_recycle_20261027/sync_work_notes.py',H/'sync_work_notes.py')
(H/'source').mkdir(exist_ok=True);rows=[]
for path in ['arch/arm64/mm/cache.S','arch/arm64/include/asm/assembler.h','arch/arm64/include/asm/cache.h','arch/arm64/include/asm/cacheflush.h']:
 b=subprocess.check_output(['git','-C','/root/repos/linux','show',rev+':'+path]);blob=subprocess.check_output(['git','-C','/root/repos/linux','rev-parse',rev+':'+path],text=True).strip();assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==blob
 name=path.replace('/','__');(H/'source'/name).write_bytes(b);rows.append(dict(path=path,local=name,blob=blob,sha256=digest(b)))
(H/'sources.json').write_text(json.dumps(dict(revision=rev,files=rows),indent=2))
info={}
for cmd in ['aarch64-linux-gnu-gcc','qemu-aarch64','aarch64-linux-gnu-objdump','gdb-multiarch']:
 info[cmd]=shutil.which(cmd)
(H/'environment.json').write_text(json.dumps(info,indent=2));print(json.dumps(info))
